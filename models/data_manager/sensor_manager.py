from typing import Optional, List
from models.data_manager.storage_manager import StorageManager
from models import ModelLogger
import asyncio


class SensorManagerlogger:
    """
    A logger class for SensorManager that customizes the ModelLogger.
    """

    logger = ModelLogger("sensor-manager").customiseLogger()


class SensorDataManager:
    """
    Manages sensor data collection and temporary storage.

    Attributes:
    - COLLECTION_INTERVAL (Optional[int]): The interval for data collection in seconds.
    - data (dict): A dictionary to store sensor data.
    - tmp_db (TempDB): An instance of TempDB for temporary data storage.
    - sensors (list): A list of sensor instances.
    """

    COLLECTION_INTERVAL: Optional[int] = 10

    def __init__(self):
        """
        Initializes the SensorDataManager with sensor instances and an empty data dictionary.
        """
        pass


    def manage_data(self, mqtt_msg):
        # algo that does some work


        self.save_data(mqtt_msg.topic, mqtt_msg.payload.decode())

    def save_data(self, topic, data):
        stg = StorageManager()
        path = stg.get_db_path_from_topic(topic)
        stg.save(path, data)
