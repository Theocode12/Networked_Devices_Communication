#!.venv/bin/python
import paho.mqtt.client as mqtt
from os import getenv

# client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
# client.username_pw_set("raspberrypi", "raspberrypi")
# client.connect("localhost", 1883, 60)

# client.publish("test/topic", "Hello from raspberypi")
# client.disconnect()

def on_connect(client, userdata, flags, rc, properties):
    print(f"Connected with result code {rc}")
    mqtt_topics = getenv('MQTT_TOPICS')
    for topic in mqtt_topics:
        client.subscribe(topic)

def on_message(client, userdata, msg):
    print(f"{msg.topic} {msg.payload.decode()}")
    from models.data_manager.sensor_manager import SensorDataManager
    manager = SensorDataManager()
    manager.manage_data(msg)

class mqttManager:
    def __init__(self):
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = on_connect
        self.client.on_message = on_message

    def set_user_passwd_credentials(self, username, passwd):
        self.client.username_pw_set(username, passwd)

    def get_user_passwd_credentials(self, *args, **kwargs):
        username = getenv('MQTT_USERNAME')
        passwd = getenv('MQTT_PASSWORD')
        return (username, passwd)
    
    def use_default_user_passwd_credentials(self):
        user_passwd = self.get_user_passwd_credentials()
        self.set_user_passwd_credentials(*user_passwd)
    
    def connect(self, host, port=1883):
        self.client.connect_async(host, port)

    def publish(self, topic, payload):
        self.client.publish(topic, payload)

    def disconnect(self):
        self.client.disconnect()