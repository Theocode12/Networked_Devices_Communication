from models import ModelLogger
from models.data_manager.comm_protocol_manager import mqttManager
from models.data_manager.comm_protocol_manager import HTTPCommunicationManager
from models.data_manager.cloud_transfer import CloudTransferManager
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
    # mqtt_manager.stop()
    http_com_manager.stop()
    cloud_transfer_manager.stop()
    APPlogger.logger.info("Application terminated gracefully")
    sys.exit(0)


async def main(mqtt_manager, http_com_manager, cloud_transfer_manager):
    # Run all managers concurrently
    # task_1 = asyncio.create_task(mqtt_manager.start())
    task_2 = asyncio.create_task(http_com_manager.start())
    task_3 = asyncio.create_task(cloud_transfer_manager.start())
    await asyncio.gather(task_2, task_3)


if __name__ == "__main__":
    load_dotenv("./config/.env")
    APPlogger.logger.info("Application started")

    # Initialize managers
    mqtt_manager = mqttManager()
    # mqtt_manager.use_default_user_passwd_credentials()
    # mqtt_manager.connect()
    http_com_manager = HTTPCommunicationManager(interval=1)  # 15 minutes interval
    cloud_transfer_manager = CloudTransferManager()

    # Register signal handlers for graceful termination
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    asyncio.run(main(mqtt_manager, http_com_manager, cloud_transfer_manager))

    # Keep the application running
    signal.pause()
