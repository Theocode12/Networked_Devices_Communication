from config import SAVE_KEYS, DUPLICATE_KEYS
from datetime import datetime
from models import ModelLogger
from models.data_manager.storage_manager import StorageManager
from typing import List, Dict, Union
from typing import Tuple
from os import getenv
from util import fetch_url, get_urls_from_ips
import asyncio
import paho.mqtt.client as mqtt
import time


class mqttManagerLogger:
    """
    A logger class for SensorManager that customizes the ModelLogger.
    """

    logger = ModelLogger("mqtt-manager").customiseLogger()


def on_connect(client, userdata, flags, rc, properties):
    """
    Callback function for when the client receives a CONNACK response from the server.

    Args:
        client (mqtt.Client): The MQTT client instance.
        userdata (dict): The private user data as set in Client() or userdata_set().
        flags (dict): Response flags sent by the broker.
        rc (int): The connection result.
        properties (dict): Properties of the MQTT message (MQTT 5.0 only).
    """

    mqttManagerLogger.logger.info(f"Connected with result code {rc}")
    mqtt_topics = getenv("MQTT_TOPICS")
    if mqtt_topics:
        for topic in mqtt_topics.split(","):
            client.subscribe(topic)
            mqttManagerLogger.logger.info(f"Subscribed to topic: {topic}")
    else:
        mqttManagerLogger.logger.warning(
            "No MQTT topics found in environment variables."
        )


def on_message(client, userdata, msg):
    """
    Callback function for when a PUBLISH message is received from the server.

    Args:
        client (mqtt.Client): The MQTT client instance.
        userdata (dict): The private user data as set in Client() or userdata_set().
        msg (mqtt.MQTTMessage): An instance of MQTTMessage, which contains the topic and payload.
    """
    from models.data_manager.sensor_manager import SensorDataManager

    mqttManagerLogger.logger.info(f"Data is received from {msg.topic}")
    manager = SensorDataManager()
    manager.manage_data(msg)


class mqttManager:
    """
    A manager class for handling MQTT connections and messaging.
    """

    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = on_connect
        self.client.on_message = on_message
        self.client.enable_logger(mqttManagerLogger.logger)

    def set_user_passwd_credentials(self, username: str, passwd: str):
        """
        Sets the username and password for MQTT authentication.

        Args:
            username (str): The username for MQTT authentication.
            passwd (str): The password for MQTT authentication.
        """
        self.client.username_pw_set(username, passwd)

    def get_user_passwd_credentials(self, *args, **kwargs) -> Tuple[str, str]:
        """
        Retrieves the MQTT username and password from environment variables.

        Returns:
            Tuple[str, str]: A tuple containing the username and password.
        """
        username = getenv("MQTT_USERNAME")
        passwd = getenv("MQTT_PASSWORD")
        return (username, passwd)

    def use_default_user_passwd_credentials(self) -> None:
        """
        Uses the default MQTT username and password for authentication.
        """
        user_passwd = self.get_user_passwd_credentials()
        if user_passwd[0] and user_passwd[1]:
            self.set_user_passwd_credentials(*user_passwd)
            mqttManagerLogger.logger.info(
                "Default username and password authentication used"
            )
        else:
            mqttManagerLogger.logger.error(
                "MQTT username or password not found in environment variables"
            )

    def connect(self, host: str = "localhost", port: int = 1883) -> None:
        """
        Connects to the MQTT broker asynchronously.

        Args:
            host (str, optional): The hostname of the MQTT broker. Defaults to 'localhost'.
            port (int, optional): The port number of the MQTT broker. Defaults to 1883.
        """
        self.client.connect_async(host, port)
        mqttManagerLogger.logger.info(f"connecting to {host} on port {port} ...")

    def publish(self, topic: str, payload: str) -> None:
        """
        Publishes a message to a specified topic.

        Args:
            topic (str): The topic to publish the message to.
            payload (str): The message payload.
        """
        self.client.publish(topic, payload)

    async def start(self) -> None:
        """
        Starts the MQTT client's network loop.
        """
        self.client.loop_start()

    def stop(self) -> None:
        """
        Stops the MQTT client's network loop.
        """
        self.client.loop_stop()
        self.client.disconnect()

    def disconnect(self) -> None:
        """
        Disconnects from the MQTT broker.
        """
        self.client.disconnect()


class HTTPCommunicationManager:
    def __init__(self, interval: int = 15) -> None:
        """
        Initializes the HTTPCommunicationManager.

        Args:
            interval (int, optional): Time interval in seconds between HTTP requests. Defaults to 900.
        """
        self.ips: List[str] = getenv("DEVICE_IPS").split(",")
        if getenv("ENV") == "development":
            self.env: str = "dev"
            self.ips: List[str] = ["localhost"]
        elif getenv("ENV") == "inter-development":
            self.env: str = "inter-dev"
        else:
            self.env: str = "prod"
        print(self.env)
        self.minute_interval: int = interval
        self.running: bool = True
        self.prev_min: Union[int, None] = None
        self.logger = ModelLogger("http-manager").customiseLogger()

    def get_urls(self) -> List[str]:
        """
        Generates URLs based on environment.

        Returns:
            List[str]: List of URLs.
        """
        if self.env == "dev":
            urls = [url + ":8080/status" for url in get_urls_from_ips(self.ips)]
        else:
            urls = [url + ":/status" for url in get_urls_from_ips(self.ips)]
        return urls

    async def start(self) -> None:
        """
        Asynchronous task for HTTP communication.
        """
        self.logger.info("HTTP communication manager started ...")
        stg_obj = StorageManager()
        while self.running:
            if self.is_save_time(minute_interval=self.minute_interval):
                data = {}
                data.update(self.get_date_time())
                results = await asyncio.gather(
                    *(fetch_url(url) for url in self.get_urls()), return_exceptions=True
                )
                self.format_data(results, data)
                path = self.create_db_path(stg_obj)
                self.save_data(stg_obj, path, data)

    def save_data(
        self, stg_obj: StorageManager, path: str, data: Dict[str, Union[str, int]]
    ) -> None:
        """
        Saves data to storage.

        Args:
            stg_obj (Any): Storage object.
            path (str): Path to save data.
            data (Dict[str, Union[str, int]]): Data to save.
        """
        stg_obj.save(path, data)
        self.logger.info("Data from atleast one inverter is  data stored")

    def format_data(
        self,
        results: List[Union[Dict[str, Union[str, int]], Exception]],
        data_obj: Dict[str, Union[str, int]],
    ) -> None:
        """
        Formats the fetched data.

        Args:
            results (List[Union[Dict[str, Union[str, int]], Exception]]): Fetched results.
            data_obj (Dict[str, Union[str, int]]): Data object to format.
        """
        duplicate = []
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                for key, value in result.items():
                    if (key in SAVE_KEYS) and (key not in duplicate):
                        if key.endswith(")"):
                            key = key.split("(")[0]
                        if key in DUPLICATE_KEYS:
                            duplicate.append(key)
                            data_obj[key] = value
                        else:
                            data_obj[key + "_" + str(i)] = value
            else:
                self.logger.error(f"Error while fetching result {i} with ip {self.ips[i]}")

    def create_db_path(self, stg_obj: StorageManager) -> str:
        """
        Creates a database path based on environment.

        Args:
            stg_obj (Any): Storage object.

        Returns:
            str: Database path.
        """
        if self.env == "dev" or self.env == "inter-dev":
            path = stg_obj.create_db_path_from_topic("dev/all")
        else:
            path = stg_obj.create_db_path_from_topic(getenv("HTTP_TOPIC"))
        return path

    def is_save_time(self, curr_time: str = None, minute_interval: int = 15) -> bool:
        """
        Checks if it's time to save data.

        Args:
            curr_time (str, optional): Current time string. Defaults to None.
            minute_interval (int, optional): Interval in minutes. Defaults to 15.

        Returns:
            bool: True if it's time to save data, False otherwise.
        """
        if not curr_time:
            curr_time = self.get_time()
        curr_min = int(curr_time.split(":")[1])
        if (not (curr_min % minute_interval)) and (
            (self.prev_min != curr_min) or (self.prev_min is None)
        ):
            self.prev_min = curr_min
            return True
        return False

    def get_date_time(self) -> Dict[str, str]:
        """
        Gets the current date and time.

        Returns:
            Dict[str, str]: Dictionary containing date and time.
        """
        return {"date": self.get_date(), "time": self.get_time()}

    def get_date(self) -> str:
        """
        Gets the current date.

        Returns:
            str: Current date.
        """
        return datetime.now().date().strftime('%d/%m/%Y')

    def get_time(self) -> str:
        """
        Gets the current time.

        Returns:
            str: Current time.
        """
        return datetime.now().time().strftime("%H:%M:%S")

    def stop(self) -> None:
        """
        Stops the HTTP communication manager.
        """
        self.running = False
        self.logger.info("HTTP communication manager stopped")


async def main():
    import dotenv

    dotenv.load_dotenv("./config/.env")
    hccm = HTTPCommunicationManager(1)
    task = asyncio.create_task(hccm.start())
    await task
    task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
