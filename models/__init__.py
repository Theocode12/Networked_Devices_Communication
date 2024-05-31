from util.logger import BaseLogger
from util import get_base_path
import logging
import os


class ModelLogger(BaseLogger):
    def __init__(self, name=None):
        super().__init__(name)

    def customiseLogger(
        self,
        level=logging.DEBUG,
        filepath=os.path.join("{}".format(get_base_path()), "logs", "models.log"),
        format=None,
    ):
        self.setLevel(level)

        if not os.path.exists(filepath):
            os.makedirs("/".join(filepath.split("/")[:-1]), exist_ok=True)
            with open(filepath, "w") as fd:
                fd.write("")

        self.setFileHandler(filepath)
        # self.setStreamHandler()

        if format:
            self.setFormatter(format)

        return self
