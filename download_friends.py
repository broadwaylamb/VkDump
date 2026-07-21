import json
import ssl
from pathlib import Path
from traceback import print_exc

from vk_api import ApiHttpError, VkTools

from auth import log_in_with_official_client, VkOfficialClientSession
from profile_cache import ProfileCache
from utils import PROFILE_FIELDS


def download_friends(directory, user_id, session: VkOfficialClientSession, profile_cache: ProfileCache):
    directory = Path(directory)
    friends_dir = directory / 'friends'
    friends_dir.mkdir(parents=True, exist_ok=True)
    full_json_path = friends_dir / f'friends{user_id}.json'
    api = session.api()
    tools = VkTools(api)
    try:
        response = tools.get_all_slow(
            method='friends.get',
            max_count=1000,
            values={
                'user_id': user_id,
                'fields': PROFILE_FIELDS,
            },
        )['items']
    except ApiHttpError as e:
        print(f'Error getting friends for {user_id}: {e.response.json()}')
        print_exc()
        return []

    profile_cache.cache_profiles(response)
    full_json_path.write_text(json.dumps(response, indent='\t', ensure_ascii=False))
    return response

def main():
    ssl._create_default_https_context = ssl._create_unverified_context
    session = log_in_with_official_client()
    profile_cache = ProfileCache(".")
    uid = input('User ID whose friends to dump: ').strip()
    fof = input('Also friends of friends? (type anything, empty string means no) ').strip() != ''

    print(f'Downloading friends of {uid}...')
    friends = download_friends('.', uid, session, profile_cache)
    if fof:
        for friend in friends:
            print(f'Downloading friends of {friend['id']}...')
            download_friends('.', friend['id'], session, profile_cache)
    profile_cache.save()
    profile_cache.download_avatars()


if __name__ == '__main__':
    main()
