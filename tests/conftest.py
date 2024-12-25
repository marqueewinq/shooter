import typing as ty
from unittest.mock import MagicMock

import pytest

from shooter.drivers.base import BaseScreenshooter


@pytest.fixture
def mock_logger():
    yield MagicMock(name="logger")


@pytest.fixture
def test_screenshooter_class():
    class TestScreenshooter(BaseScreenshooter):
        js_executed = []
        elements = []

        def get_root_element(self):
            return self.elements[0] if len(self.elements) > 0 else None

        def get_children_elements(self, element):
            result = []
            for other in self.elements:
                if other.parent is None:
                    continue
                if other.parent.id == element.id:
                    result.append(other)
            return result

        @staticmethod
        def get_parent_element(element):
            return element.parent

        def get_bounding_rect(self, element, absolute: bool) -> dict:
            return {
                "left": 1,
                "top": 2,
                "width": 3,
                "height": 4,
            }

        @staticmethod
        def get_element_hash(element) -> int:
            return element.id

        def safe_execute(self, script: str, *args: ty.Any) -> ty.Any:
            self.js_executed.append(script)

        def setup_driver(self, *args, **kwargs):
            return MagicMock(name="driver", **kwargs)

        def perform_full_page_screenshot(self, file_path: str):
            self.driver.perform_full_page_screenshot(file_path)

        def perform_viewport_screenshot(self, file_path: str):
            self.driver.perform_viewport_screenshot(file_path)

    return TestScreenshooter


@pytest.fixture
def test_screenshooter(test_screenshooter_class, mock_logger):
    yield test_screenshooter_class(logger=mock_logger)
