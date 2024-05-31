from models.data_manager.mqtt_manager import mqttManager
from models  import ModelLogger
from dotenv import load_dotenv
import signal
import sys


class APPlogger:
    """
    A logger class for SensorManager that customizes the ModelLogger.
    """

    logger = ModelLogger("app").customiseLogger()

def signal_handler(sig, frame):
    """
    Handle termination signals to gracefully shut down the application.
    """
    mqtt_manager.disconnect()
    mqtt_manager.stop()
    APPlogger.logger.info('Application terminated gracefully')
    sys.exit(0)


if __name__ == '__main__':
    load_dotenv('./config/.env')
    mqtt_manager = mqttManager()
    mqtt_manager.use_default_user_passwd_credentials()
    mqtt_manager.connect()
    mqtt_manager.start()

    # Register signal handlers for graceful termination
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    APPlogger.logger.info('Application started')

    # Keep the application running
    signal.pause()
