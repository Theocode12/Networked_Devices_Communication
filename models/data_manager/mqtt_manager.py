from config import SAVE_KEYS
from datetime import datetime
from models import ModelLogger
from models.data_manager.storage_manager import StorageManager
from typing import Tuple
from os import getenv
from util import fetch_url, get_urls_from_ips
import asyncio
import aiohttp
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
    def __init__(self, interval=900):
        self.ips = getenv("DEVICE_IPS").split(",")
        if getenv("ENV") == "development":
            self.env = "dev"
            self.ips = "localhost"
        elif getenv('ENV') == 'inter-development':
            self.env = 'inter-dev'
        else:
            self.env = "prod"
        self.interval = interval
        self.running = True
        self.logger = ModelLogger("http-manager").customiseLogger()

    def get_urls(self):
        if self.env == "dev":
            urls = [url + ":8080/status" for url in get_urls_from_ips(self.ips)]
        else:
            urls = [url + ":/status" for url in get_urls_from_ips(self.ips)]
        return urls

    async def httpcom_task(self):
        self.logger.info("HTTP communication manager started ...")
        time_now = time.perf_counter()
        while self.running:
            if (time.perf_counter() - time_now) > self.interval:
                time_now = time.perf_counter()
                data = {}
                results = await asyncio.gather(
                    *(fetch_url(url) for url in self.get_urls()), return_exceptions=True
                )
                for i, result in enumerate(results):
                    if not isinstance(result, Exception):
                        for key, value in result.items():
                            if key in SAVE_KEYS:
                                if key.endswith(")"):
                                    key = key.split("(")[0]
                                data[key + "_" + str(i)] = value
                    else:
                        self.logger.error(f"Error while fetching result {i}")
                stg = StorageManager()

                if self.env == "dev" or self.env == 'inter-dev':
                    path = stg.create_db_path_from_topic("dev/all")
                else:
                    path = stg.create_db_path_from_topic(getenv("HTTP_TOPIC"))

                data.update(self.get_date_time())
                stg.save(path, data)
                self.logger.info("HTTP communication data stored")

    def get_date_time(self):
        date = str(datetime.now().date())
        time = str(datetime.now().time()).split('.')[0]

        return {'date': date, 'time': time}

    def stop(self):
        """
        Stops the HTTP communication manager.
        """
        self.running = False
        self.logger.info("HTTP communication manager stopped")


async def main():
    import dotenv

    dotenv.load_dotenv("./config/.env")
    hccm = HTTPCommunicationManager(2)
    task = asyncio.create_task(hccm.httpcom_task())
    await task
    task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
