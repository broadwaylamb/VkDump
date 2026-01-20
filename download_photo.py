import json
import ssl
from pathlib import Path

from vk_api import VkTools

from auth import VkOfficialClientSession, log_in_with_official_client
from download_media import download_photo

def download_photo_album(directory, owner_id, album_id, session: VkOfficialClientSession):
    directory = Path(directory)
    api = session.api()
    tools = VkTools(api)
    response = tools.get_all('photos.get', 1000, {'owner_id': owner_id, 'album_id': album_id, 'extended': 1, 'photo_sizes': 1})['items']
    for photo in response:
        if 'tags' in photo and photo['tags']['count'] > 0:
            photo['tags'] = api.method('photos.getTags', {'owner_id': photo['owner_id'], 'photo_id': photo['id']})
        else:
            photo['tags'] = []
    album_dir = directory / f'album{owner_id}'
    album_dir.mkdir(parents=True, exist_ok=True)
    json_path = album_dir / f'album{owner_id}_{album_id}.json'
    json_path.write_text(json.dumps(response, indent=4, ensure_ascii=False))
    for photo in response:
        download_photo(directory, photo)

def download_all_albums(directory, owner_id, session: VkOfficialClientSession):
    directory = Path(directory)
    api = session.api()
    tools = VkTools(api)
    print(f"Downloading all albums for id{owner_id}")
    response = tools.get_all('photos.getAlbums', 1000, {'owner_id': owner_id, 'need_system': 1, 'need_covers': 1})['items']
    album_dir = directory / f'album{owner_id}'
    album_dir.mkdir(parents=True, exist_ok=True)
    json_path = album_dir / f'albums{owner_id}.json'
    json_path.write_text(json.dumps(response, indent=4, ensure_ascii=False))
    for album in response:
        print(f'Downloading photos in album {album['title']}')
        download_photo_album(directory, album['owner_id'], album['id'], session)

if __name__ == '__main__':
    ssl._create_default_https_context = ssl._create_unverified_context
    session = log_in_with_official_client()
    owner_id = input('Owner ID: ').strip()
    album_id = input('Album ID (or skip to download all albums): ').strip()
    if album_id:
        download_photo_album('.', owner_id, album_id, session)
    else:
        download_all_albums('.', owner_id, session)