import base64
import os
import typing as ty

from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service
from seleniumwire import webdriver
from webdriver_manager.chrome import ChromeDriverManager

from .base import BaseScreenshooter

CHROMEDRIVER_PATH = os.getenv("CHROMEDRIVER_PATH")


class ChromeScreenshooter(BaseScreenshooter):
    driver: webdriver.Chrome

    @staticmethod
    def get_driver_service(log_path):
        if CHROMEDRIVER_PATH is not None:  # TODO: this hangs up for some reason
            return Service(executable_path=CHROMEDRIVER_PATH, log_path=log_path)
        return Service(ChromeDriverManager().install(), log_path=log_path)

    def setup_driver(
        self,
        window_size: ty.Optional[str] = None,
        user_agent: ty.Optional[str] = None,
        proxy: ty.Optional[str] = None,
        disable_javascript: bool = False,
        headless: bool = True,
        log_path: ty.Optional[str] = None,
        extra_args: ty.Optional[ty.List[str]] = None,
    ) -> webdriver.Chrome:
        """Returns a default WebDriver"""
        seleniumwire_options = {}
        options = ChromeOptions()
        if headless:
            options.add_argument("--headless")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        # options.add_argument(
        #   "--single-process"
        # )  # Causes segmentation fault on 129.0.6668.89*
        options.add_argument("--no-first-run")
        options.add_argument("--no-sandbox")
        options.add_argument("--no-zygote")

        if window_size is not None:
            # Override default device resolution
            self.device_config.width, self.device_config.height = list(
                map(int, window_size.split("x"))
            )

        if user_agent is not None:
            # Override default device `user_agent`
            self.device_config.user_agent = user_agent

        if proxy is not None:
            seleniumwire_options = {
                "proxy": {
                    "http": proxy,
                    "https": proxy,
                    "no_proxy": "localhost,127.0.0.1",
                }
            }

        if self.device_config.is_mobile_view:
            # Activate mobile view mode
            mobile_emulation = {
                "deviceMetrics": {
                    "width": self.device_config.width,
                    "height": self.device_config.height,
                    "pixelRatio": self.device_config.pixel_ratio,
                    "touch": True,
                },
                "userAgent": self.device_config.user_agent,
            }
            options.add_experimental_option("mobileEmulation", mobile_emulation)
        else:
            options.add_argument(
                f"--window-size={self.device_config.get_window_size()}"
            )
            if self.device_config.user_agent is not None:
                options.add_argument(f'--user-agent="{self.device_config.user_agent}"')

        if disable_javascript:
            options.add_argument("--disable-javascript")

        service = self.get_driver_service(log_path=log_path)
        if log_path is not None:
            service.log_path = log_path
            service.enable_verbose_logging = True

        if extra_args:
            for extra_arg in extra_args:
                options.add_argument(extra_arg)

        driver = webdriver.Chrome(
            service=service, options=options, seleniumwire_options=seleniumwire_options
        )
        return driver

    def perform_full_page_screenshot(self, file_path: str) -> None:
        _, ext = os.path.splitext(file_path)
        result = self.driver.execute_cdp_cmd(
            "Page.captureScreenshot",
            {"format": ext[1:], "fromSurface": True, "captureBeyondViewport": True},
        )
        data = result["data"]
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(data))

        self.logger.info(f"Full-page screenshot saved at {file_path}")

    def perform_viewport_screenshot(self, file_path: str) -> None:
        self.driver.get_screenshot_as_file(file_path)
        self.logger.info(f"Viewport screenshot saved at {file_path}")
