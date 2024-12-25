import base64
import logging
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from shooter.drivers import ChromeScreenshooter, FirefoxScreenshooter
from shooter.drivers.device import Device


@pytest.mark.parametrize(
    "kwargs",
    [
        {"window_size": "100x200"},
        {"user_agent": "hello i am user agent"},
        {
            "proxy": {
                "host": "example.com",
                "port": 8000,
                "username": "username",
                "password": "password",
            }
        },
        {"device_config": Device.DESKTOP.get_device_config()},
        {"disable_javascript": True},
        {"headless": False},
        {"log_path": "/tmp/log.txt"},
        {"extra_args": {"extra": "arg"}},
    ],
)
def test_driver_loads(kwargs):
    logger = logging.getLogger(__name__)
    with patch("shooter.drivers.chrome.webdriver.Chrome"):
        ChromeScreenshooter.get_driver_service = MagicMock()
        instance = ChromeScreenshooter(logger=logger, **kwargs)
        assert instance.driver is not None

    with patch("shooter.drivers.firefox.webdriver.Firefox"):
        FirefoxScreenshooter.get_driver_service = MagicMock()
        instance = FirefoxScreenshooter(logger=logger, **kwargs)
        assert instance.driver is not None


def test_chrome__calls_screenshots():
    logger = logging.getLogger(__name__)
    with patch("shooter.drivers.chrome.webdriver.Chrome"):
        ChromeScreenshooter.get_driver_service = MagicMock()
        instance = ChromeScreenshooter(logger=logger)
        assert instance.driver is not None

    data = b"Hello world"
    mock_driver = MagicMock()
    mock_driver.execute_cdp_cmd.return_value = {"data": base64.b64encode(data)}
    instance.driver = mock_driver

    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "file.txt")
        instance.perform_full_page_screenshot(file_path)
        with open(file_path, "rb") as fd:
            assert fd.read() == data

    instance.perform_viewport_screenshot("fake/path")
    mock_driver.get_screenshot_as_file.assert_called_once()


def test_firefox__calls_screenshots():
    logger = logging.getLogger(__name__)
    with patch("shooter.drivers.firefox.webdriver.Firefox"):
        FirefoxScreenshooter.get_driver_service = MagicMock()
        instance = FirefoxScreenshooter(logger=logger)
        assert instance.driver is not None

    mock_driver = MagicMock()
    instance.driver = mock_driver

    instance.perform_full_page_screenshot("fake/path")
    mock_driver.get_full_page_screenshot_as_file.assert_called_once()

    instance.perform_viewport_screenshot("fake/path")
    mock_driver.get_screenshot_as_file.assert_called_once()
