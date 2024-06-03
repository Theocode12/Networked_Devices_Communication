import asyncio
import signal
from models.data_manager.mqtt_manager import mqttManager
from models.data_manager.mqtt_manager import HTTPCommunicationManager
from dotenv import load_dotenv

async def main(mqtt_manager, http_com_manager):
    # Run both managers concurrently
    task_1 = asyncio.create_task(mqtt_manager.start())
    task_2 = asyncio.create_task(http_com_manager.httpcom_task())
    await asyncio.gather(task_1, task_2)


async def shutdown(loop, mqtt_manager, http_com_manager):
    """
    Clean-up function to gracefully shutdown the application.
    """
    mqtt_manager.stop()
    http_com_manager.stop()
    await asyncio.sleep(1.1)
    loop.stop()

def pre_shutdown(loop, mqtt_manager, http_com_manager):
    asyncio.create_task(shutdown(loop, mqtt_manager, http_com_manager))

if __name__ == "__main__":
    load_dotenv("./config/.env")

    # Initialize managers
    mqtt_manager = mqttManager()
    mqtt_manager.use_default_user_passwd_credentials()
    mqtt_manager.connect()
    http_com_manager = HTTPCommunicationManager(interval=10)  # 15 minutes interval

    loop = asyncio.get_event_loop()

    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, pre_shutdown, loop, mqtt_manager, http_com_manager)

    try:
        # Run main application
        loop.run_until_complete(main(mqtt_manager, http_com_manager))
    except KeyboardInterrupt as e:
        raise e
    finally:
        # Clean-up
        mqtt_manager.stop()
        http_com_manager.stop()
        loop.close()
