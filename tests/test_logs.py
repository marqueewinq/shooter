import logging
from unittest import mock

import pytest

from shooter.logs import setup_task_logger


@pytest.fixture
def mock_logging_handlers():
    with mock.patch("logging.FileHandler") as mock_file_handler, mock.patch(
        "logging.StreamHandler"
    ) as mock_stream_handler:
        yield mock_file_handler, mock_stream_handler


@pytest.fixture
def mock_os_path_join():
    with mock.patch("os.path.join", return_value="mocked_path/log.txt") as mock_join:
        yield mock_join


def test_setup_task_logger(mock_logging_handlers, mock_os_path_join):
    mock_file_handler, mock_stream_handler = mock_logging_handlers
    mock_file_handler.return_value.level = logging.INFO
    mock_stream_handler.return_value.level = logging.INFO

    logger_name = "test_logger"
    output_path = "/mocked_path"

    # Call the function
    logger = setup_task_logger(logger_name, output_path)

    # Assert the logger is created correctly
    assert logger.name == logger_name
    assert logger.level == logging.DEBUG

    # Assert handlers are set correctly
    assert len(logger.handlers) == 2
    assert isinstance(logger.handlers[0], mock.MagicMock)
    assert isinstance(logger.handlers[1], mock.MagicMock)

    # Assert file handler is set with correct log path
    mock_os_path_join.assert_called_once_with(output_path, "log.txt")
    mock_file_handler.assert_called_once_with("mocked_path/log.txt")
    assert logger.handlers[0].level == logging.INFO

    # Assert stream handler is set correctly
    assert logger.handlers[1].level == logging.INFO
