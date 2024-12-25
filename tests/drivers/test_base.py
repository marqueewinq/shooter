from unittest.mock import MagicMock

import pytest
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException

from shooter.draw import ElementItem
from shooter.drivers.base import NoDriverRemainingError


def _create_element(
    element_id,
    tag_name,
    displayed=True,
    position="static",
    parent=None,
    id_attr=None,
    class_attr=None,
):
    element = MagicMock()
    element.id = element_id
    element.tag_name = tag_name
    element.is_displayed.return_value = displayed
    element.value_of_css_property.return_value = position
    element.position = position
    element.get_attribute.side_effect = lambda attr: {
        "id": id_attr,
        "class": class_attr if class_attr else None,
    }.get(attr, "")
    # Setting up rect mock properly
    element.get_bounding_rect.return_value = {
        "left": 10,
        "top": 20,
        "width": 100,
        "height": 200,
    }
    element.parent = parent
    return element


def _check_get_elements_results(actual, expected):
    assert len(actual) == len(expected)
    for act, exp in zip(
        sorted(actual, key=lambda x: x.id), sorted(expected, key=lambda x: x.id)
    ):
        assert act.id == exp.id
        assert act.parent_id == exp.parent_id
        assert act.css_selector == exp.css_selector


_common_kwargs = dict(
    bbox=(10, 20, 110, 220), position="static", is_visible=True, css_selector=""
)


@pytest.mark.parametrize(
    "elements, expected",
    [
        ([], []),
        (
            [_create_element(1, "div", id_attr="main", class_attr="container")],
            [
                ElementItem(
                    id=1,
                    parent_id=None,
                    tag_name="div",
                    bbox=(10, 20, 110, 220),
                    label="div",
                    position="static",
                    is_visible=True,
                    css_selector="div#main.container",
                )
            ],
        ),
        (
            [
                _create_element(1, "div", id_attr="header"),
                _create_element(
                    2,
                    "span",
                    class_attr="title",
                    parent=_create_element(1, "div", id_attr="header"),
                ),
            ],
            [
                ElementItem(
                    id=1,
                    parent_id=None,
                    tag_name="div",
                    bbox=(10, 20, 110, 220),
                    label="div",
                    position="static",
                    is_visible=True,
                    css_selector="div#header",
                ),
                ElementItem(
                    id=2,
                    parent_id=1,
                    tag_name="span",
                    bbox=(10, 20, 110, 220),
                    label="span",
                    position="static",
                    is_visible=True,
                    css_selector="div#header span.title",
                ),
            ],
        ),
        (
            [
                _create_element(1, "div", class_attr="content"),
                _create_element(
                    2, "span", parent=_create_element(1, "div", class_attr="content")
                ),
                _create_element(
                    3,
                    "p",
                    parent=_create_element(
                        2,
                        "span",
                        parent=_create_element(1, "div", class_attr="content"),
                    ),
                ),
            ],
            [
                ElementItem(
                    id=1,
                    parent_id=None,
                    tag_name="div",
                    bbox=(10, 20, 110, 220),
                    label="div",
                    position="static",
                    is_visible=True,
                    css_selector="div.content",
                ),
                ElementItem(
                    id=2,
                    parent_id=1,
                    tag_name="span",
                    bbox=(10, 20, 110, 220),
                    label="span",
                    position="static",
                    is_visible=True,
                    css_selector="div.content span",
                ),
                ElementItem(
                    id=3,
                    parent_id=2,
                    tag_name="p",
                    bbox=(10, 20, 110, 220),
                    label="p",
                    position="static",
                    is_visible=True,
                    css_selector="div.content span p",
                ),
            ],
        ),
        (
            [
                _create_element(1, "div"),
                _create_element(
                    2,
                    "input",
                    class_attr="search",
                    parent=_create_element(1, "div"),
                    id_attr="searchBox",
                ),
                _create_element(3, "h1", parent=_create_element(1, "div")),
            ],
            [
                ElementItem(
                    id=1,
                    parent_id=None,
                    tag_name="div",
                    bbox=(10, 20, 110, 220),
                    label="div",
                    position="static",
                    is_visible=True,
                    css_selector="div",
                ),
                ElementItem(
                    id=2,
                    parent_id=1,
                    tag_name="input",
                    bbox=(10, 20, 110, 220),
                    label="input",
                    position="static",
                    is_visible=True,
                    css_selector="div input#searchBox.search",
                ),
                ElementItem(
                    id=3,
                    parent_id=1,
                    tag_name="h1",
                    bbox=(10, 20, 110, 220),
                    label="h1",
                    position="static",
                    is_visible=True,
                    css_selector="div h1",
                ),
            ],
        ),
    ],
)
def test_get_elements(test_screenshooter, elements, expected):
    # Mock the behavior as if elements were found by Selenium
    for element in elements:
        element.find_elements.return_value = elements
        element.find_element.return_value = element

    test_screenshooter.elements = elements
    actual = test_screenshooter.get_elements(full_page_screenshot=True, pixel_ratio=1.0)
    _check_get_elements_results(actual, expected)


def test_get_elements__handles_stale_elements(test_screenshooter):
    dynamically_removed_element = _create_element(
        3, "h1", parent=_create_element(1, "div")
    )
    dynamically_removed_element.get_attribute.side_effect = (
        StaleElementReferenceException
    )
    dynamically_removed_element.is_displayed.side_effect = (
        StaleElementReferenceException
    )

    test_screenshooter.elements = [
        _create_element(1, "div"),
        _create_element(
            2,
            "input",
            class_attr="search",
            parent=_create_element(1, "div"),
            id_attr="searchBox",
        ),
        dynamically_removed_element,
    ]
    expected = [
        ElementItem(
            id=1,
            parent_id=None,
            tag_name="div",
            bbox=(10, 20, 110, 220),
            label="div",
            position="static",
            is_visible=True,
            css_selector="div",
        ),
        ElementItem(
            id=2,
            parent_id=1,
            tag_name="input",
            bbox=(10, 20, 110, 220),
            label="input",
            position="static",
            is_visible=True,
            css_selector="div input#searchBox.search",
        ),
    ]

    actual = test_screenshooter.get_elements(full_page_screenshot=True, pixel_ratio=1.0)

    _check_get_elements_results(actual, expected)


def test_get_elements__handles_stale_elements_if_root(test_screenshooter):
    dynamically_removed_element = _create_element(
        3, "h1", parent=_create_element(1, "div")
    )
    dynamically_removed_element.get_attribute.side_effect = (
        StaleElementReferenceException
    )
    dynamically_removed_element.is_displayed.side_effect = (
        StaleElementReferenceException
    )

    test_screenshooter.elements = [dynamically_removed_element]
    expected = []

    actual = test_screenshooter.get_elements(full_page_screenshot=True, pixel_ratio=1.0)

    _check_get_elements_results(actual, expected)


def test_screenshooter__with_proxy_str(
    test_screenshooter_class,
    mock_logger,
):
    proxy = "proxy://connection:string"
    test_screenshooter = test_screenshooter_class(logger=mock_logger, proxy=proxy)

    driver = test_screenshooter.driver
    assert driver.proxy == proxy

    test_screenshooter.rotate_driver()
    with pytest.raises(NoDriverRemainingError):
        _ = test_screenshooter.driver


def test_screenshooter__with_proxy_list(
    test_screenshooter_class,
    mock_logger,
):
    proxy0 = "proxy://connection:string"
    proxy1 = "another-proxy://connection:string"
    test_screenshooter = test_screenshooter_class(
        logger=mock_logger,
        proxy=[proxy0, proxy1],
    )

    driver = test_screenshooter.driver
    assert driver.proxy == proxy0

    test_screenshooter.rotate_driver()
    driver = test_screenshooter.driver
    assert driver.proxy == proxy1

    test_screenshooter.rotate_driver()
    with pytest.raises(NoDriverRemainingError):
        _ = test_screenshooter.driver


def test_screenshooter__load_page_with_checks(mock_logger, test_screenshooter_class):
    proxy0 = "proxy://connection:string"

    class TestScreenshooterMockLoad(test_screenshooter_class):
        n_tries = 0

        def load_page_and_check(self, url, *args, **kwargs):
            _ = self.driver  # Evaluate the driver
            self.n_tries += 1
            if self.n_tries == 1:
                raise RuntimeError()
            if self.n_tries == 2:
                raise TimeoutException()

    test_screenshooter = TestScreenshooterMockLoad(
        logger=mock_logger,
        proxy=[proxy0, proxy0, proxy0],
    )
    test_screenshooter.driver.current_url = "url"

    test_screenshooter.load_page_with_checks("url")
    assert test_screenshooter.n_tries == 3
