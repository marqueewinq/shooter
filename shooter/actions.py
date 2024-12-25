import typing as ty

from pydantic import Field, model_validator

from shooter.base import BaseModel

AvailableActionsUnion = ty.NewType(
    "AvailableActionsUnion",
    ty.Union[
        "ScrollDownAction",
        "ScrollUpAction",
        "ScrollToTopAction",
        "ClickAtAction",
        "ClickElementAction",
    ],
)


class BaseAction(BaseModel):
    @classmethod
    def from_dict(cls, data: dict) -> AvailableActionsUnion:
        kind = data.get("kind")
        if kind == "scroll_down":
            return ScrollDownAction(**data)
        elif kind == "scroll_up":
            return ScrollUpAction(**data)
        elif kind == "scroll_to_top":
            return ScrollToTopAction(**data)
        elif kind == "click_at":
            return ClickAtAction(**data)
        elif kind == "click_element":
            return ClickElementAction(**data)
        else:
            raise ValueError(f"Unsupported action kind: {kind}")

    def to_javascript(self) -> str:
        raise NotImplementedError()


class ScrollDownAction(BaseAction):
    """Scroll down the specified amount of pixels."""

    kind: ty.Literal["scroll_down"] = "scroll_down"

    how_much: int = Field(description="How much to scroll, in pixels.")
    element_query_selector: ty.Optional[str] = Field(
        default=None, description="Which element to scroll, default: None for `window`"
    )

    def to_javascript(self) -> str:
        if self.element_query_selector is None:
            return f"window.scrollBy(0, {self.how_much});"
        return f'document.querySelector("{self.element_query_selector}").scrollBy(0, {self.how_much});'


class ScrollUpAction(BaseAction):
    """Scroll up the specified amount of pixels."""

    kind: ty.Literal["scroll_up"] = "scroll_up"

    how_much: int = Field(description="How much to scroll, in pixels.")
    element_query_selector: ty.Optional[str] = Field(
        default=None, description="Which element to scroll, default: None for `window`"
    )

    def to_javascript(self) -> str:
        if self.element_query_selector is None:
            return f"window.scrollBy(0, -{self.how_much});"
        return f'document.querySelector("{self.element_query_selector}").scrollBy(0, -{self.how_much});'


class ScrollToTopAction(BaseAction):
    kind: ty.Literal["scroll_to_top"] = "scroll_to_top"

    def to_javascript(self) -> str:
        return "window.scrollTo(0, 0);"


class ClickAtAction(BaseAction):
    """Click on the specified absolute position on the page."""

    kind: ty.Literal["click_at"] = "click_at"

    click_x: int = Field(description="Absolute x-coordinate to click on the page.")
    click_y: int = Field(description="Absolute y-coordinate to click on the page.")

    def to_javascript(self) -> str:
        return f"document.elementFromPoint({self.click_x}, {self.click_y}).click();"


class ClickElementAction(BaseAction):
    """
    Click on the specified element on the page.

    Order of precedence:

     - element_id
     - element_class
     - element_query_selector

    If more preferred argument is specified, the rest are ignored. If element is not
     found, the actions does nothing.
    """

    kind: ty.Literal["click_element"] = "click_element"

    element_id: ty.Optional[str] = Field(
        default=None, description="ID of the element to click."
    )
    element_class: ty.Optional[str] = Field(
        default=None,
        description=(
            "Class of the element to click; in case of duplicates,"
            " the first one will be clicked."
        ),
    )
    element_query_selector: ty.Optional[str] = Field(
        default=None,
        description=(
            "Query selector of the element to click; in case of duplicates,"
            " the first on will be clicked."
        ),
    )

    @model_validator(mode="after")
    def validate_at_least_one_attribute_is_not_null(self) -> "ClickElementAction":
        if (
            self.element_id is None
            and self.element_class is None
            and self.element_query_selector is None
        ):
            raise ValueError("ClickElementAction must define at least one predicate")
        return self

    def to_javascript(self) -> str:
        if self.element_id:
            return f'document.getElementById("{self.element_id}").click();'
        if self.element_class:
            return (
                f'document.getElementsByClassName("{self.element_class}")[0].click();'
            )
        return f'document.querySelector("{self.element_query_selector}").click();'
