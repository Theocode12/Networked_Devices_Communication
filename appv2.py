from models import ModelLogger
from models.data_manager.comm_protocol_manager import mqttManager
from models.data_manager.comm_protocol_manager import HTTPCommunicationManager
from dotenv import load_dotenv
import asyncio
import signal
import sys
import os


class APPlogger:
    """
    A logger class for SensorManager that customizes the ModelLogger.
    """

    logger = ModelLogger("app").customiseLogger()


def signal_handler(sig, frame):
    """
    Handle termination signals to gracefully shut down the application.
    """
    mqtt_manager.stop()
    http_com_manager.stop()
    APPlogger.logger.info("Application terminated gracefully")
    sys.exit(0)


async def main(mqtt_manager, http_com_manager):
    # Run both managers concurrently
    task_1 = asyncio.create_task(mqtt_manager.start())
    task_2 = asyncio.create_task(http_com_manager.httpcom_task())
    await asyncio.gather(task_1, task_2)


if __name__ == "__main__":
    load_dotenv("./config/.env")
    APPlogger.logger.info("Application started")

    # Initialize managers
    mqtt_manager = mqttManager()
    mqtt_manager.use_default_user_passwd_credentials()
    mqtt_manager.connect()
    http_com_manager = HTTPCommunicationManager(interval=1)  # 15 minutes interval

    # Register signal handlers for graceful termination
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    asyncio.run(main(mqtt_manager, http_com_manager))

    # Keep the application running
    signal.pause()
