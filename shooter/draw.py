import json
import typing as ty

import cv2
from selenium.webdriver.remote.webelement import WebElement

from shooter.base import BaseModel


class ElementItem(BaseModel):
    id: int
    parent_id: ty.Optional[int] = None

    bbox: ty.Tuple[int, int, int, int]
    tag_name: str
    label: str
    position: str
    is_visible: bool
    css_selector: str

    @classmethod
    def from_web_element(
        cls,
        element: WebElement,
        rect: dict,
        is_visible: bool,
        pixel_ratio: float,
        element_index: ty.Optional[int],
        siblings: ty.List[WebElement],
        parent_selector: str,
        element_id: int,
        parent_id: ty.Optional[int] = None,
    ) -> "ElementItem":
        bbox = (
            int(rect["left"] * pixel_ratio),
            int(rect["top"] * pixel_ratio),
            int((rect["left"] + rect["width"]) * pixel_ratio),
            int((rect["top"] + rect["height"]) * pixel_ratio),
        )
        tag_name = element.tag_name
        position = element.value_of_css_property("position")
        css_selector = cls.get_css_selector(
            element=element,
            element_index=element_index,
            siblings=siblings,
            parent_selector=parent_selector,
        )

        return cls(
            id=element_id,
            parent_id=parent_id,
            bbox=bbox,
            tag_name=tag_name,
            label=tag_name,
            position=position,
            is_visible=is_visible,
            css_selector=css_selector,
        )

    @staticmethod
    def get_css_selector(
        element: WebElement,
        element_index: ty.Optional[int],
        siblings: ty.List[WebElement],
        parent_selector: str,
    ) -> str:
        element_tag = element.tag_name
        # Fetch ID and class attributes
        element_id_attr = element.get_attribute("id")
        class_attr = (
            element.get_attribute("class").replace(" ", ".")
            if element.get_attribute("class")
            else ""
        )

        # Building the selector with ID and class attributes
        id_selector = f"#{element_id_attr}" if element_id_attr else ""
        class_selector = f".{class_attr}" if class_attr else ""
        combined_selector = f"{element_tag}{id_selector}{class_selector}"

        # Calculate current selector with nth-of-type if necessary
        if element_index is None:
            # This occurs only for the root element
            current_selector = combined_selector
        else:
            # Determine if nth-of-type is needed
            same_tag_count = sum(
                1 for sib in siblings[:element_index] if sib.tag_name == element_tag
            )
            if same_tag_count > 1:
                nth_type_index = (
                    sum(
                        1
                        for sib in siblings[:element_index]
                        if sib.tag_name == element_tag
                    )
                    + 1
                )
                current_selector = f"{parent_selector} {combined_selector}:nth-of-type({nth_type_index})"
            else:
                current_selector = f"{parent_selector} {combined_selector}"

        return current_selector.strip()


def draw_elements_on_image(
    image_path: str, element_data: ty.List[ElementItem], output_path: str
) -> None:
    image = cv2.imread(image_path)

    green = (0, 255, 0)
    blue = (255, 0, 0)
    red = (0, 0, 255)
    magenta = (255, 0, 255)
    cyan = (0, 255, 255)

    for element in element_data:
        x1, y1, x2, y2 = element.bbox
        if element.position == "fixed":
            color = magenta
        elif element.tag_name == "text_box":
            color = red
        elif element.tag_name == "img":
            color = blue
        elif element.tag_name == "div":
            color = green
        else:
            color = cyan

        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        cv2.putText(
            image,
            element.label,
            (x1, y1 - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            color,
            2,
        )

    cv2.imwrite(output_path, image)


def draw_elements_from_file(
    image_path: str, elements_path: str, output_path: str
) -> None:
    with open(elements_path) as fd:
        element_data_raw = json.load(fd)

    element_data = [ElementItem(**it) for it in element_data_raw]

    draw_elements_on_image(
        image_path=image_path, element_data=element_data, output_path=output_path
    )


if __name__ == "__main__":  # pragma: no cover
    import fire

    fire.Fire(draw_elements_from_file)
