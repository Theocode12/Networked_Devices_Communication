from models import ModelLogger
from os import getenv
import paho.mqtt.client as mqtt

class mqttManagerLogger:
    """
    A logger class for SensorManager that customizes the ModelLogger.
    """

    logger = ModelLogger("sensor-manager").customiseLogger()

def on_connect(client, userdata, flags, rc, properties):
    mqttManagerLogger.logger.info(f"Connected with result code {rc}")
    mqtt_topics = getenv('MQTT_TOPICS')
    for topic in mqtt_topics.split(','):
        client.subscribe(topic)

def on_message(client, userdata, msg):
    from models.data_manager.sensor_manager import SensorDataManager

    mqttManagerLogger.logger.info(f"Data is received from {msg.topic}")
    manager = SensorDataManager()
    manager.manage_data(msg)

def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
    mqttManagerLogger.logger(f'client disconnected with {reason_code}')

class mqttManager:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = on_connect
        self.client.on_message = on_message
        # self.client.on_disconnect = on_disconnect
        self.client.enable_logger(mqttManagerLogger.logger)

    def set_user_passwd_credentials(self, username, passwd):
        self.client.username_pw_set(username, passwd)

    def get_user_passwd_credentials(self, *args, **kwargs):
        username = getenv('MQTT_USERNAME')
        passwd = getenv('MQTT_PASSWORD')
        return (username, passwd)
    
    def use_default_user_passwd_credentials(self):
        user_passwd = self.get_user_passwd_credentials()
        self.set_user_passwd_credentials(*user_passwd)
        mqttManagerLogger.logger.info(f"default username and password authentication used")
    
    def connect(self, host='localhost', port=1883):
        self.client.connect_async(host, port)
        mqttManagerLogger.logger.info(f"connecting to {host} on port {port} ...")

    def publish(self, topic, payload):
        self.client.publish(topic, payload)

    def start(self):
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()

    def disconnect(self):
        self.client.disconnect()