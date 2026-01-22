import urllib.request
from pathlib import Path
from traceback import print_exc


def download_thing(directory, attachment_type, owner_id, object_id, url, extension):
    if object_id is None:
        directory = Path(directory) / attachment_type
        filename = f'{attachment_type}{owner_id}.{extension}'
    else:
        directory = Path(directory) / attachment_type / f'{attachment_type}{owner_id}'
        filename = f'{attachment_type}{owner_id}_{object_id}.{extension}'
    directory.mkdir(parents=True, exist_ok=True)
    dest = directory / filename
    print(f'Downloading {filename}')
    if dest.exists():
        print("Already downloaded, skipping")
        return
    try:
        urllib.request.urlretrieve(url, directory / filename)
    except:
        print(f"Could not download")
        print_exc()
