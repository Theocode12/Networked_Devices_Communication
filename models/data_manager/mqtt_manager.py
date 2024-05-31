from models import ModelLogger
from typing import Tuple
from os import getenv
import paho.mqtt.client as mqtt


class mqttManagerLogger:
    """
    A logger class for SensorManager that customizes the ModelLogger.
    """

    logger = ModelLogger("sensor-manager").customiseLogger()


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

    def start(self) -> None:
        """
        Starts the MQTT client's network loop.
        """
        self.client.loop_start()

    def stop(self) -> None:
        """
        Stops the MQTT client's network loop.
        """
        self.client.loop_stop()

    def disconnect(self) -> None:
        """
        Disconnects from the MQTT broker.
        """
        self.client.disconnect()
