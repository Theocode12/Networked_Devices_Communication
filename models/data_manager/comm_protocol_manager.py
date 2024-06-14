from config import SAVE_KEYS, DUPLICATE_KEYS
from datetime import datetime
from models import ModelLogger
from models.data_manager import BaseManager
from models.data_manager.storage_manager import StorageManager
from typing import List, Dict, Union, Optional, Tuple
from os import getenv
from util import fetch_url, get_urls_from_ips
import asyncio
import paho.mqtt.client as mqtt


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


class mqttManager(BaseManager):
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


class HTTPCommunicationManager(BaseManager):
    def __init__(self, lock: Optional[asyncio.Lock] = None, **kwargs) -> None:
        """
        Initializes the HTTPCommunicationManager.

        Args:
            lock: used to lock shared resources like network connections
            kwargs: additional keyword arguments like hour, minute, second to specify interval to collect metrics.
        """
        self.ips: List[str] = getenv("DEVICE_IPS", "").split(",")
        self.kwargs: Dict = kwargs
        self.running: bool = True
        self.prev_time: Optional[datetime] = None
        self.lock = lock if lock is not None else asyncio.Lock()
        self.logger = ModelLogger("http-manager").customiseLogger()

        if getenv("MODE") == "dev":
            self.mode: str = "dev"
            self.ips: List[str] = ["localhost"]
        elif getenv("MODE") == "inter-dev":
            self.mode: str = "inter-dev"
        else:
            self.mode: str = "prod"

    def create_db_path(self, stg_obj: StorageManager) -> str:
        """
        Creates a database path based on environment.

        Args:
            stg_obj (Any): Storage object.

        Returns:
            str: Database path.
        """
        if self.mode == "dev" or self.mode == "inter-dev":
            path = stg_obj.create_db_path_from_topic("dev/all")
        else:
            path = stg_obj.create_db_path_from_topic(getenv("HTTP_TOPIC"))
        return path

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
                self.logger.error(
                    f"Error while fetching result {i} with ip {self.ips[i]}"
                )

    def get_date(self) -> str:
        """
        Gets the current date.

        Returns:
            str: Current date.
        """
        return datetime.now().date().strftime("%d/%m/%Y")

    def get_time(self) -> str:
        """
        Gets the current time.

        Returns:
            str: Current time.
        """
        return datetime.now().time().strftime("%H:%M:%S")

    def get_date_time(self) -> Dict[str, str]:
        """
        Gets the current date and time.

        Returns:
            Dict[str, str]: Dictionary containing date and time.
        """
        return {"date": self.get_date(), "time": self.get_time()}

    def get_urls(self) -> List[str]:
        """
        Generates URLs based on environment.

        Returns:
            List[str]: List of URLs.
        """
        if self.mode == "dev":
            urls = [url + ":8080/status" for url in get_urls_from_ips(self.ips)]
        else:
            urls = [url + ":/status" for url in get_urls_from_ips(self.ips)]
        return urls

    def is_save_time(
        self, hour: int = None, minute: int = None, second: int = None, now=None
    ) -> bool:
        """
        Returns True if the current time matches the given interval of hours, minutes, or seconds.

        Parameters:
        - hour (int, optional): Interval for hours.
        - minute (int, optional): Interval for minutes.
        - second (int, optional): Interval for seconds.

        Returns:
        - bool: True if the current time matches the given interval, False otherwise.
        """
        hour = hour if hour is not None else self.kwargs.get("hour")
        minute = minute if minute is not None else self.kwargs.get("minute")
        second = second if second is not None else self.kwargs.get("second")

        now = now or datetime.now()

        if self.prev_time is not None:
            if (
                hour is not None
                and now.hour % hour == 0
                and self.prev_time.hour != now.hour
            ):
                self.prev_time = now
                return True
            if (
                minute is not None
                and now.minute % minute == 0
                and self.prev_time.minute != now.minute
            ):
                self.prev_time = now
                return True
            if (
                second is not None
                and now.second % second == 0
                and self.prev_time.second != now.second
            ):
                self.prev_time = now
                return True
        else:
            if (
                (hour is not None and hour != 0 and now.hour % hour == 0)
                or (minute is not None and minute != 0 and now.minute % minute == 0)
                or (second is not None and second !=0 and now.second % second == 0)
            ):
                self.prev_time = now
                return True

        return False

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

    async def start(self) -> None:
        """
        Asynchronous task for HTTP communication.
        """
        self.logger.info("HTTP communication manager started ...")
        stg_obj = StorageManager()
        while self.running:
            if self.is_save_time():
                data = {}
                async with self.lock:
                    results = await asyncio.gather(
                        *(fetch_url(url) for url in self.get_urls()),
                        return_exceptions=True,
                    )
                self.format_data(results, data)
                if len(data) != 0:
                    data.update(self.get_date_time())
                    path = self.create_db_path(stg_obj)
                    self.save_data(stg_obj, path, data)
            await asyncio.sleep(1)

    def stop(self) -> None:
        """
        Stops the HTTP communication manager.
        """
        self.running = False
        self.logger.info("HTTP communication manager stopped")


async def main():
    import dotenv
    import datetime

    dotenv.load_dotenv("./config/.env")
    # now = datetime.time(12,30,10)
    # now = None
    hccm = HTTPCommunicationManager(minute=15)
    await hccm.start()


if __name__ == "__main__":
    asyncio.run(main())
