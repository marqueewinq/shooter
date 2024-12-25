import io
import json
import os
import tempfile
import zipfile
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from shooter.app import app as fastapi_app
from shooter.app import setup_app
from shooter.schema import TakeScreenshotConfig


@pytest.fixture
def app() -> FastAPI:
    with tempfile.TemporaryDirectory() as tmpdir:
        fastapi_app.state.output_path = tmpdir
        return fastapi_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


@pytest.mark.asyncio
async def test_index(client):
    response = client.get("/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_app__setup_app():
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "does_not_exist_yet")
        with patch("os.getenv", return_value=output_path):
            await setup_app(fastapi_app)
            assert fastapi_app.state.output_path == output_path


@pytest.mark.asyncio
@patch(
    "shooter.app.setup_task_logger", return_value=MagicMock()
)  # removes logging output
async def test_take_screenshots__success(mock_logger, client):
    with patch("shooter.app.take_screenshot.s") as mock_take_screenshot, patch(
        "shooter.app.group"
    ) as mock_group_callable:
        mock_signature = MagicMock(name="signature")
        mock_group_result = MagicMock(name="group_result", id="12345")
        mock_task_group = MagicMock(name="task_group")
        mock_take_screenshot.return_value = mock_signature
        mock_group_callable.return_value = mock_task_group
        mock_task_group.apply_async.return_value = mock_group_result

        correct_sites = [
            {"url": "https://example.com", "browser": "chrome"},
            "https://example.com",
        ]

        response = client.post(
            "/take_screenshots/",
            json={"sites": correct_sites},
        )

        assert response.status_code == 200
        assert response.json() == {
            "message": f"Scheduled {len(correct_sites)} tasks",
            "group_result_id": "12345",
        }


@pytest.mark.asyncio
async def test_task_progress__partial_success(client):
    with patch("celery.result.GroupResult.restore") as mock_restore:
        mock_async_result_ready_ok = MagicMock()
        mock_async_result_ready_ok.ready.return_value = True
        mock_async_result_ready_ok.successful.return_value = True
        mock_async_result_ready_ok.state = "SUCCESS"
        mock_async_result_not_ready = MagicMock()
        mock_async_result_not_ready.ready.return_value = False
        mock_async_result_not_ready.successful.return_value = False
        mock_async_result_not_ready.state = "PENDING"
        mock_async_result_ready_error = MagicMock()
        mock_async_result_ready_error.ready.return_value = True
        mock_async_result_ready_error.successful.return_value = False
        mock_async_result_ready_error.state = "FAILED"
        mock_restore.return_value = [
            mock_async_result_ready_ok,
            mock_async_result_not_ready,
            mock_async_result_ready_error,
        ]

        response = client.get("/take_screenshots/12345")

        assert response.status_code == 200
        assert response.json() == {
            "completed": 1,
            "total": 3,
            "failed": 1,
            "state": "PENDING",
            "all_successful": False,
            "ready": False,
        }


@pytest.mark.asyncio
async def test_task_progress__full_success(client):
    with patch("celery.result.GroupResult.restore") as mock_restore:
        mock_async_result_ready_ok = MagicMock()
        mock_async_result_ready_ok.ready.return_value = True
        mock_async_result_ready_ok.successful.return_value = True
        mock_async_result_ready_ok.state = "SUCCESS"
        mock_restore.return_value = [
            mock_async_result_ready_ok,
        ]

        response = client.get("/take_screenshots/12345")

        assert response.status_code == 200
        assert response.json() == {
            "completed": 1,
            "total": 1,
            "failed": 0,
            "state": "SUCCESS",
            "all_successful": True,
            "ready": True,
        }


@pytest.mark.asyncio
async def test_task_progress__not_found(client):
    with patch("celery.result.GroupResult.restore") as mock_restore:
        group_task_id = 12345
        mock_restore.return_value = None

        response = client.get(f"/take_screenshots/{group_task_id}")

        assert response.status_code == 409
        assert response.json()["detail"] == f"Group task {group_task_id} not found"


def test_download_screenshots_zip__ok(app, client):
    group_id = "test-group-id"
    base_path = app.state.output_path

    def _create_file(file_path: str) -> None:
        with open(file_path, "w") as file:
            file.write(file_path)

    with patch("celery.result.GroupResult.restore") as mock_restore:
        async_result_list = []
        # Add ready tasks
        for index_i in range(5):
            # Create the fake files
            directory_path = os.path.join(base_path, f"result_{index_i}")
            os.makedirs(directory_path)
            for index_j in range(5):
                _create_file(os.path.join(directory_path, f"{index_j}.txt"))

            # Set up the associated async_result
            mock_async_result = MagicMock()
            mock_async_result.ready.return_value = True
            mock_async_result.successful.return_value = True
            mock_async_result.result = {"result": {"output_path": directory_path}}
            async_result_list.append(mock_async_result)

        # Add non-ready task
        mock_async_result_not_ready = MagicMock()
        mock_async_result_not_ready.ready.return_value = False
        async_result_list.append(mock_async_result_not_ready)

        # Add ready task with wrong result format
        mock_async_result_wrong_result = MagicMock()
        mock_async_result_wrong_result.ready.return_value = True
        mock_async_result_wrong_result.successful.return_value = True
        mock_async_result_wrong_result.result = {"result": {}}
        async_result_list.append(mock_async_result_wrong_result)

        # Add ready task with non-existent output directory
        mock_async_result_no_files = MagicMock()
        mock_async_result_no_files.ready.return_value = True
        mock_async_result_no_files.successful.return_value = True
        mock_async_result_no_files.result = {
            "result": {"output_path": os.path.join(base_path, "does_not_exist")}
        }
        async_result_list.append(mock_async_result_no_files)

        # Add ready task with output_path pointing to the file (instead of directory)
        file_path = os.path.join(base_path, "file.txt")
        with open(file_path, "w") as fd:
            fd.write("This is a file")
        mock_async_result_is_not_dir = MagicMock()
        mock_async_result_is_not_dir.ready.return_value = True
        mock_async_result_is_not_dir.successful.return_value = True
        mock_async_result_is_not_dir.result = {"result": {"output_path": file_path}}
        async_result_list.append(mock_async_result_is_not_dir)

        mock_restore.return_value = async_result_list

        response = client.get(f"/take_screenshots/{group_id}/zip")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert (
            f"attachment; filename={group_id}.zip"
            in response.headers["content-disposition"]
        )

        # Verify the content is a valid zip file
        zip_bytes = BytesIO(response.content)
        assert zipfile.is_zipfile(
            zip_bytes
        ), "The response content should be a valid zip file"

        # Verify each file contents are correct
        with zipfile.ZipFile(zip_bytes, "r") as zipf:
            for info in zipf.infolist():
                with zipf.open(info) as file:
                    content = file.read().decode("utf-8").strip()
                    expected_content = os.path.join(base_path, info.filename)
                    assert (
                        content == expected_content
                    ), f"Content mismatch for {info.filename}"


def test_download_screenshots_zip__no_tasks(app, client):
    group_id = "test-group-id"

    with patch("celery.result.GroupResult.restore") as mock_restore:
        mock_restore.return_value = []

        response = client.get(f"/take_screenshots/{group_id}/zip")
        assert response.status_code == 409
        assert (
            response.json()["detail"]
            == f"Group task {group_id} does not have associated files"
        )


def test_download_screenshots_zip__not_found(client):
    with patch("celery.result.GroupResult.restore") as mock_restore:
        group_task_id = 12345
        mock_restore.return_value = None

        response = client.get(f"/take_screenshots/{group_task_id}/zip")

        assert response.status_code == 409
        assert response.json()["detail"] == f"Group task {group_task_id} not found"
