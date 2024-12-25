import enum
import typing as ty
from urllib.parse import ParseResult, quote, urlparse

from celery.result import AsyncResult
from pydantic import Field, field_validator, model_validator

from shooter.actions import ClickAtAction  # noqa: F401
from shooter.actions import ClickElementAction  # noqa: F401
from shooter.actions import ScrollDownAction  # noqa: F401
from shooter.actions import ScrollToTopAction  # noqa: F401
from shooter.actions import ScrollUpAction  # noqa: F401
from shooter.actions import AvailableActionsUnion, BaseAction
from shooter.base import BaseModel
from shooter.drivers.device import Device


def validate_url(url: str, raise_for_error: bool = False) -> ty.Optional[ParseResult]:
    """Validated the URL against stronger set of constraints."""
    # Parse the URL
    parsed = urlparse(url)

    def return_error_message(_parsed: ParseResult) -> str:
        # Check for missing scheme (protocol) or invalid scheme
        if not _parsed.scheme:
            return "Missing URL scheme (protocol)"
        if _parsed.scheme not in {"http", "https"}:
            return "Invalid URL scheme (only 'http' and 'https' are allowed)"

        # Check for invalid port number
        if _parsed.port is not None and (not (1 <= _parsed.port <= 65535)):
            return "Invalid port number"

        # Ensure the netloc (network location) is present
        if not _parsed.netloc:
            return "Missing network location in URL"

        # Check for consecutive dots in the netloc
        if ".." in _parsed.netloc:
            return "URL contains consecutive dots in the netloc"

    error_message = return_error_message(parsed)

    if error_message is None:
        return parsed
    if raise_for_error:
        raise ValueError(error_message)


class ScrollDirection(enum.Enum):
    DOWN = "down"
    UP = "up"


class BrowserChoice(enum.Enum):
    """Enum for browser choices."""

    CHROME = "chrome"
    FIREFOX = "firefox"

    def __str__(self) -> str:
        return self.value


class ProxyConfig(BaseModel):
    host: str
    port: int
    username: str
    password: str
    protocol: str = "https"

    def get_connection_string(self, masked: bool = False):
        safe_username = quote(self.username)
        safe_password = quote(self.password) if not masked else "***"
        return (
            f"{self.protocol}://{safe_username}:{safe_password}@{self.host}:{self.port}"
        )


class TakeScreenshotConfig(BaseModel):
    """Config for individual screenshot task."""

    # fmt: off
    url: ty.Optional[str] = Field(default=None, description="The URL of the page to capture.")
    full_page_screenshot: bool = Field(default=True, description="Capture the full page or just the viewport.")
    browser: BrowserChoice = Field(default=BrowserChoice.CHROME, description="Which browser to capture with")
    capture_visible_elements: bool = Field(default=True, description="Save visible page elements as a JSON file (with visible=True property).")
    capture_invisible_elements: bool = Field(default=False, description="Save invisible page elements as a JSON file (with visible=False property).")
    window_size: ty.Optional[str] = Field(default=None, description="Browser window size in 'widthxheight' format, e.g., '1920x1080'.")
    user_agent: ty.Optional[str] = Field(default=None, description="Custom user agent string.")
    proxy: ty.Optional[ty.Union[ProxyConfig, ty.List[ProxyConfig]]] = Field(default=None, description="Connection details for proxy server. Specify list of different proxy configs to retry them in the given order.")
    wait_after_load: float = Field(default=5, description="Time to wait for page load in seconds.")
    wait_before_load: ty.Optional[float] = Field(default=None, description="Time to wait before loading the page (default: random 0..5 seconds).")
    wait_for_selector: ty.Optional[str] = Field(default=None, description="Wait for the target element to become available")
    wait_for_selector_timeout: float = Field(default=10.0, description="Timeout for `wait_for_selector` in seconds.")
    scroll_pause_time: float = Field(default=0.1, description="Pause time between scrolls in seconds.")
    actions: ty.Optional[ty.List[AvailableActionsUnion]] = Field(default=None, description="List of actions to do before the capture.")
    device: Device = Field(default=Device.DESKTOP, description="Which device to emulate.")
    disable_javascript: bool = Field(default=False, description="Disable javaScript for this page.")
    # fmt: on

    def parsed_url(self) -> ParseResult:
        _parsed_url = validate_url(self.url, raise_for_error=False)
        if _parsed_url is None:
            raise ValueError(
                "Somehow TakeScreenshotConfig was created with incorrect url"
            )
        return _parsed_url

    @field_validator("url")
    @classmethod
    def validate_url(cls, value):
        if value is None:
            return value  # Nothing to validate
        validate_url(value, raise_for_error=True)
        return value

    @field_validator("window_size")
    @classmethod
    def validate_window_size(cls, value):
        """Asserts window_size is in the acceptable format"""
        if value is None:
            return
        parts = value.split("x")
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError(
                "window_size must be in the format 'widthxheight', e.g., '1920x1080'."
            )
        return value

    def dict(self, *args, **kwargs) -> dict:
        """
        Dict representation with the attributes converted into JSON-serializable values.

        Replaces:

         - `browser` and `device` with str(value)
         - `proxy` with masked proxy connection string
        """
        data = super().dict(*args, **kwargs)
        data["browser"] = data["browser"].value
        data["device"] = data["device"].value
        if data["proxy"] is not None:
            if isinstance(data["proxy"], list):
                data["proxy"] = [
                    ProxyConfig(**it).get_connection_string(masked=True)
                    for it in data["proxy"]
                ]
            else:
                data["proxy"] = ProxyConfig(**data["proxy"]).get_connection_string(
                    masked=True
                )
        return data


class TakeScreenshotRequest(BaseModel):
    sites: ty.List[ty.Union[str, TakeScreenshotConfig]] = Field(
        ...,
        example=[
            "https://example.com",
            {
                "url": "https://another-example.com",
                "full_page_screenshot": False,
                "window_size": "1280x720",
            },
        ],
        description="A list of screenshot configurations.",
    )
    default_config: TakeScreenshotConfig = Field(
        default=TakeScreenshotConfig(),
        description="Default configuration applied to all screenshot tasks.",
    )

    @model_validator(mode="before")
    def convert_urls_to_config(cls, values):
        """
        Applies the order of precedence in TakeScreenshotConfig instances.

        Order of precedence of config values:

         1. Individual `TakeScreenshotConfig` objects;
         2. Values in `TakeScreenshotRequest.default_config`;
         3. Default values.

        Converts simple strings in `sites` to TakeScreenshotConfig instances. The
         missing values in that config are taken from `default_config`.

        For the partial TakeScreenshotConfig instances, fills unspecified values with
         the values from `default_config`.
        """
        default_config_dict_without_url = (
            values["default_config"]
            if "default_config" in values
            else TakeScreenshotConfig(url="https://example.com").dict()
        )
        if "url" in default_config_dict_without_url:
            default_config_dict_without_url.pop("url")

        replaced_sites: ty.List[TakeScreenshotConfig] = []
        for index, url_or_config in enumerate(values["sites"]):
            # Create the replacement instance
            replaced_config: TakeScreenshotConfig
            if isinstance(url_or_config, str):
                # Replace url string with the `default_config`
                replaced_config = TakeScreenshotConfig(
                    url=url_or_config, **default_config_dict_without_url
                )
            else:
                # Check that url is provided
                if url_or_config.get("url") is None:
                    raise ValueError(
                        f"Url is required in sites' items, position {index}"
                    )
                # Update provided config with default values from default_config
                new_config = (
                    default_config_dict_without_url.copy()
                )  # Start with the default_config
                new_config.update(url_or_config)  # Apply individual values
                replaced_config = TakeScreenshotConfig(**new_config)

            replaced_sites.append(replaced_config)

        values["sites"] = replaced_sites
        return values

    def set_actions(
        self,
        hostname_to_actions: ty.Dict[str, ty.List[BaseAction]],
        force_override: bool = False,
    ) -> "TakeScreenshotRequest":
        """Replaces actions for the specified configs with the provided values."""
        # Fill out the hostname -> config mapping
        hostnames: ty.List[str] = []
        for config in self.sites:
            hostnames.append(config.parsed_url().hostname)

        # Replace the action config in-place
        for hostname, actions in hostname_to_actions.items():
            index = hostnames.index(hostname)
            if index is None:
                # Hostname is not found, skipping
                continue
            if self.sites[index].action is not None and not force_override:
                # Do not override specified actions if not asked to
                continue
            self.sites[index].actions = actions
        return self


class TakeScreenshotResponse(BaseModel):
    message: str
    group_result_id: str


class TaskProgressResponse(BaseModel):
    completed: int
    failed: int
    total: int
    state: str
    all_successful: bool
    ready: bool

    @classmethod
    def from_async_result_list(
        cls, async_result_list: ty.List[AsyncResult]
    ) -> "TaskProgressResponse":
        completed = 0
        failed = 0
        total = len(async_result_list)
        states = []

        # Collect statistics
        for result in async_result_list:
            if result.ready():
                if result.successful():
                    completed += 1
                    states.append(result.state)
                else:
                    failed += 1
                    states.append(result.state)
            else:
                states.append(result.state)

        # Determine the overall state
        if len(states) > 0 and all(state == "SUCCESS" for state in states):
            state = "SUCCESS"
        elif any(state == "PENDING" for state in states):
            state = "PENDING"
        elif any(state == "FAILURE" for state in states):
            state = "FAILURE"
        else:
            state = "UNKNOWN"

        # Determine if all tasks were successful
        all_successful = completed > 0 and completed == total and failed == 0

        # Determine if all tasks had finished
        ready = completed + failed == total

        return cls(
            completed=completed,
            failed=failed,
            total=total,
            state=state,
            all_successful=all_successful,
            ready=ready,
        )
