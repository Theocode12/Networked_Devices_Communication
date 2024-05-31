from models.exceptions.exception import (
    FileOpenError,
    FileReadError,
    FileWriteError,
    FileCloseError,
    CreateDirectoryError,
    RemoveDirectoryError,
)
from models import ModelLogger
from typing import Optional, Dict, List, Any, Union, Tuple
from datetime import datetime
from util import get_base_path, convert_to_int_or_leave_unchanged, env_variables
import os
import io


class DBlogger:
    """
    The DBlogger class represents a logger for database operations.

    It provides a logger instance for logging database-related events.
    """

    logger = ModelLogger("db").customiseLogger()


class FileDB:
    """
    The FileDB class represents a simple file-based database manager.

    It provides methods for opening, closing, reading, and writing to files, as well as managing metadata.

    Attributes:
    - target (Optional[str]): The target file path.
    - fd (Optional[io.TextIOWrapper]): The file descriptor for the open file.
    - mode (Optional[str]): The mode in which to open the file ('r' for reading, 'w' for writing, etc.).

    Methods:
    - __init__(target: Optional[str] = None, mode: Optional[str] = None): Initialize the FileDB instance.
    - __enter__() -> "FileDB": Enter the context manager and open the file.
    - __exit__(exc_type, exc_value, trace) -> None: Exit the context manager and close the file.
    - create_dir(dir: str) -> str: Create a directory.
    - remove_dir(dir: str) -> str: Remove a directory.
    - create_file(path: Optional[str] = None) -> str: Create a file.
    - delete_file(path: str) -> None: Delete a file.
    - file_exits(path: str) -> bool: Check if a file exists.
    - get_db_filedir() -> str: Get the file directory for the database based on the current date.
    - set_target(path: str) -> str: Set the target file path for the database.
    - open(path: Optional[str] = None, mode: str = "r+") -> io.TextIOWrapper: Open a file for reading or writing.
    - close() -> None: Close the currently open file.
    - write(data: str) -> int: Write data to the open file.
    - write_data_line(data: Dict[str, Any]) -> int: Write a dictionary as a line to the open file.
    - readline() -> str: Read a line from the open file.
    - readlines() -> List[str]: Read all lines from the open file.
    """

    def __init__(
        self, target: Optional[str] = None, mode: Optional[str] = None
    ) -> None:
        """
        Initialize the FileDB instance.

        Args:
        - target (Optional[str]): The target file path.
        - mode (Optional[str]): The mode in which to open the file ('r' for reading, 'w' for writing, etc.).

        Attributes:
        - target: The target file path.
        - fd: The file descriptor for the open file.
        - mode: The mode in which to open the file.
        """
        self.target = target
        self.fd: io.TextIOWrapper = None
        self.mode = mode

    def __enter__(self) -> "FileDB":
        """
        Enter the context manager. Open the file for reading and writing.

        Returns:
        - The FileDB instance.
        """
        self.open(
            path=self.target,
            mode=self.mode or "r+",
        )
        return self

    def __exit__(self, exc_type, exc_value, trace) -> None:
        """
        Exit the context manager. Close the file.

        Args:
        - exc_type: The exception type.
        - exc_value: The exception value.
        - trace: The traceback.
        """
        self.close()
        if exc_type is not None:
            DBlogger.logger.critical(
                "Exception Trying to Access File {}: {}".format(exc_type, exc_value)
            )

    def create_dir(self, dir: str) -> str:
        """
        Create a directory.

        Args:
        - dir (str): The directory path.

        Returns:
        - The created directory path.

        Raises:
        - CreateDirectoryError: If an error occurs while creating the directory.
        """
        if dir:
            try:
                os.makedirs(dir, exist_ok=True)
                # DBlogger.logger.info("Directory created/exists: {}".format(dir))
            except Exception as e:
                raise CreateDirectoryError("Failed to create directory: {}".format(dir))
        return dir

    def remove_dir(self, dir: str) -> str:
        """
        Remove a directory.

        Args:
        - dir (str): The directory path.

        Returns:
        - The removed directory path.

        Raises:
        - RemoveDirectoryError: If an error occurs while removing the directory.
        """
        if dir:
            try:
                os.rmdir(dir)
                DBlogger.logger.info("Directory removed: {}".format(dir))
            except Exception as e:
                raise RemoveDirectoryError("Failed to remove directory: {}".format(dir))
        return dir

    def create_file(self, path: str) -> str:
        """
        Create a file.

        Args:
        - path (Optional[str]): The file path.

        Returns:
        - The created file path.

        Raises:
        - FileOpenError: If an error occurs while creating or opening the file.
        """

        self.create_dir("/".join(path.split("/")[:-1]))

        if not self.file_exits(path):
            with FileDB(path, "x") as db:
                db.write("")

            DBlogger.logger.info("File Created: {}".format(path))

        return path

    def delete_file(self, path: str) -> None:
        """
        Delete a file.

        Args:
        - path (str): The file path.
        """
        if self.file_exits(path):
            try:
                os.remove(path)
                DBlogger.logger.info("Deleted file: {}".format(path))
            except Exception:
                pass

    def file_exits(self, path: str) -> bool:
        """
        Check if a file exists.

        Args:
        - path (str): The file path.

        Returns:
        - True if the file exists, False otherwise.
        """
        return os.path.exists(path)

    def get_db_filedir(self, create=True) -> str:
        """
        Get the file path for the database based on the current date.

        Returns:
        - The generated file path.
        """
        now = datetime.now()
        year, month, day = now.year, now.month, now.day

        dir = os.path.join(
            get_base_path(),
            f"data/{year}/{month:02d}/{day:02d}",
        )

        if create:
            self.create_dir(dir)
        return dir

    def set_target(self, path: str) -> str:
        """
        Set the target file path for the database.

        Args:
        - path (str): The target file path.

        Returns:
        - The target file path.
        """
        self.close()  # For safety because fd doesn't correspond to target
        self.target = path
        return self.target

    def open(self, path: Optional[str] = None, mode: str = "r+") -> io.TextIOWrapper:
        """
        Open a file for reading or writing.

        Args:
        - path (Optional[str]): The path to the file. If None, self.target is used.
        - mode (str): The mode in which to open the file ('r' for reading, 'w' for writing, etc.).

        Returns:
        - The file descriptor.

        Raises:
        - FileOpenError: If an error occurs while opening the file.
        """
        if path:
            self.set_target(path)
        try:
            self.fd = open(self.target, mode)
        except Exception as e:
            raise FileOpenError("Error opening file: {}".format(self.target))
        return self.fd

    def close(self) -> None:
        """
        Close the currently open file.

        Raises:
        - FileCloseError: If an error occurs while closing the file.
        """
        try:
            if self.fd:
                self.fd.close()
        except Exception as e:
            raise FileCloseError("Error while closing file: {}".format(self.target))
        self.fd = None

    def write(self, data: str) -> int:
        """
        Write data to the open file.

        Args:
        - data (str): The data to write to the file.

        Returns:
        - The number of bytes written.

        Raises:
        - FileWriteError: If an error occurs while writing to the file.
        """
        try:
            if self.fd:
                self.fd.write(data)
        except Exception:
            DBlogger.logger.error("Error writing to file: {}".format(self.target))
            raise FileWriteError("Error writing to file: {}".format(self.target))

        return data

    def write_data_line(self, data: Dict[str, Any]) -> int:
        """
        Write a dictionary as a line to the open file.

        Args:
        - data (Dict[str, Any]): The data to write as a line.

        Returns:
        - The number of bytes written.

        Raises:
        - FileWriteError: If an error occurs while writing to the file.
        """
        line = ",".join([f"{key}={value}" for key, value in data.items()])
        return self.write(line + "\n")

    def readline(self) -> str:
        """
        Read a line from the open file.

        Returns:
        - The read line.

        Raises:
        - FileReadError: If an error occurs while reading from the file.
        """
        line = None
        try:
            if self.fd:
                line = self.fd.readline()
        except Exception:
            DBlogger.logger.error(
                "Error reading line from file: {}".format(self.target)
            )
            raise FileReadError("Error reading line from file: {}".format(self.target))
        return line

    def readlines(self) -> List[str]:
        """
        Read all lines from the open file.

        Returns:
        - The read lines.

        Raises:
        - FileReadError: If an error occurs while reading from the file.
        """
        lines = []
        try:
            if self.fd:
                lines = self.fd.readlines()
        except Exception:
            DBlogger.logger.error(
                "Error reading lines from file: {}".format(self.target)
            )
            raise FileReadError("Error reading lines from file: {}".format(self.target))
        return lines


class MetaDB(FileDB):
    """
    MetaDB is a class representing a metadata database that extends FileDB.
    It provides methods for retrieving, updating, saving, and clearing metadata.

    Attributes:
    - meta (Dict[str, Any]): A dictionary to store metadata.
    - metadata_lines (List[str]): A list of lines in the metadata file.

    Methods:
    - __init__(): Initialize a MetaDB instance.
    - retrieve_metadata_lines(path: Optional[str] = None, forcedb: bool = True) -> List[str]: Retrieve lines from a metadata file.
    - update_metadata_lines(meta: Dict[str, Any] = {}) -> List[str]: Update lines in the metadata file with provided metadata.
    - retrieve_metadata(path: Optional[str] = None, meta: List[str] = [], forcedb: bool = True) -> Dict[str, str]: Retrieve metadata from a file.
    - save_metadata(path: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> None: Save metadata to a file.
    - clear_metadata() -> None: Clear the metadata stored in the instance.
    - update_metadata(newmeta: Dict[str, str]) -> Dict[str, str]: Update the metadata with the provided key-value pairs.
    - readline(offset: int = None) -> str: Read a line from the open file.
    - readlines(offset: int = None) -> List[str]: Read all lines from the open file.
    - get_metadata_path() -> str: Get the path to the metadata file.
    """

    def __init__(self):
        """
        Initialize a MetaDB instance.

        Attributes:
        - meta: A dictionary to store metadata.
        - metadata_lines: A list of lines in the metadata.
        """
        self.meta = {}
        self.metadata_lines: List[str] = []
        super().__init__()

    def retrieve_metadata_lines(
        self, path: Optional[str] = None, forcedb: bool = True
    ) -> List[str]:
        """
        Retrieve lines from a metadata file.

        Args:
        - path (Optional[str]): The optional path to the metadata file.
        - forcedb (bool): Whether to force querying the database.

        Returns:
        - List[str]: A list of lines from the metadata file.
        """
        if not path:
            path = self.get_metadata_path()
        if forcedb:
            self.set_target(path)
            with self:
                self.metadata_lines = [
                    line.rstrip("\n") for line in super().readlines()
                ]

        return self.metadata_lines

    def update_metadata_lines(self, meta: Dict[str, Any] = {}) -> List[str]:
        """
        Update lines in the metadata file with provided metadata.

        Args:
        - meta (Dict): Key-value pairs to update in the metadata.

        Returns:
        - List[str]: The updated list of lines from the metadata file.
        """
        meta = meta or self.meta
        keys = set(meta.keys())
        for index, line in enumerate(self.metadata_lines):
            if not line.startswith("#") and line:
                datakey = line.split("=")[0]
                if datakey in keys:
                    self.metadata_lines[index] = "{}={}".format(datakey, meta[datakey])
                    keys.remove(datakey)
        for key in keys:
            self.metadata_lines.append("{}={}".format(key, meta[key]))
        return self.metadata_lines

    def retrieve_metadata(
        self, path: Optional[str] = None, meta: List[str] = [], forcedb: bool = True
    ) -> Dict[str, str]:
        """
        Retrieve metadata from a file.

        Args:
        - path (Optional[str]): The optional path to the metadata file.
        - meta (List[str]): Optional keys to retrieve from the metadata_lines.
        - forcedb (bool): Whether to force query the database.

        Returns:
        - Dict[str, str]: The retrieved metadata.
        """
        lines = self.retrieve_metadata_lines(path, forcedb)
        for line in lines:
            if not line.startswith("#") and "=" in line:
                key, val = [line.strip() for line in line.split("=")]
                if not meta or key in meta:
                    self.meta[key] = convert_to_int_or_leave_unchanged(val)
        return self.meta

    def save_metadata(
        self, path: Optional[str] = None, meta: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save metadata to a file.

        The metadata is updated with the provided key-value pairs, and the updated metadata is saved to a file.

        Args:
        - path (Optional[str]): The optional path to the metadata file.
        - meta (Dict): Key-value pairs to update in the metadata.

        Raises:
        - Exception: If an error occurs while saving the metadata.
        """
        if not path:
            path = self.get_metadata_path()

        if not meta:
            meta = self.meta

        if self.file_exits(path):
            self.retrieve_metadata_lines(path)

        with self as db:
            for line in self.update_metadata_lines(meta):
                db.write(line + "\n")
        DBlogger.logger.info("Updated metadata saved to file")

    def clear_metadata(self) -> None:
        """
        Clear the metadata stored in the instance.

        This method resets the metadata dictionary to an empty state.
        """
        self.meta = {}

    def update_metadata(self, newmeta: Dict[str, str]) -> Dict[str, str]:
        """
        Update the metadata with the provided key-value pairs.

        Args:
        - newmeta (Dict): Key-value pairs to update in the metadata.

        Returns:
        - Dict[str, str]: The updated metadata.
        """
        if newmeta:
            self.meta.update(newmeta)
        return self.meta

    def readline(self, offset: int = None) -> str:
        """
        Read a line from the open file.

        Args:
        - offset (int): Metadata to determine the file offset.

        Returns:
        - str: The read line.

        Raises:
        - Exception: If an error occurs while reading from the file.
        """
        self.fd.seek(offset or self.meta.get("Offset", 0))
        line = super().readline()
        self.update_metadata({"Offset": self.fd.tell()})
        return line

    def readlines(self, offset: int = None) -> List[str]:
        """
        Read all lines from the open file.

        Args:
        - offset (int): Metadata to determine the file offset.

        Returns:
        - List[str]: The list of read lines.
        """
        if offset is not None:
            self.fd.seek(offset)
        lines = super().readlines()
        self.update_metadata({"Offset": self.fd.tell()})
        return lines

    def get_metadata_path(self) -> str:
        """
        Get the path to the metadata file.

        Returns:
        - str: The path to the metadata file.
        """
        return os.path.join("{}".format(get_base_path()), "config", "meta.txt")
