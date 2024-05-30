import logging
from util import get_base_path
import os


class BaseLogger(logging.Logger):
    def __init__(self, name: str) -> None:
        self.format: logging.Formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        )
        super().__init__(name)

    def setFormatter(self, format: str) -> None:
        self.format = logging.Formatter(format)

    def getFormatter(self) -> logging.Formatter:
        return self.format

    def setFileHandler(self, filename: str) -> None:
        file_handler = logging.FileHandler(filename)
        file_handler.setFormatter(self.getFormatter())
        self.addHandler(file_handler)

    def setStreamHandler(self) -> None:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(self.getFormatter())
        self.addHandler(stream_handler)


class LogDisabledContext:
    def __enter__(self):
        # Save the original log level
        self.original_log_level = logging.root.manager.disable
        # Temporarily disable logging
        logging.disable(logging.CRITICAL)

    def __exit__(self, exc_type, exc_value, traceback):
        # Restore the original log level
        logging.disable(self.original_log_level)


if __name__ == "__main__":
    logger = BaseLogger("test")
    logger.setLevel(logging.DEBUG)
    logger.setFileHandler(
        os.path.join("{}".format(get_base_path()), "logs", "models.log")
    )
    logger.setStreamHandler()

    logger.debug("Starting logging")
