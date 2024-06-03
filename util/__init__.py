from dotenv import dotenv_values
from typing import Union, Dict
import os
import subprocess
import aiohttp


def get_base_path():
    return "".join([os.getcwd(), "/"])


def is_internet_connected():
    try:
        subprocess.check_output(["timeout", "1", "ping", "-c", "1", "google.com"])
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False


def convert_to_int_or_leave_unchanged(value: str) -> Union[int, str]:
    """
    Attempt to convert a string to an integer. If successful, return the integer;
    otherwise, return the original string.

    Args:
    - value (str): The input string.

    Returns:
    - Union[int, str]: The converted integer or the original string.
    """
    if value.isdigit():
        return int(value)
    return value


def env_variables() -> Dict[str, str]:
    """
    Load environment variables from the .env file.
    """
    env_path = os.path.join(get_base_path(), "config", ".env")
    env_variables = dotenv_values(env_path)
    return env_variables


def modify_data_to_dict(line: str) -> Dict[str, Union[str, float]]:
    data = line.rstrip("\n").split(",")
    data_dict = {}
    for datum in data:
        param, value = datum.split("=")
        if value == "None":
            value = None
        else:
            value = value.strip()
        data_dict[param.strip()] = value

    return data_dict


async def fetch_url(url, timeout=1):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=timeout) as resp:
            try:
                data = await resp.json()
            except Exception as e:
                raise e
    return data

def get_urls_from_ips(ips: list):
    return [f'http://{ip}' for ip in ips]
