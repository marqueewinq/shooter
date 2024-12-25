import asyncio
import hashlib
import json
import logging
import os
import typing as ty
import zipfile
from contextlib import asynccontextmanager
from io import BytesIO
from pathlib import Path

from celery import group
from celery.result import AsyncResult, GroupResult
from celery.utils.abstract import CallableSignature
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

from shooter.base import BaseModel
from shooter.celery_app import take_screenshot
from shooter.logs import setup_app_logger, setup_task_logger
from shooter.schema import (
    TakeScreenshotConfig,
    TakeScreenshotRequest,
    TakeScreenshotResponse,
    TaskProgressResponse,
)

# Default directory to save the resulting files
OUTPUT_PATH = os.getenv("OUTPUT_PATH")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await setup_app(_app)
    yield


async def setup_app(_app: FastAPI):
    """App start-up handler"""
    # Create the output directory
    output_path = os.getenv("OUTPUT_PATH")
    assert (
        output_path is not None
    ), "You must set up an OUTPUT_PATH environment variable."
    os.makedirs(output_path, exist_ok=True)
    _app.state.output_path = output_path
    # Create the app logger
    _app.state.logger = setup_app_logger(__name__)


app = FastAPI(
    title="Shooter",
    summary="Shooter: full-page screenshot tool",
    contact={
        "name": "Mark",
        "url": "https://t.me/marqueewinq",
        "email": "mark.vinogradov@phystech.edu",
    },
    version="1.0.0",
    lifespan=lifespan,
)

if ty.TYPE_CHECKING:

    class AppState(BaseModel):
        output_path: str
        logger: logging.Logger

    app.state = AppState()


@app.get("/")
async def index():
    """Health check endpoint"""
    return {}


async def _schedule_screenshot_task(
    config: TakeScreenshotConfig,
) -> ty.Optional[CallableSignature]:
    """Creates a take_screenshot task signature based on the provided config."""
    # Serialize the config to a JSON string
    config_dict = config.dict()
    config_str = json.dumps(config_dict, sort_keys=True)
    config_hash = hashlib.sha256(config_str.encode()).hexdigest()

    # Get the hostname from the URL
    hostname = config.parsed_url().hostname

    # Sanitize the hostname to avoid directory traversal attacks
    safe_hostname = hostname.replace("..", "").replace("/", "").replace("\\", "")
    directory_name = f"{safe_hostname}__{config.browser}__{'fullpage' if config.full_page_screenshot else 'viewport'}__{config_hash}"

    # Use the config hash as part of the output path
    host_path = os.path.join(app.state.output_path, safe_hostname)
    os.makedirs(host_path, exist_ok=True)
    output_path = os.path.join(host_path, directory_name)
    os.makedirs(output_path, exist_ok=True)

    # Save the config for observability
    with open(os.path.join(output_path, "config.json"), "w") as fd:
        json.dump(config.dict(), fd)

    # Create a unique logger for this task
    task_logger = setup_task_logger(config.url, output_path)
    task_logger.info(f"Scheduling screenshot task for {config.url}")
    task_logger.info(f"Output directory: {output_path}")

    # Handle proxy parameter passing
    proxy: ty.Optional[ty.Union[str, ty.List[str]]] = None
    if config.proxy is not None:
        if isinstance(config.proxy, list):
            proxy = [it.get_connection_string(masked=False) for it in config.proxy]
        else:
            proxy = config.proxy.get_connection_string(masked=False)

    # Return task signature
    return take_screenshot.s(
        url=config.url,
        output_path=output_path,
        config_dict=dict(
            browser=config.browser.value,
            full_page_screenshot=config.full_page_screenshot,
            capture_visible_elements=config.capture_visible_elements,
            capture_invisible_elements=config.capture_invisible_elements,
            window_size=config.window_size,
            user_agent=config.user_agent,
            proxy=proxy,
            wait_after_load=config.wait_after_load,
            wait_before_load=config.wait_before_load,
            wait_for_selector=config.wait_for_selector,
            wait_for_selector_timeout=config.wait_for_selector_timeout,
            scroll_pause_time=config.scroll_pause_time,
            actions=config_dict["actions"],
            device=config.device.value,
            disable_javascript=config.disable_javascript,
        ),
    )


async def _schedule_screenshot_group_task(
    config_list: ty.List[TakeScreenshotConfig],
) -> ty.Tuple[str, int]:
    """Schedules the tasks with provided configs as a group task.

    :param config_list: list of individual task configs (see `_schedule_screenshot_task`)

    :return pair of (group task id, number of task scheduled)
    """
    # Collect all signatures
    promise_list = [_schedule_screenshot_task(config) for config in config_list]
    signature_or_none_list = await asyncio.gather(*promise_list)

    # Filter in only successfully created signatures
    signature_list = [sig for sig in signature_or_none_list if sig is not None]

    # Apply as a group task
    task_group = group(signature_list)
    group_result = task_group.apply_async()

    # Commit to the celery_app.backend
    group_result.save()

    return group_result.id, len(signature_list)


@app.post(
    "/take_screenshots/",
    summary="Take screenshots for the provided sites.",
    response_model=TakeScreenshotResponse,
)
async def take_screenshots(
    request_data: TakeScreenshotRequest,
) -> TakeScreenshotResponse:
    """
    Schedules an async task for each given URL to do a screenshot of it.

    Takes in `TakeScreenshotRequest`; `.sites` can be either url or an
     `TakeScreenshotConfig`.

    Order of precedence of config values:

     1. Individual `TakeScreenshotConfig` objects;
     2. Values in `TakeScreenshotRequest.default_config`;
     3. Default values.

    The url MUST include the scheme (i.e. "https://") prefix; incorrect urls will be
     ignored.

    Example of the valid payload:

    ```json
    {
       "sites": [
         "https://google.com/",
         {"url": "https://google.com/", "browser": "firefox"}
       ],
       "default_config": {
         "browser": "chrome"
       }
     }
    ```

    This will capture both pages in mobile view, but with the different browsers. The
     default config will be applied to the first entry, but in the second entry the
     local value takes precedence.

    Returns `group_result_id`, which can be used to fetch the group task result.
    """
    group_result_id, n_members = await _schedule_screenshot_group_task(
        config_list=request_data.sites
    )
    return TakeScreenshotResponse(
        message=f"Scheduled {n_members} tasks",
        group_result_id=group_result_id,
    )


@app.get(
    "/take_screenshots/{group_result_id}",
    summary="Check the progress of a batch task.",
    response_model=TaskProgressResponse,
    responses={
        409: {
            "description": "Task with the provided ID is not found in the result backend",
        }
    },
)
async def task_progress(group_result_id: str) -> TaskProgressResponse:
    """
    Returns a status of the given task group.
    """
    async_result_list: ty.List[AsyncResult] = GroupResult.restore(group_result_id)
    if async_result_list is None:
        raise HTTPException(
            status_code=409, detail=f"Group task {group_result_id} not found"
        )
    return TaskProgressResponse.from_async_result_list(async_result_list)


@app.get("/take_screenshots/{group_result_id}/zip")
async def download_screenshots_zip(group_result_id: str):
    """
    Downloads all screenshots associated with a given group_result_id as a zip file.

    Depending on a group size, this can take up to 10 seconds; setting a high timeout
     is recommended.
    """
    # Fetch the group result
    async_result_list: ty.List[AsyncResult] = GroupResult.restore(group_result_id)
    if async_result_list is None:
        raise HTTPException(
            status_code=409, detail=f"Group task {group_result_id} not found"
        )

    # Collect the output_path from each task in the group
    collected_path_list: ty.List[Path] = []
    for async_result in async_result_list:
        if not async_result.ready() or not async_result.successful():
            continue
        try:
            output_path = Path(async_result.result["result"]["output_path"])
        except KeyError:
            continue

        if not output_path.exists() or not output_path.is_dir():
            continue

        collected_path_list.append(output_path)

    if len(collected_path_list) == 0:
        raise HTTPException(
            status_code=409,
            detail=f"Group task {group_result_id} does not have associated files",
        )

    # Create the zip file from the collected paths
    in_memory_zip = BytesIO()
    with zipfile.ZipFile(in_memory_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for base_path in collected_path_list:
            for file in base_path.rglob("*"):
                # Add each file in the task subdirectory
                zipf.write(file, arcname=file.relative_to(base_path.parent))

        zipf.close()

    # Create the response from the zip contents
    in_memory_zip.seek(0)
    return Response(
        content=in_memory_zip.read(),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={group_result_id}.zip"},
    )


def _serve_app(host: str = "0.0.0.0", port: int = 8000):  # pragma: no cover
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":  # pragma: no cover
    import fire
    import uvicorn

    fire.Fire(_serve_app)
