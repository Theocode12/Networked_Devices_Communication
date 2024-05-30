from models.db_engine.db import FileDB
from models import ModelLogger
from typing import Sequence, Dict
from util import get_base_path
import os


class SMlogger:
    """
    Class for logging database activities.
    """

    logger = ModelLogger("data-saving").customiseLogger(
        filepath=os.path.join("{}".format(get_base_path()), "logs", "storage.log")
    )


class StorageManager:
    """
    Manages data collection from specified data models and stores it in a file-based database.

    Attributes:
    - db_path (str): Path to the file-based database.

    Methods:
    - __init__(self, sensor_names: Sequence[str] = [], **kwargs): Initialize the StorageManager instance with specified sensors and additional parameters.
    - save_collected_data(self, data: Dict) -> None: Save the collected data to the database.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the StorageManager instance.

        Parameters:
        - kwargs: Additional parameters (locks, queues, or managers).
        """
        self.db = FileDB()

    def get_db_path_from_topic(self,topic):
        dir = self.db.get_db_filedir(create=False)
        return os.path.join(dir, topic.lstrip("/"))

    def create_db_path_from_topic(self, topic: str):
        path = self.get_db_path_from_topic(topic)
        self.db.create_file(path)
        return path

    def save(self, path: str, data: Dict) -> None:
        """
        Save the collected data to the database.

        Parameters:
        - data (Dict): Data to be saved.
        """
        with FileDB(path, "a") as db:
            db.write_data_line(data)


if __name__ == "__main__":
    stg = StorageManager()
    path = stg.create_db_path_from_topic('/dev/test')
    stg.save(path, {'topic':'/dev/test'})

