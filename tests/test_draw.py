import json
from unittest import mock

import pytest

from shooter.draw import ElementItem, draw_elements_from_file, draw_elements_on_image


@pytest.fixture
def mock_cv2():
    with mock.patch(
        "cv2.imread", return_value=mock.MagicMock()
    ) as mock_imread, mock.patch(
        "cv2.rectangle", return_value=mock.MagicMock()
    ) as mock_rectangle, mock.patch(
        "cv2.putText", return_value=mock.MagicMock()
    ) as mock_put_text, mock.patch(
        "cv2.imwrite", return_value=True
    ) as mock_imwrite:
        yield mock_imread, mock_rectangle, mock_put_text, mock_imwrite


def test_draw_elements_on_image(mock_cv2):
    mock_imread, mock_rectangle, mock_put_text, mock_imwrite = mock_cv2
    image_path = "test_image.jpg"
    output_path = "output_image.jpg"
    # fmt: off
    element_data = [
        ElementItem(id="0", bbox=(10, 10, 100, 100), tag_name="div", label="Div Element", position="", is_visible=True, css_selector=""),
        ElementItem(id="1", bbox=(110, 110, 200, 200), tag_name="text_box", label="Text Box", position="", is_visible=True, css_selector=""),
        ElementItem(id="2", bbox=(210, 210, 300, 300), tag_name="img", label="Image Element", position="", is_visible=True, css_selector=""),
        ElementItem(id="3", bbox=(310, 310, 400, 400), tag_name="unknown", label="Unknown Element", position="", is_visible=True, css_selector=""),
        ElementItem(id="4", bbox=(410, 410, 500, 500), tag_name="div", label="Fixed Element", position="fixed", is_visible=True, css_selector=""),
    ]
    # fmt: on

    draw_elements_on_image(image_path, element_data, output_path)

    mock_imread.assert_called_once_with(image_path)
    assert mock_rectangle.call_count == 5
    assert mock_put_text.call_count == 5
    mock_imwrite.assert_called_once_with(output_path, mock.ANY)


@pytest.fixture
def mock_open_and_json():
    # fmt: off
    data = [
        {"id": "0", "bbox": [10, 10, 100, 100], "tag_name": "div", "label": "Div Element", "position": "", "is_visible": True, "css_selector": ""},
        {"id": "1", "bbox": [110, 110, 200, 200], "tag_name": "text_box", "label": "Text Box", "position": "", "is_visible": True, "css_selector": ""},
        {"id": "2", "bbox": [210, 210, 300, 300], "tag_name": "img", "label": "Image Element", "position": "", "is_visible": True, "css_selector": ""},
        {"id": "3", "bbox": [310, 310, 400, 400], "tag_name": "unknown", "label": "Unknown Element", "position": "", "is_visible": True, "css_selector": ""},
        {"id": "4", "bbox": [410, 410, 500, 500], "tag_name": "div", "label": "Fixed Element", "position": "fixed", "is_visible": True, "css_selector": ""}
    ]
    mock_open = mock.mock_open(read_data=json.dumps(data))
    # fmt: on
    with mock.patch("builtins.open", mock_open), mock.patch(
        "json.load", return_value=data
    ) as mock_json_load:
        yield mock_open, mock_json_load


def test_draw_elements_from_file(mock_open_and_json, mock_cv2):
    mock_open, mock_json_load = mock_open_and_json
    mock_imread, mock_rectangle, mock_put_text, mock_imwrite = mock_cv2
    image_path = "test_image.jpg"
    elements_path = "elements.json"
    output_path = "output_image.jpg"

    draw_elements_from_file(image_path, elements_path, output_path)

    mock_open.assert_called_once_with(elements_path)
    mock_json_load.assert_called_once()
    mock_imread.assert_called_once_with(image_path)
    assert mock_rectangle.call_count == 5
    assert mock_put_text.call_count == 5
    mock_imwrite.assert_called_once_with(output_path, mock.ANY)
