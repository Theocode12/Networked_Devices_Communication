#!.venv/bin/python
from models.data_manager.storage_manager import StorageManager
import asyncio
import aiohttp

async def fetch_url(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            try:
                data = resp.json()
            except Exception as e:
                raise e
    return data

async def put_url(url):
    pass

def get_urls_from_ips(ips: list):
    return [f'http://{ip}/status' for ip in ips]

async def httpcom(ips: list):
    urls = get_urls_from_ips(ips)
    results = await asyncio.gather((fetch_url(url) for url in urls), return_exceptions=True)
    data = {}
    for i, result in enumerate(results):
        if isinstance(result) is Exception:
            pass # log exception
        else:
            # reformat data and append to data list
            pass
    stg = StorageManager()
    path = stg.create_db_path_from_topic('/dev/all')
    stg.save(path, data)

    
if __name__ == "__main__":
    print(get_urls_from_ips(['192.168.1.89', '192.168.4.2']))