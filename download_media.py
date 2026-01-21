from pathlib import Path
from traceback import print_exc

from auth import VkOfficialClientSession
from download_audio import download_audio
from download_thing import download_thing

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

def download_media_attachment(directory, attachment, session: VkOfficialClientSession):
    directory = Path(directory)
    if attachment['type'] == 'photo':
        download_photo(directory, attachment['photo'])
        return
    elif attachment['type'] == 'posted_photo':
        photo = attachment['posted_photo']
        url = photo['photo_604']
        owner_id = photo['owner_id']
        object_id = photo['id']
        extension = 'jpg'
    elif attachment['type'] == 'video':
        return # слишком сложно и долго
    elif attachment['type'] == 'audio':
        audio = attachment['audio']
        print(f'Downloading audio attachment "{audio['artist']} - {audio['title']}"')
        directory = directory / 'audio' / f'audio{audio["owner_id"]}'
        directory.mkdir(parents=True, exist_ok=True)
        try:
            download_audio(directory, audio)
        except:
            print(f"Could not download audio")
            print_exc()
        return
    elif attachment['type'] == 'document':
        document = attachment['document']
        url = document['url']
        owner_id = document['owner_id']
        object_id = document['id']
        extension = document['ext']
    elif attachment['type'] == 'graffiti':
        graffiti = attachment['graffiti']
        if 'photo_604' in graffiti:
            url = graffiti['photo_604']
        elif 'photo_586' in graffiti:
            url = graffiti['photo_586']
        elif 'photo_200' in graffiti:
            url = graffiti['photo_200']
        else:
            return
        owner_id = graffiti['owner_id']
        object_id = graffiti['id']
        extension = 'png'
    elif attachment['type'] == 'album':
        album = attachment['album']
        print(f'Downloading attached photo album {album['title']}')
        download_photo_album(directory, album['owner_id'], album['id'], session)
        return
    elif attachment['type'] == 'sticker':
        sticker = attachment['sticker']
        images = sticker['images'].sort(reverse=True, key=lambda x: x['width'])
        if len(images) == 0:
            return
        url = images[0]['url']
        owner_id = sticker['product_id']
        object_id = sticker['sticker_id']
        extension = 'png'
    else:
        return
    download_thing(directory, attachment['type'], owner_id, object_id, url, extension)