from models.exceptions.exception import (
    CloudUploadError,
)
from models.db_engine.db import MetaDB
from models import ModelLogger
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
            print('to push to spreadsheet')
            data = await fetch_url_spreadsheet(url)
            print(data)
            # if "success" not in data:
            #     raise CloudUploadError
            CTFlogger.logger.info('Data successfully upload to datasheet')
        except:
            CTFlogger.logger.error("Failed to upload data to google sheet")
            raise CloudUploadError


class CloudTransferManager:
    """
    CloudTransferManager is responsible for managing the
    batch upload process of data and also concurrent upload of data to the cloud
    """

    collection_interval: Optional[int] = None

    def __init__(self, interval=2, lock=None) -> None:
        """
        Initialize the CloudTransferManager.

        Parameters:
        - lock (Optional[object]): An optional lock object for resource synchronization.
        """
        self.cloud_transfer = CloudTransfer()
        self.interval = int(interval)+1
        self.running = True

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

    async def upload_files(self, last_upload_filepath: str, db_root: str) -> None:
        """
        Upload a list of files to the cloud.

        Parameters:
        - base_path (str): The base path for file storage.
        - files (List[str]): A list of files to upload.
        """
        for filepath in self.get_unuploaded_files(last_upload_filepath, db_root):
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
                url = self.cloud_transfer.create_url(line)
                try:
                    print('in upload file checking intenet method')
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

    def _is_connected(self, timeout=3) -> bool:
        """
        Check if the cloud transfer is connected.

        Returns:
        - bool: True if connected, False otherwise.
        """
        return is_internet_connected(timeout)
    

    def get_unuploaded_files(
        self, last_upload_filepath: str, db_path: str
    ) -> Iterator[str]:
        """
        Get a list of unuploaded files based on the last upload file date.

        Parameters:
        - last_upload_file_date (List[str]): The date components of the last upload file.
        - db_path (str): The path to the database.

        Returns:
        - List[str]: A list of unuploaded files.
        """

        last_upload_date = datetime.datetime.strptime(
            last_upload_filepath, os.path.join(db_path, "%Y/%m/%d/inverter/all")
        )
        current_date = datetime.datetime.now()
        date_range = (current_date - last_upload_date).days
        if date_range == 0:
            yield last_upload_filepath
        else:
            for i in range(1, date_range + 1):
                date = last_upload_date + datetime.timedelta(days=i)
                dir_path = os.path.join(
                    db_path, date.strftime("%Y/%m/%d"), "inverter", "all"
                )
                if os.path.exists(dir_path):
                    yield dir_path

    def get_time(self) -> str:
        """
        Gets the current time.

        Returns:
            str: Current time.
        """
        from datetime import datetime
        return datetime.now().time().strftime("%H:%M:%S")
    
    def is_send_time(self, curr_time: str = None, minute_interval: int = 3) -> bool:
        """
        Checks if it's time to save data.

        Args:
            curr_time (str, optional): Current time string. Defaults to None.
            minute_interval (int, optional): Interval in minutes. Defaults to 3.

        Returns:
            bool: True if it's time to save data, False otherwise.
        """
        if not curr_time:
            curr_time = self.get_time()
        curr_min = int(curr_time.split(":")[1])
        print(curr_min)
        if (not (curr_min % minute_interval)):
            print('truthy')
            return True
        print('falsy')
        return False


    async def start(self) -> None:
        """
        Logic for transferring data to cloud.
        """

        while self.running:
            if self.is_send_time(minute_interval=self.interval) and self._is_connected():
                try:
                    print('in running')
                    await self.batch_upload()
                except CloudUploadError:
                    continue

    def stop(self) -> None:
        self.running = False
        CTFlogger.logger.info("Cloud Trasfer manager stopped")


if __name__ == "__main__":
    import asyncio

    load_dotenv("./config/.env")
    ctf = CloudTransfer()
    url = ctf.create_url(
        "date=06/06/2024,time=21:28:00,PoutW_0=0,Vpv_0=0,BuckCurr_0=0,Ppv_0=0,PoutVA_0=193,BusVolt_0=407.9,Vbat=50.8,PoutW_1=210,Vpv_1=0,BuckCurr_1=0,Ppv_1=0,PoutVA_1=244,BusVolt_1=402.5,PoutW_2=127,Vpv_2=0,BuckCurr_2=0,Ppv_2=0,PoutVA_2=193,BusVolt_2=405.6"
    )
    # asyncio.run(ctf.push_data_to_datasheet(url))
    print(url)
    # print(is_internet_connected())
    ctfm = CloudTransferManager()
    asyncio.run(ctfm.start())
    # asyncio.run(ctfm.upload_files('/home/user/Solar_Station_Communication/data/2024/06/03/inverter/all', '/home/user/Solar_Station_Communication/data/'))
    # for filepath in ctfm.get_unuploaded_files('/home/user/Solar_Station_Communication/data/2024/06/03/inverter/all', '/home/user/Solar_Station_Communication/data/'):
    #     print(filepath)
    # files = ctfm.get_unuploaded_files(
    #     ["30", "05", "2024"], "/home/valentine/Solar_Station_Communication/data"
    # )
    # print(files)
    # asyncio.run(
    #     ctfm.upload_file(
    #         "/home/valentine/Solar_Station_Communication/data/2024/06/03/inverter/all"
    #     )
    # )
