from typing import Optional, List
from models.data_manager.storage_manager import StorageManager
from models import ModelLogger
import asyncio
import json


class SensorManagerlogger:
    """
    A logger class for SensorManager that customizes the ModelLogger.
    """

    logger = ModelLogger("sensor-manager").customiseLogger()


class SensorDataManager:
    """
    Manages sensor data collection.

    Attributes:
    - data (dict): A dictionary to store sensor data.

    """

    def __init__(self):
        """
        Initializes the SensorDataManager with sensor instances and an empty data dictionary.
        """
        pass


    def manage_data(self, mqtt_msg):
        # algo that does some work
        payload = mqtt_msg.payload.decode()
        payload = json.loads(payload)

        self.save_data(mqtt_msg.topic, payload)

    def save_data(self, topic, data):
        stg = StorageManager()
        path = stg.create_db_path_from_topic(topic)
        stg.save(path, data)


class MqttMessage:
    def __init__(self, topic=None, payload=None):
        self.topic = '/dev/test1'
        self.payload = json.dumps({'dc-voltage': 240}).encode()

if __name__ == '__main__':
    manager = SensorDataManager()
    manager.manage_data(MqttMessage())
