import json
import re
import ssl
from pathlib import Path
from traceback import print_exc

from vk_api import VkTools, VkToolsException, VkApiError

from auth import VkOfficialClientSession, log_in_with_official_client
from utils import PROFILE_FIELDS
from download_thing import download_photo
from utils import get_likes
from profile_cache import ProfileCache
from vktools_with_profiles import VkToolsWithProfiles


def download_photo_album(directory, owner_id, album_id, session: VkOfficialClientSession, with_likes=False, profile_cache: ProfileCache=None):
    directory = Path(directory)
    api = session.api()
    tools = VkToolsWithProfiles(api)
    should_save_profile_cache = profile_cache is None
    album_dir = directory / 'album' / f'album{owner_id}'
    album_dir.mkdir(parents=True, exist_ok=True)
    full_json_path = album_dir / f'album{owner_id}_{album_id}.json'
    if profile_cache is None:
        profile_cache = ProfileCache(directory)

    try:
        response = tools.get_all(
            method='photos.get',
            max_count=1000,
            values={'owner_id': owner_id, 'album_id': album_id, 'extended': 1, 'photo_sizes': 1},
            profile_cache=profile_cache
        )['items']
    except VkToolsException:
        print_exc()
        print("Could not download")
        return
    except VkApiError:
        print_exc()
        print("Could not download")
        return

    for photo in response:
        if 'tags' in photo and photo['tags']['count'] > 0:
            print(f'Downloading tags for photo {photo["owner_id"]}_{album_id}')
            photo['tags'] = api.method(
                method='photos.getTags',
                values={
                    'owner_id': photo['owner_id'],
                    'photo_id': photo['id'],
                },
            )
            print(f'Downloading users for tags for photo {photo["owner_id"]}_{album_id}')
            user_ids = []
            for tag in photo['tags']:
                if 'user_id' in tag:
                    user_ids.append(str(tag['user_id']))
            users = api.method(
                method='users.get',
                values={
                    'user_ids': ','.join(user_ids),
                    'fields': PROFILE_FIELDS,
                },
            )
            profile_cache.cache_profiles(users)
        else:
            photo['tags'] = []

        if 'comments' in photo and photo['comments']['count'] > 0:
            print(f'Downloading comments for photo {photo["owner_id"]}_{photo['id']}')
            try:
                comments = tools.get_all(
                    method='photos.getComments',
                    max_count=100,
                    values={
                        'owner_id': photo['owner_id'],
                        'photo_id': photo['id'],
                        'need_likes': True,
                        'sort': 'asc',
                        'extended': 1,
                        'fields': PROFILE_FIELDS,
                    },
                    profile_cache=profile_cache,
                )['items']
            except VkToolsException:
                comments = []
            except VkApiError:
                comments = []

            if with_likes:
                for comment in comments:
                    if 'likes' not in comment or 'count' not in comment['likes'] or comment['likes']['count'] == 0:
                        continue
                    print(f'Downloading likes for comment {comment['id']}...')
                    comment['likes']['list'] = get_likes(tools, owner_id, 'photo_comment', comment['id'], profile_cache)

            for comment in comments:
                if 'attachments' in comment:
                    print(f'Downloading attachments for comment {comment["id"]}...')
                    for attachment in comment['attachments']:
                        from download_media import download_media_attachment
                        download_media_attachment(directory, attachment, session, profile_cache)

            photo['comments']['list'] = comments

        if with_likes and 'likes' in photo and photo['likes']['count'] > 0:
            print(f'Downloading likes for photo {photo["owner_id"]}_{album_id}')
            photo['likes']['list'] = get_likes(tools, owner_id, 'photo', photo['id'], profile_cache)

    full_json_path.write_text(json.dumps(response, indent=4, ensure_ascii=False))

    print(f'Downloading actual images for album {owner_id}_{album_id}')
    for photo in response:
        download_photo(directory, photo)

    if should_save_profile_cache:
        profile_cache.save()
        profile_cache.download_avatars()

def download_all_albums(directory, owner_id, session: VkOfficialClientSession, with_likes=False):
    directory = Path(directory)
    api = session.api()
    tools = VkTools(api)
    profile_cache = ProfileCache(directory)
    print(f"Downloading all albums for id{owner_id}")
    response = tools.get_all(
        method='photos.getAlbums',
        max_count=1000,
        values={'owner_id': owner_id, 'need_system': 1, 'need_covers': 1},
    )['items']
    album_dir = directory / 'album' / f'album{owner_id}'
    album_dir.mkdir(parents=True, exist_ok=True)
    json_path = album_dir / f'albums{owner_id}.json'
    json_path.write_text(json.dumps(response, indent=4, ensure_ascii=False))
    for album in response:
        if album['id'] == -7:
            continue # Альбом "Фотографии на стене" пропускаем, лучше использовать download_wall.py для этого
        print(f'Downloading photos in album {album['title']}')
        download_photo_album(directory, album['owner_id'], album['id'], session, with_likes, profile_cache)
    profile_cache.save()
    profile_cache.download_avatars()

def main():
    ssl._create_default_https_context = ssl._create_unverified_context
    session = log_in_with_official_client()
    owner_id = input('Owner ID: ').strip()
    album_id = input('Album ID (or skip to download all albums): ').strip()
    with_likes = input('With likes? (type anything, empty string means no) ').strip() != ""
    if album_id:
        download_photo_album('.', owner_id, album_id, session, with_likes)
    else:
        download_all_albums('.', owner_id, session, with_likes)

if __name__ == '__main__':
    main()
