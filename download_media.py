from pathlib import Path

from auth import VkOfficialClientSession
from download_audio import download_audio
from download_photo import download_photo_album
from download_thing import download_thing, download_photo
from profile_cache import ProfileCache


def download_media_attachment(directory, attachment, session: VkOfficialClientSession, profile_cache: ProfileCache=None):
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
        download_audio(directory, audio)
        return
    elif attachment['type'] == 'doc':
        document = attachment['doc']
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
        download_photo_album(directory, album['owner_id'], album['id'], session, profile_cache)
        return
    elif attachment['type'] == 'sticker':
        sticker = attachment['sticker']
        if len(sticker['images']) == 0:
            return
        image = max(sticker['images'], key=lambda x: x['width'])
        url = image['url']
        owner_id = sticker['product_id']
        object_id = sticker['sticker_id']
        extension = 'png'
    elif attachment['type'] == 'wall':
        if 'attachments' in attachment:
            print(f'Downloading attachments for post {attachment["id"]}...')
            for attachment in attachment['attachments']:
                download_media_attachment(directory, attachment, session, profile_cache)
        return
    else:
        return
    download_thing(directory, attachment['type'], owner_id, object_id, url, extension)