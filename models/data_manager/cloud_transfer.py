from awscrt import mqtt
from awsiot import mqtt_connection_builder
from models.exceptions.exception import (
    AWSCloudConnectionError,
    AWSCloudDisconnectError,
    FileOpenError,
    AWSCloudUploadError,
)
from models.db_engine.db import MetaDB
from models import ModelLogger
from multiprocessing.connection import Connection, Pipe
from multiprocessing import Process
from typing import List, Dict, Union, Optional
from time import sleep
from util import (
    get_base_path,
    is_internet_connected,
    env_variables,
    modify_data_to_dict,
)
import sys
import json
import os


class CTFlogger:
    """
    Class for logging cloud transfer activities.
    """

    logger = ModelLogger("cloud-transfer").customiseLogger(
        filename=os.path.join(
            "{}".format(get_base_path()), "logs", "cloud_transfer.log"
        )
    )


def on_connection_interrupted(connection, error, **kwargs):
    """
    Callback function invoked when the MQTT connection is interrupted.

    Parameters:
        - connection: The MQTT connection object.
        - error (str): The error message describing the interruption.
        - **kwargs: Additional keyword arguments.
    """

    CTFlogger.logger.error("Connection interrupted. error: {}".format(error))


def on_connection_resumed(connection, return_code, session_present, **kwargs):
    """
    Callback function invoked when the MQTT connection is resumed.

    Parameters:
        - connection: The MQTT connection object.
        - return_code (int): The return code indicating the connection status.
        - session_present (bool): Indicates if the session is present.
        - **kwargs: Additional keyword arguments.
    """
    CTFlogger.logger.info(
        "Connection resumed. return_code: {} session_present: {}".format(
            return_code, session_present
        )
    )

    if return_code == mqtt.ConnectReturnCode.ACCEPTED and not session_present:
        CTFlogger.logger.info(
            "Session did not persist. Resubscribing to existing topics..."
        )
        resubscribe_future, _ = connection.resubscribe_existing_topics()

        # Cannot synchronously wait for resubscribe result because we're on the connection's event-loop thread,
        # evaluate result with a callback instead.
        resubscribe_future.add_done_callback(on_resubscribe_complete)


def on_resubscribe_complete(resubscribe_future):
    """
    Callback function invoked when resubscription to topics is complete.

    Parameters:
        - resubscribe_future: The future object representing the resubscription process.
    """
    resubscribe_results = resubscribe_future.result()
    CTFlogger.logger.info("Resubscribe results: {}".format(resubscribe_results))

    for topic, qos in resubscribe_results["topics"]:
        if qos is None:
            sys.exit("Server rejected resubscribe to topic: {}".format(topic))


def on_message_received(topic, payload, dup, qos, retain, **kwargs):
    """
    Callback function invoked when a message is received.

    Parameters:
        - topic (str): The topic from which the message was received.
        - payload (bytes): The payload of the message.
        - dup (bool): Indicates if the message is a duplicate.
        - qos (int): The quality of service level.
        - retain (bool): Indicates if the message should be retained.
        - **kwargs: Additional keyword arguments.
    """
    CTFlogger.logger.info("Received message from topic '{}': {}".format(topic, payload))


def on_connection_success(connection, callback_data):
    """
    Callback function invoked when the MQTT connection is successful.

    Parameters:
        - connection: The MQTT connection object.
        - callback_data: Additional callback data.
    """
    assert isinstance(callback_data, mqtt.OnConnectionSuccessData)
    CTFlogger.logger.info(
        "Connection Successful with return code: {} session present: {}".format(
            callback_data.return_code, callback_data.session_present
        )
    )


def on_connection_failure(connection, callback_data):
    """
    Callback function invoked when the MQTT connection fails.

    Parameters:
        - connection: The MQTT connection object.
        - callback_data: Additional callback data.
    """
    assert isinstance(callback_data, mqtt.OnConnectionFailureData)
    CTFlogger.logger.warning(
        "Connection failed with error code: {}".format(callback_data.error)
    )


def on_connection_closed(connection, callback_data):
    """
    Callback function to handle the event of a connection being closed.

    Parameters:
    - connection: The connection object.
    - callback_data: Additional data associated with the callback.
    """
    CTFlogger.logger.warning("Connection closed")


class CloudTransfer:
    """
    CloudTransfer is responsible for establishing and managing MQTT connections for cloud data transfer.
    """

    endpoint = ""
    cert_filepath = ""
    pri_key_filepath = ""
    ca_filepath = ""
    client_id = ""
    message_topic = ""

    def __init__(self) -> None:
        """
        Initialize the CloudTransfer instance and load environment variables.
        """
        self.mqtt_connection = None
        self.connected = False
        self._load_env()

    @classmethod
    def _load_env(cls) -> None:
        """
        Load environment variables from the .env file.
        """
        for key, value in env_variables().items():
            setattr(CloudTransfer, key, value)

    def connect(self) -> None:
        """
        Establish a connection to the MQTT broker.
        """
        self.mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=self.endpoint,
            cert_filepath=self.cert_filepath,
            pri_key_filepath=self.pri_key_filepath,
            ca_filepath=self.ca_filepath,
            on_connection_interrupted=on_connection_interrupted,
            on_connection_resumed=on_connection_resumed,
            client_id=self.client_id,
            clean_session=False,
            keep_alive_secs=30,
            http_proxy_options=None,
            on_connection_success=on_connection_success,
            on_connection_failure=on_connection_failure,
            on_connection_closed=on_connection_closed,
        )

        try:
            mqtt_future = self.mqtt_connection.connect()
            # Future.result() waits until a result is available
            mqtt_future.result(timeout=2)
            CTFlogger.logger.info("Connection sucessfully established")
            self.connected = True
        except Exception:
            CTFlogger.logger.error("Failed to establish connection")
            raise AWSCloudConnectionError

    def disconnect(self) -> None:
        """
        Disconnect from the MQTT broker.
        """
        try:
            disconnect_future = self.mqtt_connection.disconnect()
            disconnect_future.result(2)
            CTFlogger.logger.info("Disconnected successfully")
            self.connected = False
        except Exception:
            raise AWSCloudDisconnectError

    def publish(self, data: dict, timeout: int = 2) -> None:
        """
        Publish data to the specified MQTT topic.

        Parameters:
        - data (Dict[str, Any]): The data to be published.
        - timeout (int): Timeout duration for the publish operation.
        """
        try:
            message_json = json.dumps(data)
            pub_future, id = self.mqtt_connection.publish(
                topic=self.message_topic,
                payload=message_json,
                qos=mqtt.QoS.AT_LEAST_ONCE,
            )
            pub_future.result(timeout)
            CTFlogger.logger.info("Data Published successfully")
        except TimeoutError:
            CTFlogger.logger.info("Data failed to publish")
            raise AWSCloudUploadError("Data failed to publish")

    def subscribe(self, topic):
        """
        Subscribe to the specified MQTT topic.

        Parameters:
        - topic (str): The topic to subscribe to.
        """
        pass


class CloudTransferManager:
    """
    CloudTransferManager is responsible for managing the batch upload process of data and also concurrent upload of data to the cloud
    """

    collection_interval: Optional[int] = None

    def __init__(self, lock=None) -> None:
        """
        Initialize the CloudTransferManager.

        Parameters:
        - lock (Optional[object]): An optional lock object for resource synchronization.
        """
        self.cloud_transfer = CloudTransfer()
        self.meta_db = MetaDB()
        self.lock = lock

    def batch_upload(
        self,
        base_path: Optional[str] = None,
    ) -> None:
        """
        Perform batch upload of files to the cloud.

        Parameters:
        - base_path (Optional[str]): The base path for file storage.
        """
        # Only works on Linux and Mac OS
        if not base_path:
            base_path = get_base_path()
        CTFlogger.logger.info("Starting Batch Upload")
        db_path = os.path.join(base_path, "data/")
        # Remember to lock resources (file when using them)
        metadata = self.meta_db.retrieve_metadata()
        last_upload_filepath = metadata.get("LastUploadFile")
        if (
            last_upload_filepath is not None
            and last_upload_filepath
            and self._is_connected()
        ):
            try:
                last_upload_date = last_upload_filepath.replace(db_path, "")
                files = self.get_unuploaded_files(last_upload_date.split("/"), db_path)
                self.upload_files(db_path, files)
                CTFlogger.logger.info("Batch upload complete")
            except AWSCloudUploadError as e:
                raise e

    def upload_files(self, base_path: str, files: List[str]) -> None:
        """
        Upload a list of files to the cloud.

        Parameters:
        - base_path (str): The base path for file storage.
        - files (List[str]): A list of files to upload.
        """
        for file in files:
            filepath = os.path.join(base_path, file)
            try:
                self.upload_file(filepath)
            except Exception:
                CTFlogger.logger.error("File: {} Uploading Failed".format(filepath))
                raise AWSCloudUploadError(f"Could not upload file: {filepath}")

    def upload_file(self, filepath: str) -> None:
        """
        Upload the content of a file to the cloud.

        Parameters:
        - filepath (str): The path to the file.
        """
        self.meta_db.set_target(filepath)
        with self.meta_db as db:
            lines = db.readlines(self.meta_db.meta.get("Offset", 0))

        if self._is_connected():
            for line in lines:
                data = modify_data_to_dict(line)
                self.cloud_transfer.publish(data)

            self.meta_db.save_metadata(
                meta={
                    "LastUploadFile": filepath,
                    "Offset": self.meta_db.meta.get("Offset", 0),
                }
            )
            self.meta_db.meta["Offset"] = None
            CTFlogger.logger.info("File: {} Successfully uploaded".format(filepath))

    def _is_connected(self) -> bool:
        """
        Check if the cloud transfer is connected.

        Returns:
        - bool: True if connected, False otherwise.
        """
        return is_internet_connected() and self.cloud_transfer.connected

    def get_unuploaded_files(
        self, last_upload_file_date: List[str], db_path: str
    ) -> List[str]:
        """
        Get a list of unuploaded files based on the last upload file date.

        Parameters:
        - last_upload_file_date (List[str]): The date components of the last upload file.
        - db_path (str): The path to the database.

        Returns:
        - List[str]: A list of unuploaded files.
        """
        files_to_be_uploaded = []

        # Function to filter directories and files based on LastUploadFile
        def filter_dirs_or_files(files, index):
            try:
                file_index = files.index(last_upload_file_date[index])
                for file in files[:file_index]:
                    files.remove(file)
            except ValueError:
                pass

        for root, dirs, files in os.walk(db_path):
            dirs.sort()
            files.sort()

            # Filter directories based on LastUploadFile
            filter_dirs_or_files(dirs, 0)  # Year
            filter_dirs_or_files(dirs, 1)  # Month

            # Filter files based on LastUploadFile
            filter_dirs_or_files(files, 2)  # Day

            # Append the remaining files to files_to_be_uploaded
            files_to_be_uploaded.extend(
                os.path.join(root[-7:], file) for file in files
            )  # Fix magic number 7

        return files_to_be_uploaded

    def run(self, recv_cmd_pipe: Connection, data_pipe: Connection = None):
        """
        Logic for transferring data to cloud.

        Parameters:
        - recv_cmd_pipe (Connection): Pipe to receive commands.
        - data_pipe (Optional[Connection]): Unused for now.
        """
        db = MetaDB()

        while True:
            if recv_cmd_pipe.poll():
                command = recv_cmd_pipe.recv()
                if command == "END":
                    CTFlogger.logger.info("Cloud Transfer Stopped")
                    break

            if self._is_connected():
                db.set_target(db.get_db_filepath())
                if db.target != self.meta_db.retrieve_metadata(
                    path=db.get_metadata_path()
                ).get("LastUploadFile"):
                    try:
                        self.batch_upload()
                    except AWSCloudUploadError:
                        continue
                else:
                    db.retrieve_metadata()
                    db.set_target(db.get_db_filepath())
                    with db as db_connection:
                        line = db_connection.readline()
                    if line:
                        data = modify_data_to_dict(line)
                        self.cloud_transfer.publish(data)  # fix publish timeout
                        db.save_metadata()
            else:
                try:
                    self.cloud_transfer.connect()
                except AWSCloudConnectionError:
                    pass


if __name__ == "__main__":
    ctf = CloudTransfer()
    ctf.connect()
    if ctf.connected == True:
        ctf.publish(
            {
                "longitude": "7.3733° E",
                "latitude": "6.8429° N",
                "current": "120",
                "voltage": "48",
                "power": "6560",
            }
        )
        ctf.disconnect()
