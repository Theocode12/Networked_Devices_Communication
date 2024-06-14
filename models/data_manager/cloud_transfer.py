from models.exceptions.exception import (
    CloudUploadError,
)
from models.db_engine.db import MetaDB
from models import ModelLogger
from models.data_manager import BaseManager
from models.data_manager.storage_manager import StorageManager
from typing import List, Dict, Union, Optional, Iterator
from util import (
    get_base_path,
    is_internet_connected,
    modify_data_to_dict,
)
from util import get_urls_from_ips, fetch_url_spreadsheet
from os import getenv
import os
import datetime
import asyncio
from dotenv import load_dotenv


class CTFlogger:
    """
    Class for logging cloud transfer activities.
    """

    logger = ModelLogger("cloud-transfer").customiseLogger()


class CloudTransfer:
    """
    This class helps in constructing URLs
    from environment variables and provided data lines,
    and it provides functionality to push data to these URLs.
    """

    def __init__(self) -> None:
        """
        Initialize the CloudTransfer instance and load environment variables.
        It sets the base URL for data transfer by combining the host
        and sheet ID retrieved from environment variables.
        """
        self.base_url = self.create_base_url()

    def create_base_url(self) -> str:
        """
        Create the base URL for the Google Apps Script execution.

        Retrieves the host and Google Sheet ID from
        environment variables and constructs the base URL.

        Returns:
            str: The base URL constructed from the host and Google Sheet ID.
        """
        host = getenv("GOOGLE_HOST")
        sheet_id = getenv("GOOGLE_SHEET_ID")
        return "{}/macros/s/{}/exec".format(
            get_urls_from_ips([host])[0],
            sheet_id,
        )

    def generate_query_string(self, data_line: str) -> str:
        """
        Generate a query string from a data line.

        Converts a data line into a dictionary
        and constructs a query string from the key-value pairs.

        Parameters:
            data_line (str): A line of data to be converted into query parameters.

        Returns:
            str: The generated query string.
        """
        query_string = "?"
        data_dict = modify_data_to_dict(data_line)
        for key, value in data_dict.items():
            query_string += "{}={}&".format(key, value)
        return query_string.rstrip("&")

    def create_url(self, data_line) -> str:
        """
        Create a complete URL with the base URL and query string.

        Combines the base URL with the generated query string from the data line.

        Parameters:
            data_line (str): A line of data to be converted into
                            query parameters and appended to the base URL.

        Returns:
            str: The complete URL with the base URL and query string.
        """
        return self.base_url + self.generate_query_string(data_line)

    async def push_data_to_datasheet(self, url, timeout: int = 2) -> None:
        """
        Push data to the specified URL asynchronously.

        Attempts to fetch data from the URL with a specified timeout.
        Handles any exceptions that occur during the fetch.

        Parameters:
            url (str): The URL to which data is to be pushed.
            timeout (int): Timeout duration (in seconds) for the fetch operation. Default is 2 seconds.

        Returns:
            None
        """
        try:
            data = await fetch_url_spreadsheet(url)
            # if "success" not in data:
            #     raise CloudUploadError
            CTFlogger.logger.info("Data successfully upload to datasheet")
        except:
            CTFlogger.logger.error("Failed to upload data to google sheet")
            raise CloudUploadError


class CloudTransferManager(BaseManager):
    """
    CloudTransferManager is responsible for managing the
    batch upload process of data and also concurrent upload of data to the cloud
    """

    collection_interval: Optional[int] = None

    def __init__(self, lock: Optional[asyncio.Lock] = None, **kwargs) -> None:
        """
        Initialize the CloudTransferManager.

        Parameters:
        - lock (Optional[object]): An optional lock object for resource synchronization.
        """
        self.cloud_transfer = CloudTransfer()
        self.kwargs = kwargs
        self.running = True
        self.lock = lock or asyncio.Lock()
        self.prev_time = None

        if getenv("MODE") == "dev":
            self.mode: str = "dev"
        elif getenv("MODE") == "inter-dev":
            self.mode: str = "inter-dev"
        else:
            self.mode: str = "prod"

    def _is_connected(self, timeout=3) -> bool:
        """
        Check if the cloud transfer is connected.

        Returns:
        - bool: True if connected, False otherwise.
        """
        return is_internet_connected(timeout)

    async def batch_upload(
        self,
        base_path: Optional[str] = None,
    ) -> None:
        """
        Perform batch upload of files to the cloud.

        Parameters:
        - base_path (Optional[str]): The base path for file storage.
        """
        meta_db = MetaDB()
        if not base_path:
            base_path = get_base_path()
        db_root = os.path.join(base_path, "data/")
        metadata = meta_db.get_all_metadata()
        last_upload_filepath = metadata.get("LastUploadedFile")
        if (
            last_upload_filepath is not None
            and last_upload_filepath
            and self._is_connected()
        ):
            try:
                CTFlogger.logger.info("Starting Batch Upload")
                await self.upload_files(last_upload_filepath, db_root)
                CTFlogger.logger.info("Batch upload complete")
            except CloudUploadError as e:
                raise e

    def get_time(self) -> str:
        """
        Gets the current time.

        Returns:
            str: Current time.
        """

        return datetime.datetime.now().time().strftime("%H:%M:%S")

    def is_send_time(
        self, hour: int = None, minute: int = None, second: int = None, now=None
    ) -> bool:
        """
        Returns True if the current time matches the given interval of hours, minutes, or seconds.

        Parameters:
        - hour (int, optional): Interval for hours.
        - minute (int, optional): Interval for minutes.
        - second (int, optional): Interval for seconds.

        Returns:
        - bool: True if the current time matches the given interval, False otherwise.
        """
        hour = hour if hour is not None else self.kwargs.get("hour")
        minute = minute if minute is not None else self.kwargs.get("minute")
        second = second if second is not None else self.kwargs.get("second")

        now = now or datetime.datetime.now()

        if self.prev_time is not None:
            if hour is not None and now.hour % hour == 0:
                self.prev_time = now
                return False
            if minute is not None and now.minute % minute == 0:
                self.prev_time = now
                return False
            if second is not None and now.second % second == 0:
                self.prev_time = now
                return False
        else:
            if (
                (hour is not None and hour != 0 and now.hour % hour == 0)
                or (minute is not None and minute != 0 and now.minute % minute == 0)
                or (second is not None and second !=0 and now.second % second == 0)
            ):
                self.prev_time = now
                return False
        return True

    async def upload_files(self, last_upload_filepath: str, db_root: str) -> None:
        """
        Upload a list of files to the cloud.

        Parameters:
        - base_path (str): The base path for file storage.
        - files (List[str]): A list of files to upload.
        """

        for filepath in StorageManager.get_unuploaded_files(
            last_upload_filepath, db_root
        ):
            try:
                await self.upload_file(filepath)
            except Exception as e:
                CTFlogger.logger.error("File: {} Uploading Failed".format(filepath))
                raise CloudUploadError(
                    f"Could not upload file: {filepath}\n Exception due to: {e}"
                )

    async def upload_file(self, filepath: str, metadata_path=None) -> None:
        """
        Upload the content of a file to the cloud.

        Parameters:
        - filepath (str): The path to the file.
        """
        meta_db = MetaDB(metadata_path, filepath, mode="r")
        meta_db.get_all_metadata()
        last_uploaded_file = meta_db.get_metadata("LastUploadedFile")

        if last_uploaded_file == filepath:
            last_uploaded_file_offset = meta_db.get_metadata("LastUploadedFileOffset")
        else:
            last_uploaded_file_offset = 0

        with meta_db:
            meta_db.fd.seek(last_uploaded_file_offset)
            finished = False
            while self._is_connected():
                line = meta_db.fd.readline()
                if not line:
                    finished = True
                    break  # End of file
                if self.mode == "dev":
                    url = "http://localhost:8080/"
                else:
                    url = self.cloud_transfer.create_url(line)
                async with self.lock:
                    try:
                        await self.cloud_transfer.push_data_to_datasheet(url)
                    except CloudUploadError as e:
                        raise e
                    else:

                        offset = meta_db.fd.tell()
                        meta_db.save_metadata(
                            meta={
                                "LastUploadedFileOffset": offset,
                                "LastUploadedFile": filepath,
                            }
                        )
        if not finished:
            CTFlogger.logger.error("Upload failed due to no internet connection")
            raise CloudUploadError("Upload failed due to no internet connection")

    async def start(self) -> None:
        """
        Logic for transferring data to cloud.
        """
        while self.running:
            if self.is_send_time() and self._is_connected():
                try:
                    await self.batch_upload()
                except CloudUploadError:
                    continue
            await asyncio.sleep(1)

    def stop(self) -> None:
        self.running = False
        CTFlogger.logger.info("Cloud Trasfer manager stopped")


async def main():
    import dotenv

    dotenv.load_dotenv("./config/.env")
    now = datetime.time(12, 1, 43)
    ctfm = CloudTransferManager(minute=15)
    await ctfm.start()


if __name__ == "__main__":
    asyncio.run(main())

    # ctf = CloudTransfer()
    # url = ctf.create_url(
    #     "date=06/06/2024,time=21:28:00,PoutW_0=0,Vpv_0=0,BuckCurr_0=0,Ppv_0=0,PoutVA_0=193,BusVolt_0=407.9,Vbat=50.8,PoutW_1=210,Vpv_1=0,BuckCurr_1=0,Ppv_1=0,PoutVA_1=244,BusVolt_1=402.5,PoutW_2=127,Vpv_2=0,BuckCurr_2=0,Ppv_2=0,PoutVA_2=193,BusVolt_2=405.6"
    # )
    # asyncio.run(ctf.push_data_to_datasheet(url))
    # print(url)
    # print(is_internet_connected())
