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
        print_exc()
        print(f"Could not download {filename}")


def download_photo(directory, photo):
    urls = {}
    for size in photo['sizes']:
        urls[size['type']] = size['url']

    if 'w' in urls:
        url = urls['w']
    elif 'z' in urls:
        url = urls['z']
    elif 'y' in urls:
        url = urls['y']
    elif 'x' in urls:
        url = urls['x']
    elif 'm' in urls:
        url = urls['m']
    elif 's' in urls:
        url = urls['s']
    else:
        return
    download_thing(directory, 'photo', photo['owner_id'], photo['id'], url, 'jpg')
