import os
import sys

sys.path += [
    os.path.dirname(__file__),
    os.path.join(os.path.dirname(__file__), ".."),
]

import json
import logging
import random
import re
import time
import typing as ty
from pprint import pformat

import retry

from shooter.actions import BaseAction
from shooter.draw import draw_elements_on_image
from shooter.drivers import BaseScreenshooter, ChromeScreenshooter, FirefoxScreenshooter
from shooter.drivers.device import Device
from shooter.logs import setup_task_logger

logging.getLogger("seleniumwire").setLevel(logging.ERROR)


def browser_to_screenshooter_class(browser: str) -> ty.Type[BaseScreenshooter]:
    return {
        "firefox": FirefoxScreenshooter,
        "chrome": ChromeScreenshooter,
    }[browser]


@retry.retry(tries=5, delay=1)
def _check_setup(output_path: str) -> None:
    assert os.access(output_path, os.W_OK), f"Not writable: {output_path=}"


def make_screenshot_from_url(
    url: str,
    output_path: str,
    browser: str = "chrome",
    logger: ty.Optional[logging.Logger] = None,
    full_page_screenshot: bool = True,
    capture_visible_elements: bool = True,
    capture_invisible_elements: bool = False,
    wait_after_load: float = 5,
    wait_before_load: ty.Optional[float] = None,
    wait_for_selector: ty.Optional[str] = None,
    wait_for_selector_timeout: float = 10,
    window_size: ty.Optional[str] = None,
    user_agent: ty.Optional[str] = None,
    proxy: ty.Optional[ty.Union[str, ty.List[str]]] = None,
    scroll_pause_time: float = 0.1,
    actions: ty.Optional[ty.List[dict]] = None,
    device: str = "desktop",
    disable_javascript: bool = False,
    headless: bool = True,
) -> None:
    """
    Take a screenshot of the web page.

    Given an url, saves a page screenshot, elements.json and labelled image
     in `output_path` directory.

    The chrome driver used by selenium is cached and will be reused on subsequent
     executions.

    :param url: URL to screenshot
    :param output_path: directory to save the resulting files
    :param browser: driver to take a screenshot with; either "chrome" (default)
        or "firefox".
    :param logger: logger to use (default = logging.getLogger(__package__)
    :param full_page_screenshot: if True, captures the whole page; if False -- only
        the current viewport is captured.
    :param capture_visible_elements: by default, only full_page.png will be saved;
        if True, saves visible page elements as a JSON file (with visible=True property).
    :param capture_invisible_elements: if Trie, also saves invisible elements into the
        same JSON file (with visible=False property).
    :param wait_after_load: how much time to wait until the page is ready.
    :param wait_before_load: how much time to wait before loading the page
        (default: random 0..5 sec).
    :param wait_for_selector: wait for the specified selector to become available.
    :param wait_for_selector_timeout: timeout in seconds for `wait_for_selector`
        (default: 10 sec).
    :param window_size: Viewport dimensions (i.e. `1920x1080`)
    :param user_agent: Overrides default user-agent header.
    :param proxy: Connection string to proxy server,
        i.e. `https://{username}:{password}@{hostname}:{port}`
    :param scroll_pause_time: How much to wait between `actions`.
    :param actions: List of BaseActions (as dicts) to do before the capture.
    :param device: Which device to emulate (default: "desktop").
    :param disable_javascript: Disables javascript for this page.
    :param headless: If False, the browser window will pop up. Furthermore, the script
        will pause after the page loads, allowing the user to interact with it. To
        continue normally, press Enter.
    """
    _check_setup(output_path=output_path)

    screenshot_path = os.path.join(output_path, "screenshot.png")
    elements_json_path = os.path.join(output_path, "elements.json")
    labelled_screenshot_path = os.path.join(output_path, "screenshot.labelled.png")
    driver_log_path = os.path.join(output_path, "driver_log.txt")

    start_time = time.time()

    # Override with the default logger if necessary
    logger = logger if logger is not None else setup_task_logger(url, output_path)

    # Convert CLI arguments to corresponding instances
    screenshooter_class = browser_to_screenshooter_class(browser)
    device_config = Device(device.upper()).get_device_config()
    action_list = (
        [BaseAction.from_dict(item) for item in actions]
        if actions is not None
        else None
    )

    # Mask the password in the proxy connection string
    def mask_proxy_conn_str(conn_str: ty.Optional[str]) -> str:
        if conn_str is None:
            return conn_str
        return re.sub(
            r"(?<=:)[^:@]*(?=@)",
            "****",
            conn_str,  # assumes password is between the first : and @
        )

    masked_proxy: ty.Optional[ty.Union[str, ty.List[str]]] = None
    if proxy is not None and isinstance(proxy, list):
        masked_proxy = [mask_proxy_conn_str(it) for it in proxy]
    if proxy is not None and isinstance(proxy, str):
        masked_proxy = mask_proxy_conn_str(proxy)

    logger.info(
        (
            f"Started making a screenshot with PID={os.getpid()}: \n"
            f"\t{browser=}\n"
            f"\t{full_page_screenshot=}\n"
            f"\t{capture_visible_elements=}\n"
            f"\t{capture_invisible_elements=}\n"
            f"\t{wait_after_load=}\n"
            f"\t{window_size=}\n"
            f"\t{user_agent=}\n"
            f"\tproxy={pformat(masked_proxy)}\n"
            f"\t{scroll_pause_time=}\n"
            f"\tactions={pformat(action_list)}\n"
            f"\t{device=}\n"
            f"\t{disable_javascript=}\n"
            f"\t{headless=}\n"
        )
    )

    # Create a WebDriver
    try:
        driver_setup_time_start = time.time()
        screenshooter = screenshooter_class(
            logger=logger,
            window_size=window_size,
            user_agent=user_agent,
            proxy=proxy
            if proxy is None or isinstance(proxy, list)
            else [proxy],  # Transform `proxy` to list of values or None
            device_config=device_config,
            disable_javascript=disable_javascript,
            headless=headless,
            log_path=driver_log_path,
        )
        logger.info(
            f"{browser.capitalize()} driver set up in {time.time() - driver_setup_time_start:.2f}s"
        )
    except Exception as e:
        logger.error(e)
        raise e

    device_config = screenshooter.device_config

    if wait_before_load is None:
        # Wait for random 0..5 seconds
        wait_before_load = random.random() * 5

    # Load the page
    load_page_time_start = time.time()
    is_page_loaded = screenshooter.load_page_with_checks(
        url,
        wait_before_load=wait_before_load,
        wait_after_load=wait_after_load,
        wait_for_selector=wait_for_selector,
        wait_for_selector_timeout=wait_for_selector_timeout,
    )
    if not is_page_loaded:
        raise RuntimeError(f"Could not load the page: {url}")
    logger.info(f"Page loaded in {time.time() - load_page_time_start:.2f}s")

    logger.info(
        f"Setting viewport dimensions to {device_config.width}x{device_config.height}..."
    )
    screenshooter.set_viewport_dimensions(device_config.width, device_config.height)

    if not headless:
        input("You can now interact with the page. Press Enter to continue...")

    # Create necessary artifacts
    logger.info("Making a screenshot...")
    if full_page_screenshot:
        screenshooter.take_full_page_screenshot(
            screenshot_path,
            scroll_pause_time=scroll_pause_time,
            actions=action_list,
        )
    else:
        screenshooter.take_viewport_screenshot(
            screenshot_path,
            scroll_pause_time=scroll_pause_time,
            actions=action_list,
        )

    if capture_visible_elements:
        pixel_ratio = device_config.pixel_ratio
        logger.info(f"Fetching elements with {pixel_ratio=}...")
        element_data = screenshooter.get_elements(
            pixel_ratio=pixel_ratio,
            full_page_screenshot=full_page_screenshot,
            capture_invisible_elements=capture_invisible_elements,
        )
        with open(elements_json_path, "w") as fd:
            json.dump([it.dict() for it in element_data], fd)

        logger.info("Drawing the labelled image...")
        draw_elements_on_image(screenshot_path, element_data, labelled_screenshot_path)

    total_seconds = time.time() - start_time
    logger.info(f"Done in {total_seconds:.2f}s.")


if __name__ == "__main__":  # pragma: no cover
    import fire

    fire.Fire(make_screenshot_from_url)
