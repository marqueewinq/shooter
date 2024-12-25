import tempfile
from unittest.mock import MagicMock, patch

import pytest

from shooter.actions import ScrollDownAction, ScrollUpAction
from shooter.draw import ElementItem
from shooter.drivers import ChromeScreenshooter, FirefoxScreenshooter
from shooter.schema import BrowserChoice
from shooter.__main__ import browser_to_screenshooter_class, make_screenshot_from_url


@pytest.mark.parametrize(
    "full_page_screenshot,scroll_actions,expected_call,expected_file_mode",
    [
        (True, [], "captureScreenshot", "wb"),
        (False, [], "get_screenshot_as_file", "w"),
        (True, [("down", 100)], "captureScreenshot", "wb"),
        (False, [("up", 50)], "get_screenshot_as_file", "w"),
    ],
)
def test_take_page_screenshot(
    full_page_screenshot,
    scroll_actions,
    expected_call,
    expected_file_mode,
    test_screenshooter,
):
    height = 123
    driver_mock = MagicMock()
    logger_mock = MagicMock()
    body_mock = MagicMock()
    driver_mock.find_element.return_value = body_mock
    driver_mock.get_window_size.return_value = {"height": height}

    test_screenshooter.driver = driver_mock
    test_screenshooter.logger = logger_mock

    file_path = "/fake/path.png"

    def scroll_actions_to_actions(scroll_actions):
        actions = [
            ScrollDownAction(how_much=how_much)
            if where == "down"
            else ScrollUpAction(how_much=how_much)
            for where, how_much in scroll_actions
        ]
        if len(actions) == 0:
            return None
        return actions

    def assert_actions_called(scroll_actions):
        actions = scroll_actions_to_actions(scroll_actions)
        if actions is None:
            return
        for ac in actions:
            expected_script = ac.to_javascript()
            print(test_screenshooter.js_executed)
            assert expected_script in test_screenshooter.js_executed

    actions = scroll_actions_to_actions(scroll_actions)
    with patch("base64.b64decode", return_value=b"data"), patch("time.sleep"), patch(
        "os.path.splitext", return_value=("/fake/path", ".png")
    ):
        if full_page_screenshot:
            test_screenshooter.take_full_page_screenshot(
                file_path=file_path,
                scroll_pause_time=0.1,
                actions=actions,
            )
            if scroll_actions:
                assert_actions_called(scroll_actions)

            driver_mock.perform_full_page_screenshot.assert_called_once_with(file_path)
        else:
            test_screenshooter.take_viewport_screenshot(
                file_path=file_path,
                scroll_pause_time=0.1,
                actions=actions,
            )

            assert_actions_called(scroll_actions)
            driver_mock.perform_viewport_screenshot.assert_called_once_with(file_path)

        if not scroll_actions and not full_page_screenshot:
            driver_mock.execute_script.assert_not_called()


def test_get_all_elements(test_screenshooter, mock_logger):
    driver_mock = MagicMock()
    elements_mock = [MagicMock() for _ in range(3)]
    elements_mock[0].id = "0"
    elements_mock[0].location = {"x": 10, "y": 20}
    elements_mock[0].size = {"width": 100, "height": 200}
    elements_mock[0].get_attribute.return_value = "outerHTML"
    elements_mock[0].tag_name = "input"
    elements_mock[0].get_attribute.return_value = "text"
    elements_mock[0].value_of_css_property.return_value = "fixed"
    elements_mock[0].is_displayed.return_value = True
    elements_mock[0].parent = None

    elements_mock[1].id = "1"
    elements_mock[1].location = {"x": 30, "y": 40}
    elements_mock[1].size = {"width": 150, "height": 250}
    elements_mock[1].get_attribute.return_value = "outerHTML"
    elements_mock[1].tag_name = "h1"
    elements_mock[1].value_of_css_property.return_value = "absolute"
    elements_mock[1].is_displayed.return_value = True
    elements_mock[1].parent = elements_mock[0]

    # Add an invisible element
    elements_mock[2].id = "2"
    elements_mock[2].location = {"x": 50, "y": 60}
    elements_mock[2].size = {"width": 250, "height": 350}
    elements_mock[2].get_attribute.return_value = "outerHTML"
    elements_mock[2].tag_name = "div"
    elements_mock[2].value_of_css_property.return_value = "absolute"
    elements_mock[2].is_displayed.return_value = False
    elements_mock[2].parent = None

    driver_mock.find_elements.return_value = elements_mock
    test_screenshooter.driver = driver_mock
    test_screenshooter.elements = elements_mock

    element_data = test_screenshooter.get_elements(driver_mock)

    assert len(element_data) == 2, "Should return data for two visible elements"
    assert all([isinstance(it, ElementItem) for it in element_data])


@pytest.mark.parametrize("full_page_screenshot", [True, False])
@patch("shooter.__main__.draw_elements_on_image")
def test_make_screenshot_from_url(
    draw_mock,
    test_screenshooter,
    full_page_screenshot,
):
    driver_mock = MagicMock()

    url = "http://example.com"
    elements_mock = [MagicMock()]
    elements_mock[0].id = "0"
    elements_mock[0].location = {"x": 10, "y": 20}
    elements_mock[0].size = {"width": 100, "height": 200}
    elements_mock[0].get_attribute.return_value = "outerHTML"
    elements_mock[0].tag_name = "div"
    elements_mock[0].get_attribute.return_value = "text"
    elements_mock[0].value_of_css_property.return_value = "fixed"
    elements_mock[0].parent = None
    logger_mock = MagicMock()

    driver_mock.current_url = url
    driver_mock.find_elements.return_value = elements_mock

    test_screenshooter.driver = driver_mock
    test_screenshooter.logger = logger_mock
    test_screenshooter.elements = elements_mock

    def browser_to_screenshooter_class(browser):
        return {"test": lambda *args, **kwargs: test_screenshooter}[browser]

    with patch(
        "shooter.__main__.browser_to_screenshooter_class",
        browser_to_screenshooter_class,
    ), tempfile.TemporaryDirectory() as tmpdir:
        make_screenshot_from_url(
            url,
            tmpdir,
            browser="test",
            wait_after_load=0,
            wait_before_load=0,
            logger=logger_mock,
            full_page_screenshot=full_page_screenshot,
        )
        driver_mock.get.assert_called_once_with(url)
        if full_page_screenshot:
            driver_mock.perform_full_page_screenshot.assert_called_once()
        else:
            driver_mock.perform_viewport_screenshot.assert_called_once()
        draw_mock.assert_called_once()


@pytest.mark.parametrize(
    "key,expected_type",
    [
        (BrowserChoice.FIREFOX.value, FirefoxScreenshooter),
        (BrowserChoice.CHROME.value, ChromeScreenshooter),
    ],
)
def test_browser_to_screenshooter_class(key, expected_type):
    """
    Tests that BrowserChoice values are aligned with browser_to_screenshooter_class
     function.
    """
    actual_type = browser_to_screenshooter_class(key)
    assert actual_type == expected_type
