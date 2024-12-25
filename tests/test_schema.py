from unittest.mock import MagicMock

import pytest

from shooter.actions import (
    ClickAtAction,
    ClickElementAction,
    ScrollDownAction,
    ScrollToTopAction,
    ScrollUpAction,
)
from shooter.app import TakeScreenshotConfig, TakeScreenshotRequest
from shooter.drivers.device import Device
from shooter.schema import BrowserChoice, ProxyConfig, TaskProgressResponse


@pytest.mark.parametrize(
    "data",
    [
        {"sites": ["https://shop.cravt.by/"]},
        {"sites": [{"url": "https://shop.cravt.by/"}]},
        {
            "sites": [
                "https://shop.cravt.by/",
                {"url": "https://sochipark.ru", "device": "IPHONE_X"},
                {"url": "https://sochipark.ru", "browser": "firefox"},
            ]
        },
    ],
)
def test_validation__ok(data):
    instance = TakeScreenshotRequest(**data)  # Assert does not throw ValidationError
    instance.dict()  # Assert does not throw ValueError


def test_validation__window_size_incorrect():
    with pytest.raises(ValueError) as err:
        TakeScreenshotConfig(window_size="100500")

    assert (
        "window_size must be in the format 'widthxheight', e.g., '1920x1080'."
        in str(err.value)
    )


@pytest.mark.parametrize(
    "data, expected",
    [
        # Test without default_config
        (
            {"sites": ["https://example.com"]},
            [
                TakeScreenshotConfig(url="https://example.com"),
            ],
        ),
        # Test without default_config
        (
            {"sites": [{"url": "https://example.com"}]},
            [
                TakeScreenshotConfig(url="https://example.com"),
            ],
        ),
        # Test default application with a single URL (string)
        (
            {
                "sites": ["https://example.com"],
                "default_config": {"wait_after_load": 100500},
            },
            [
                TakeScreenshotConfig(
                    url="https://example.com",
                    wait_after_load=100500,
                )
            ],
        ),
        # Test with multiple configurations, ensuring default values are applied and overridden properly
        (
            {
                "sites": [
                    {
                        "url": "https://example.com",
                        "full_page_screenshot": False,
                        "window_size": "100x200",
                        "actions": [{"kind": "scroll_down", "how_much": 100}],
                    },
                    {
                        "url": "https://example.com",
                        "actions": [{"kind": "scroll_up", "how_much": 300}],
                        "wait_after_load": 5000,
                        "wait_before_load": 10,
                    },
                ],
                "default_config": {
                    "capture_visible_elements": False,
                    "device": "IPHONE_X",
                    "wait_after_load": 1000,
                    "full_page_screenshot": True,
                },
            },
            [
                TakeScreenshotConfig(
                    url="https://example.com",
                    full_page_screenshot=False,
                    actions=[ScrollDownAction(how_much=100)],
                    window_size="100x200",
                    capture_visible_elements=False,
                    device=Device.IPHONE_X,
                    wait_after_load=1000,
                ),
                TakeScreenshotConfig(
                    url="https://example.com",
                    actions=[ScrollUpAction(how_much=300)],
                    capture_visible_elements=False,
                    device=Device.IPHONE_X,
                    full_page_screenshot=True,
                    wait_after_load=5000,
                    wait_before_load=10,
                ),
            ],
        ),
        # Test where only default config is provided, which should also apply
        (
            {
                "sites": [{"url": "https://example.com"}],
                "default_config": {"device": "IPHONE_15"},
            },
            [TakeScreenshotConfig(url="https://example.com", device=Device.IPHONE_15)],
        ),
        # Test when actions is explicitly None
        (
            {
                "sites": [
                    "https://example.com",
                    {"url": "https://another-example.com", "actions": None},
                ],
                "default_config": {"actions": None},
            },
            [
                TakeScreenshotConfig(
                    url="https://example.com",
                    actions=None,
                ),
                TakeScreenshotConfig(
                    url="https://another-example.com",
                    actions=None,
                ),
            ],
        ),
        # Test all possible actions
        (
            {
                "sites": [
                    {
                        "url": "https://example.com",
                        "actions": [
                            {"kind": "scroll_down", "how_much": 100},
                            {"kind": "scroll_up", "how_much": 200},
                            {"kind": "scroll_to_top"},
                            {"kind": "click_at", "click_x": 300, "click_y": 400},
                            {"kind": "click_element", "element_id": "element_id"},
                            {"kind": "click_element", "element_class": "element_class"},
                            {
                                "kind": "click_element",
                                "element_query_selector": "element_query_selector",
                            },
                        ],
                    }
                ]
            },
            [
                TakeScreenshotConfig(
                    url="https://example.com",
                    actions=[
                        ScrollDownAction(how_much=100),
                        ScrollUpAction(how_much=200),
                        ScrollToTopAction(),
                        ClickAtAction(click_x=300, click_y=400),
                        ClickElementAction(element_id="element_id"),
                        ClickElementAction(element_class="element_class"),
                        ClickElementAction(
                            element_query_selector="element_query_selector"
                        ),
                    ],
                )
            ],
        ),
        # Test when browser is set
        (
            {
                "sites": [
                    "https://example.com",
                    {
                        "url": "https://another-example.com",
                        "browser": BrowserChoice.FIREFOX.value,
                    },
                ],
            },
            [
                TakeScreenshotConfig(
                    url="https://example.com",
                ),
                TakeScreenshotConfig(
                    url="https://another-example.com",
                    browser=BrowserChoice.FIREFOX,
                ),
            ],
        ),
        # Test when the proxy is set
        (
            {
                "sites": [
                    {
                        "url": "https://example.com",
                        "proxy": {
                            "host": "aba.caba.io",
                            "port": 9000,
                            "username": "hello",
                            "password": "abcde12345!@#$%",
                        },
                    }
                ]
            },
            [
                TakeScreenshotConfig(
                    url="https://example.com",
                    proxy=ProxyConfig(
                        host="aba.caba.io",
                        port=9000,
                        username="hello",
                        password="abcde12345!@#$%",
                    ),
                )
            ],
        ),
        # Test when wait_for_selector is specified
        (
            {
                "sites": [
                    {"url": "https://example.com", "wait_for_selector": "html div a"},
                    {
                        "url": "https://example.com",
                        "wait_for_selector": "html div a",
                        "wait_for_selector_timeout": 5.0,
                    },
                ]
            },
            [
                TakeScreenshotConfig(
                    url="https://example.com",
                    wait_for_selector="html div a",
                    wait_for_selector_timeout=10.0,
                ),
                TakeScreenshotConfig(
                    url="https://example.com",
                    wait_for_selector="html div a",
                    wait_for_selector_timeout=5.0,
                ),
            ],
        ),
    ],
)
def test_validation__default_config_overrides(data, expected):
    request = TakeScreenshotRequest(**data)
    assert request.sites == expected, f"Failed for input data {data}"
    [it.dict() for it in request.sites]  # Assert foes not fail


@pytest.mark.parametrize(
    "invalid_payload",
    [
        {},
        {"url": None},
        {"url": 100500},
    ],
)
def test_validation__url_is_provided_checked(invalid_payload):
    with pytest.raises(ValueError) as err:
        TakeScreenshotRequest(**{"sites": [invalid_payload]})

    assert "url" in str(err.value).lower()


@pytest.mark.parametrize(
    "instance,expected",
    [
        # Basic test
        (
            ProxyConfig(
                host="aba.caba.io",
                port=9000,
                username="hello",
                password="world",
            ),
            "https://hello:world@aba.caba.io:9000",
        ),
        # Test when password should be encoded
        (
            ProxyConfig(
                host="aba.caba.io",
                port=9000,
                username="hello",
                password="wor;ld;!@#$%^&*()",
            ),
            "https://hello:wor%3Bld%3B%21%40%23%24%25%5E%26%2A%28%29@aba.caba.io:9000",
        ),
    ],
)
def test_validation__ProxyConfig_get_connection_string__ok(instance, expected):
    assert instance.get_connection_string() == expected


@pytest.mark.parametrize(
    "async_result_list, expected",
    [
        # fmt: off
        # all tasks are successful
        (
            [
                MagicMock(ready=MagicMock(return_value=True), successful=MagicMock(return_value=True), state="SUCCESS"),
                MagicMock(ready=MagicMock(return_value=True), successful=MagicMock(return_value=True), state="SUCCESS"),
                MagicMock(ready=MagicMock(return_value=True), successful=MagicMock(return_value=True), state="SUCCESS")
            ],
            TaskProgressResponse(completed=3, failed=0, total=3, state="SUCCESS", all_successful=True, ready=True)
        ),
        # some tasks are pending
        (
            [
                MagicMock(ready=MagicMock(return_value=False), state="PENDING"),
                MagicMock(ready=MagicMock(return_value=True), successful=MagicMock(return_value=True), state="SUCCESS"),
                MagicMock(ready=MagicMock(return_value=True), successful=MagicMock(return_value=False), state="FAILURE")
            ],
            TaskProgressResponse(completed=1, failed=1, total=3, state="PENDING", all_successful=False, ready=False)
        ),
        # all tasks are failed
        (
            [
                MagicMock(ready=MagicMock(return_value=True), successful=MagicMock(return_value=False), state="FAILURE"),
                MagicMock(ready=MagicMock(return_value=True), successful=MagicMock(return_value=False), state="FAILURE"),
                MagicMock(ready=MagicMock(return_value=True), successful=MagicMock(return_value=False), state="FAILURE")
            ],
            TaskProgressResponse(completed=0, failed=3, total=3, state="FAILURE", all_successful=False, ready=True)
        ),
        # there are mixed results and some are unknown
        (
            [
                MagicMock(ready=MagicMock(return_value=True), successful=MagicMock(return_value=True), state="SUCCESS"),
                MagicMock(ready=MagicMock(return_value=True), successful=MagicMock(return_value=False), state="FAILURE"),
                MagicMock(ready=MagicMock(return_value=False), state="PENDING")
            ],
            TaskProgressResponse(completed=1, failed=1, total=3, state="PENDING", all_successful=False, ready=False)
        ),
        # state is unknown
        (
            [

            ],
            TaskProgressResponse(completed=0, failed=0, total=0, state="UNKNOWN", all_successful=False, ready=True)
        ),
        # fmt: on
    ],
)
def test_from_async_result_list(async_result_list, expected):
    response = TaskProgressResponse.from_async_result_list(async_result_list)
    assert response == expected


@pytest.mark.parametrize(
    "url",
    [
        "example.com",  # Missing protocol
        "https://example..com",  # Consecutive dots
        "https://example..com/path",  # Consecutive dots with path
        "https://example.com:99999",  # Invalid port number
        "ftp://example.com",  # Incorrect protocol
    ],
)
def test_validate_url__raises(url):
    with pytest.raises(ValueError):
        TakeScreenshotConfig(url=url)
