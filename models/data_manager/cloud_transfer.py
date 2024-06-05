from models.exceptions.exception import (
    AWSCloudConnectionError,
    AWSCloudUploadError,
)
from models.db_engine.db import MetaDB
from models import ModelLogger
from multiprocessing.connection import Connection
from typing import List, Dict, Union, Optional
from util import (
    get_base_path,
    is_internet_connected,
    modify_data_to_dict,
)
from util import get_urls_from_ips, fetch_url
from os import getenv
import sys
import json
import os
from dotenv import load_dotenv


class CTFlogger:
    """
    Class for logging cloud transfer activities.
    """

    logger = ModelLogger("cloud-transfer").customiseLogger()


class CloudTransfer:
    """
    This class helps in constructing URLs from environment variables and provided data lines,
    and it provides functionality to push data to these URLs.
    """

    def __init__(self) -> None:
        """
        Initialize the CloudTransfer instance and load environment variables.
        It sets the base URL for data transfer by combining the host and sheet ID retrieved from environment variables.
        """
        self.base_url = self.create_base_url()

    def create_base_url(self):
        """
        Create the base URL for the Google Apps Script execution.

        Retrieves the host and Google Sheet ID from environment variables and constructs the base URL.

        Returns:
            str: The base URL constructed from the host and Google Sheet ID.
        """
        host = getenv("GOOGLE_HOST")
        sheet_id = getenv("GOOGLE_SHEET_ID")
        return "{}/macros/s/{}/exec".format(
            get_urls_from_ips([host])[0],
            sheet_id,
        )

    def generate_query_string(self, data_line):
        """
        Generate a query string from a data line.

        Converts a data line into a dictionary and constructs a query string from the key-value pairs.

        Parameters:
            data_line (str): A line of data to be converted into query parameters.

        Returns:
            str: The generated query string.
        """
        query_string = "?"
        data_dict = modify_data_to_dict(data_line)
        for key, value in data_dict.items():
            query_string += "{}={}&".format(key, value)
        return query_string.rstrip('&')

    def create_url(self, data_line):
        """
        Create a complete URL with the base URL and query string.

        Combines the base URL with the generated query string from the data line.

        Parameters:
            data_line (str): A line of data to be converted into query parameters and appended to the base URL.

        Returns:
            str: The complete URL with the base URL and query string.
        """
        return self.base_url + self.generate_query_string(data_line)

    async def push_data_line(self, url, timeout: int = 2) -> None:
        """
        Push data to the specified URL asynchronously.

        Attempts to fetch data from the URL with a specified timeout. Handles any exceptions that occur during the fetch.

        Parameters:
            url (str): The URL to which data is to be pushed.
            timeout (int): Timeout duration (in seconds) for the fetch operation. Default is 2 seconds.

        Returns:
            None
        """
        try:
            data = await fetch_url(url, 2, "text")
        except:
            pass  # Log some stuff


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
        return is_internet_connected()

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

    def run(self):
        """
        Logic for transferring data to cloud.

        Parameters:
        - recv_cmd_pipe (Connection): Pipe to receive commands.
        - data_pipe (Optional[Connection]): Unused for now.
        """
        db = MetaDB()

        while True:

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
    load_dotenv("./config/.env")
    ctf = CloudTransfer()
    url = ctf.create_url('date=2024-06-05,time=03:22:00,Output_Watts_0=11,PV_Voltage_0=0,Buck_Converter_Current_0=0,PV_Power_0=1,Output_VA_0=179,Bus_Voltage_0=404.6,Battery_Voltage_0=0,Output_Watts_1=94,PV_Voltage_1=0,Buck_Converter_Current_1=0,PV_Power_1=0,Output_VA_1=179,Bus_Voltage_1=399.5,Battery_Voltage_1=0')
    print(url)
