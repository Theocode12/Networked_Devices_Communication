from models.db_engine.db import FileDB
from models import ModelLogger
from typing import Sequence, Dict
from util import get_base_path
import os


class DSlogger:
    """
    Class for logging database activities.
    """

    logger = ModelLogger("data-saving").customiseLogger(
        filename=os.path.join("{}".format(get_base_path()), "logs", "storage.log")
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
        pass

    def get_db_path_from_topic(self,topic):
        pass


    def save(self, path, data: Dict) -> None:
        """
        Save the collected data to the database.

        Parameters:
        - data (Dict): Data to be saved.
        """
        with FileDB(path, "a") as db:
            db.write_data_line(data)

    
