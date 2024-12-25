import os
import typing as ty

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from seleniumwire import webdriver
from webdriver_manager.core.driver_cache import DriverCacheManager
from webdriver_manager.firefox import GeckoDriverManager

from .base import BaseScreenshooter

GECKODRIVER_PATH = os.getenv("GECKODRIVER_PATH")


class FirefoxScreenshooter(BaseScreenshooter):
    driver: webdriver.Firefox

    @staticmethod
    def get_driver_service(log_path):
        if GECKODRIVER_PATH is not None:
            return Service(executable_path=GECKODRIVER_PATH, log_path=log_path)
        return Service(
            GeckoDriverManager(cache_manager=DriverCacheManager()).install(),
            log_path=log_path,
        )

    def setup_driver(
        self,
        window_size: ty.Optional[str] = None,
        user_agent: ty.Optional[str] = None,
        proxy: ty.Optional[str] = None,
        disable_javascript: bool = False,
        headless: bool = True,
        log_path: ty.Optional[str] = None,
        extra_args: ty.Optional[ty.List[str]] = None,
    ) -> webdriver.Firefox:
        """Sets up and returns a Firefox WebDriver."""
        seleniumwire_options = {}
        options = FirefoxOptions()
        if headless:
            options.add_argument("--headless")

        if window_size is not None:
            # Override default device resolution
            self.device_config.width, self.device_config.height = list(
                map(int, window_size.split("x"))
            )

        if user_agent is not None:
            # Override default device `user_agent`
            self.device_config.user_agent = user_agent

        if proxy is not None:
            # Because https://github.com/SeleniumHQ/selenium/issues/7911
            #  and https://bugzilla.mozilla.org/show_bug.cgi?id=1395886 the selenium
            #  does not support proxying for firefox driver directly. We'll use
            #  selenium-wire to configure the proxy.
            seleniumwire_options = {
                "proxy": {
                    "http": proxy,
                    "https": proxy,
                    "no_proxy": "localhost,127.0.0.1",
                }
            }

        if self.device_config.is_mobile_view:
            self.device_config.pixel_ratio = (
                1.0  # Pixel ratio is always 1.0 for Firefox
            )

        options.add_argument(f"--width={self.device_config.width}")
        options.add_argument(f"--height={self.device_config.height}")

        if self.device_config.user_agent is not None:
            options.set_preference(
                "general.useragent.override", self.device_config.user_agent
            )

        if disable_javascript:
            options.set_preference("javascript.enabled", False)

        service = self.get_driver_service(log_path=log_path)
        if extra_args:
            for extra_arg in extra_args:
                options.add_argument(extra_arg)

        driver = webdriver.Firefox(
            service=service, options=options, seleniumwire_options=seleniumwire_options
        )
        return driver

    def perform_full_page_screenshot(self, file_path: str) -> None:
        self.driver.get_full_page_screenshot_as_file(file_path)
        self.logger.info(f"Full-page screenshot saved at {file_path}")

    def perform_viewport_screenshot(self, file_path: str) -> None:
        self.driver.get_screenshot_as_file(file_path)
        self.logger.info(f"Viewport screenshot saved at {file_path}")
