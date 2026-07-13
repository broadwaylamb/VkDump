import json
import re
import ssl
from pathlib import Path
from traceback import print_exc

from vk_api import ApiHttpError

from auth import log_in_with_official_client, VkOfficialClientSession
from profile_cache import ProfileCache
from utils import PROFILE_FIELDS
from vktools_with_profiles import VkToolsWithProfiles


def download_friends(directory, user_id, session: VkOfficialClientSession, profile_cache: ProfileCache):
    directory = Path(directory)
    friends_dir = directory / 'friends'
    friends_dir.mkdir(parents=True, exist_ok=True)
    full_json_path = friends_dir / f'friends{owner_id}.json'
    api = session.api()
    tools = VkToolsWithProfiles(api)
    try:
        response = tools.get_all_slow(
            method='friends.get',
            max_count=5000,
            values={
                'user_id': user_id,
                'fields': PROFILE_FIELDS,
            },
            profile_cache=profile_cache,
        )['items']
    except ApiHttpError as e:
        print(f'Error getting friends for {user_id}: {e.response.json()}')
        print_exc()
        return

    full_json_path.write_text(json.dumps(response, indent='\t', ensure_ascii=False))

if __name__ == '__main__':
    ssl._create_default_https_context = ssl._create_unverified_context
    session = log_in_with_official_client()
    profile_cache = ProfileCache(".")
    for wall_f in Path("./wall").iterdir():
        m = re.match("wall(-?\\d+).json", str(wall_f.name))
        if m is not None:
            owner_id = int(m.group(1))
            if owner_id < 0:
                continue
            print(f"Downloading friends of {owner_id}...")
            download_friends(".", owner_id, session, profile_cache)

    profile_cache.save()