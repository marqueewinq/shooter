import abc
import logging
import time
import typing as ty
from functools import partial
from urllib.parse import urlparse

from selenium.common.exceptions import (
    JavascriptException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumwire.webdriver import Chrome, Firefox

from shooter.actions import BaseAction, ScrollToTopAction
from shooter.draw import ElementItem
from shooter.drivers.device import Device, DeviceConfig

WebDriver = ty.NewType("WebDriver", ty.Union[Chrome, Firefox])


class NoDriverRemainingError(BaseException):
    """Raised when Screenshooter runs out of drivers."""


class BaseScreenshooter(abc.ABC):
    logger: logging.Logger

    def __init__(
        self,
        logger: logging.Logger,
        window_size: ty.Optional[str] = None,
        proxy: ty.Optional[
            ty.List[str]
        ] = None,  # Conn strings like: https://{username}:{password}@{hostname}:{port}`
        user_agent: ty.Optional[str] = None,
        device_config: DeviceConfig = Device.DESKTOP.get_device_config(),
        disable_javascript: bool = False,
        headless: bool = True,
        log_path: ty.Optional[str] = None,
        extra_args: ty.Optional[ty.List[str]] = None,
    ) -> None:
        self.logger = logger
        self.device_config = device_config

        # Setup a lazy driver for each proxy
        if not isinstance(proxy, list):
            proxy = [proxy]
        self._setup_driver_list = [
            partial(
                self.setup_driver,
                window_size=window_size,
                user_agent=user_agent,
                proxy=proxy_conn_str,
                disable_javascript=disable_javascript,
                headless=headless,
                log_path=log_path,
                extra_args=extra_args,
            )
            for proxy_conn_str in proxy
        ]
        self._current_driver_index: int = 0
        self._current_driver: ty.Optional[WebDriver] = None

    def __del__(self) -> None:
        try:
            self.driver.quit()
        except NoDriverRemainingError:
            pass

    @property
    def driver(self) -> WebDriver:
        if self._current_driver_index >= len(self._setup_driver_list):
            raise NoDriverRemainingError()
        if self._current_driver is None:
            # Initialize the driver
            self._current_driver = self._setup_driver_list[self._current_driver_index]()
        return self._current_driver

    @driver.setter
    def driver(self, value: WebDriver) -> None:
        self._current_driver = value

    def rotate_driver(self):
        self._current_driver.quit()
        self._current_driver_index += 1
        self._current_driver = None

    def load_page_with_checks(
        self,
        url: str,
        wait_after_load: float = 5,
        wait_before_load: float = 0,
        wait_for_selector: ty.Optional[str] = None,
        wait_for_selector_timeout: float = 10,
    ) -> bool:
        page_loaded = False
        while not page_loaded:
            try:
                self.load_page_and_check(
                    url=url,
                    wait_before_load=wait_before_load,
                    wait_after_load=wait_after_load,
                    wait_for_selector=wait_for_selector,
                    wait_for_selector_timeout=wait_for_selector_timeout,
                )
            except (RuntimeError, TimeoutException) as exc:
                # Rotate the proxy and try again
                self.rotate_driver()
                self.logger.error(exc, exc_info=exc)
                continue
            except NoDriverRemainingError:
                break
            page_loaded = True
        return page_loaded

    @staticmethod
    def _normalize_hostname(hostname: str) -> str:
        return hostname.replace("www.", "")

    def load_page_and_check(
        self,
        url: str,
        wait_after_load: float = 5,
        wait_before_load: float = 0,
        wait_for_selector: ty.Optional[str] = None,
        wait_for_selector_timeout: float = 10,
    ):
        # Wait before the load
        self.logger.info(f"Waiting for {wait_before_load:.2f}s")
        time.sleep(wait_before_load)

        # Load the page
        self.logger.info("Loading the page...")
        self.driver.get(url)

        # Wait after the load
        self.logger.info(f"Waiting for {wait_after_load:.2f}s")
        time.sleep(wait_after_load)
        if wait_for_selector is not None:
            self.wait_for_selector(
                wait_for_selector, wait_for_selector_timeout
            )  # raises TimeoutException

        # Check that the loaded page hostname matches the requested hostname
        expected_hostname = self._normalize_hostname(urlparse(url).hostname)
        current_hostname = self._normalize_hostname(
            urlparse(self.driver.current_url).hostname
        )
        if expected_hostname != current_hostname:
            raise RuntimeError(f"{expected_hostname=} != {current_hostname=}")

    def safe_execute(self, script: str, *args: ty.Any) -> ty.Any:
        try:
            return self.driver.execute_script(script, *args)
        except JavascriptException as exc:
            self.logger.warning(exc, exc_info=exc)

    def take_full_page_screenshot(
        self,
        file_path: str,
        scroll_pause_time: float = 0.1,
        actions: ty.Optional[ty.List[BaseAction]] = None,
    ) -> None:
        if actions is not None:
            # Perform specified actions
            self.perform_actions(
                actions=actions + [ScrollToTopAction()],
                pause_between_actions=scroll_pause_time,
            )

        self.perform_full_page_screenshot(file_path)

    def take_viewport_screenshot(
        self,
        file_path: str,
        scroll_pause_time: float = 0.1,
        actions: ty.Optional[ty.List[BaseAction]] = None,
    ) -> None:
        if actions is not None:
            # Perform specified actions
            self.perform_actions(
                actions=actions, pause_between_actions=scroll_pause_time
            )

        self.perform_viewport_screenshot(file_path)

    def perform_actions(
        self,
        actions: ty.Optional[ty.List[BaseAction]] = None,
        pause_between_actions: float = 0,
    ) -> None:
        for action in actions:
            script = action.to_javascript()
            self.logger.info(f"Performing {action}: {script}")
            self.safe_execute(script)

            self.trigger_reflow()

            self.logger.info(f"Waiting for {pause_between_actions:.2f}s...")
            time.sleep(pause_between_actions)

    def set_viewport_dimensions(self, width: int, height: int) -> None:
        self.driver.set_window_size(width, height)
        self.safe_execute(f"window.resizeTo({width}, {height});")

    def get_root_element(self) -> WebElement:
        return self.driver.find_element(By.CSS_SELECTOR, "html")

    @staticmethod
    def get_parent_element(element: WebElement) -> ty.Optional[WebElement]:
        """Get the parent element for the given one."""
        return element.find_element(By.XPATH, ".//parent::*")

    @staticmethod
    def get_children_elements(element: WebElement) -> ty.Optional[ty.List[WebElement]]:
        return element.find_elements(By.XPATH, "./*")

    @staticmethod
    def get_element_hash(element: WebElement) -> int:
        text = element.get_attribute("outerHTML")
        return text.__hash__()

    def get_elements(
        self,
        full_page_screenshot: bool,
        pixel_ratio: float = 1.0,
        capture_invisible_elements: bool = False,
    ) -> ty.List[ElementItem]:
        """
        Given a WebDriver, finds all relevant elements and returns a list of them with
         adjusted bounding boxes based on the `pixel_ratio`.
        """
        self.trigger_reflow()

        id_to_element: ty.Dict[int, ElementItem] = {}

        def traverse_dom(
            element: WebElement,
            parent_selector: str = "",
            siblings: ty.Optional[ty.List[WebElement]] = None,
            index: ty.Optional[int] = None,
        ):
            element_id = self.get_element_hash(element)
            if element_id in id_to_element:
                return id_to_element[element_id]

            is_visible = element.is_displayed()
            if not (is_visible or capture_invisible_elements):
                return

            rect = self.get_bounding_rect(element, absolute=full_page_screenshot)

            item = ElementItem.from_web_element(
                element=element,
                rect=rect,
                is_visible=is_visible,
                pixel_ratio=pixel_ratio,
                element_index=index,
                siblings=siblings,
                parent_selector=parent_selector,
                element_id=element_id,
                parent_id=None,  # Will be filled later
            )
            id_to_element[element_id] = item

            children = self.get_children_elements(element)
            for child_index, child in enumerate(children):
                try:
                    child_item = traverse_dom(
                        child, item.css_selector, children, child_index
                    )
                except StaleElementReferenceException:
                    # WebElement has been dynamically removed from the page
                    continue
                if child_item:
                    child_item.parent_id = element_id

            return item

        root_element = self.get_root_element()
        if root_element is None:
            return []
        try:
            traverse_dom(root_element)
        except StaleElementReferenceException:
            # Root element has been removed
            return []
        return list(id_to_element.values())

    def get_bounding_rect(self, element: WebElement, absolute: bool) -> dict:
        if absolute:
            # Fetch absolute element positions
            location = element.location
            size = element.size
            return {
                "left": location["x"],
                "top": location["y"],
                "width": size["width"],
                "height": size["height"],
            }
        # Fetch element position relative to the client (viewport)
        return self.safe_execute(
            """
            var elem = arguments[0];
            var rect = elem.getBoundingClientRect();
            return {
                left: rect.left,
                top: rect.top,
                width: rect.width,
                height: rect.height
            };
        """,
            element,
        )

    def trigger_reflow(self) -> None:
        self.safe_execute(
            "return document.body.offsetHeight;"
        )  # This triggers reflow of the whole DOM

    def wait_for_selector(self, css_selector: str, timeout: float = 10) -> None:
        WebDriverWait(self.driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css_selector))
        )

    @abc.abstractmethod
    def setup_driver(
        self,
        window_size: ty.Optional[str] = None,
        user_agent: ty.Optional[str] = None,
        proxy: ty.Optional[str] = None,
        disable_javascript: bool = False,
        headless: bool = True,
        log_path: ty.Optional[str] = None,
        extra_args: ty.Optional[ty.List[str]] = None,
    ) -> WebDriver:
        raise NotImplementedError

    @abc.abstractmethod
    def perform_full_page_screenshot(self, file_path: str) -> None:
        raise NotImplementedError

    @abc.abstractmethod
    def perform_viewport_screenshot(self, file_path: str) -> None:
        raise NotImplementedError
