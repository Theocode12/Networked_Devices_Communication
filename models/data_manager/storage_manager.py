from models.db_engine.db import FileDB
from models import ModelLogger
from typing import Dict, Iterator
from util import get_base_path
import datetime
import os


class SMlogger:
    """
    Class for logging database activities.
    """

    logger = ModelLogger("storage-manager").customiseLogger(
        filepath=os.path.join("{}".format(get_base_path()), "logs", "storage.log")
    )


class StorageManager:
    """
    Manages data collection from specified data models and stores it in a file-based database.

    Attributes:
    - db (FileDB): Instance of FileDB for database operations.

    Methods:
    - __init__(self, *args, **kwargs): Initialize the StorageManager instance with additional parameters.
    - get_db_path_from_topic(self, topic: str) -> str: Generate the file path for the database based on the topic.
    - create_db_path_from_topic(self, topic: str) -> str: Create the file path for the database based on the topic.
    - save(self, path: str, data: Dict) -> None: Save the collected data to the database.
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the StorageManager instance.

        Parameters:
        - kwargs: Additional parameters (locks, queues, or managers).
        """
        self.db = FileDB()

    def get_db_path_from_topic(self, topic):
        """
        Generate the file path for the database based on the topic.

        Parameters:
        - topic (str): The MQTT topic to generate the path for.

        Returns:
        - str: The generated file path.
        """
        dir = self.db.get_db_filedir(create=False)
        return os.path.join(dir, topic.lstrip("/"))

    @staticmethod
    def get_unuploaded_files(last_upload_filepath: str, db_path: str) -> Iterator[str]:
        """
        Get a list of unuploaded files based on the last upload file date.

        Parameters:
        - last_upload_file_date (List[str]): The date components of the last upload file.
        - db_path (str): The path to the database.

        Returns:
        - List[str]: A list of unuploaded files.
        """
        from os import getenv

        mode = getenv("MODE")

        if mode == "dev" or mode == "inter-dev":
            last_upload_date = datetime.datetime.strptime(
                last_upload_filepath, os.path.join(db_path, "%Y/%m/%d/dev/all")
            )
        else:
            last_upload_date = datetime.datetime.strptime(
                last_upload_filepath, os.path.join(db_path, "%Y/%m/%d/inverter/all")
            )
        current_date = datetime.datetime.now()
        date_range = (current_date - last_upload_date).days

        for i in range(0, date_range + 1):
            date = last_upload_date + datetime.timedelta(days=i)
            if mode == "dev" or mode == "inter-dev":
                dir_path = os.path.join(
                    db_path, date.strftime("%Y/%m/%d"), "dev", "all"
                )
            else:
                dir_path = os.path.join(
                    db_path, date.strftime("%Y/%m/%d"), "inverter", "all"
                )
            if os.path.exists(dir_path):
                yield dir_path

    def create_db_path_from_topic(self, topic: str):
        """
        Create the file path for the database based on the topic.

        Parameters:
        - topic (str): The MQTT topic to create the path for.

        Returns:
        - str: The created file path.
        """
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
    for file in stg.get_unuploaded_files(
        "/home/valentine/Solar_Station_Communication/data/2024/06/09/dev/all",
        "/home/valentine/Solar_Station_Communication/data/",
    ):
        print(file)
