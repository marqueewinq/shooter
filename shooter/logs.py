import logging
import os


def setup_task_logger(logger_name: str, output_path: str):
    """Create a logger for each screenshot task with a unique log file."""
    # Hash the URL to create a unique log filename
    log_file_path = os.path.join(output_path, "log.txt")

    # Create a logger
    task_logger = logging.getLogger(logger_name)
    task_logger.setLevel(logging.DEBUG)

    # Clear the default handlers
    task_logger.handlers.clear()

    # Create the common formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create a file handler for this specific task
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # Create a stream handler for stdout
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)

    # Add handlers to the logger
    task_logger.addHandler(file_handler)
    task_logger.addHandler(stream_handler)

    return task_logger


def setup_app_logger(logger_name: str, level: int = logging.INFO):
    # Create a logger
    app_logger = logging.getLogger(logger_name)
    app_logger.setLevel(logging.DEBUG)

    # Clear the default handlers
    app_logger.handlers.clear()

    # Create the formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Create a stream handler for stdout
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    # Add handlers to the logger
    app_logger.addHandler(stream_handler)

    return app_logger
