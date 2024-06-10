from models import ModelLogger
from models.data_manager.comm_protocol_manager import mqttManager, HTTPCommunicationManager
from models.data_manager.cloud_transfer import CloudTransferManager
from models.data_manager import BaseManager
from dotenv import load_dotenv
from typing import List
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
    http_manager.stop()
    cloud_manager.stop()
    APPlogger.logger.info("Application terminated gracefully")
    sys.exit(0)


async def main(*args: BaseManager):
    # Run all managers concurrently
    tasks = []
    for manager in args:
        tasks.append(asyncio.create_task(manager.start()))
    await asyncio.gather(*tasks)


def get_enabled_managers() -> List:
    managers = []
    if os.getenv("MQTT_ENABLED") == "true":
        mqtt_manager.use_default_user_passwd_credentials()
        mqtt_manager.connect()
        managers.append(mqtt_manager)
    else:
        APPlogger.logger.info("MQTT Manager not enabled")
    if os.getenv("HTTP_ENABLED") == "true":
        managers.append(http_manager)
    else:
        APPlogger.logger.info("HTTP Manager not enabled")
    if os.getenv("CLOUD_ENABLED") == "true":
        managers.append(cloud_manager)
    else:
        APPlogger.logger.info("Cloud Manager not enabled")
    return managers


if __name__ == "__main__":
    load_dotenv("./config/.env")
    APPlogger.logger.info("Application started")

    lock = asyncio.Lock()

    # Initialize managers
    mqtt_manager = mqttManager()
    http_manager = HTTPCommunicationManager(
        lock=lock, minute=int(os.getenv("DATA_TRANSFER_INTERVAL"))
    )  # 15 minutes interval default
    cloud_manager = CloudTransferManager(
        lock=lock, minute=int(os.getenv("DATA_TRANSFER_INTERVAL"))
    )  # minutes interval
    # Register signal handlers for graceful termination
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    asyncio.run(main(*get_enabled_managers()))

    # Keep the application running
    signal.pause()
