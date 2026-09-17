import json
from pathlib import Path
from traceback import print_exc

from vk_api import VkTools, ApiHttpError, ApiError, VkToolsException

from auth import VkOfficialClientSession
from profile_cache import ProfileCache
from utils import PROFILE_FIELDS


def download_group_members(directory, group_id, friends_only, session: VkOfficialClientSession, profile_cache=None):
    directory = Path(directory)
    profile_cache_passed = profile_cache is not None
    if not profile_cache_passed:
        profile_cache = ProfileCache(directory)
    directory = directory / 'group_members'
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f'members{group_id}.json'
    api = session.api()
    tools = VkTools(api)
    params = {
        'group_id': group_id,
        'fields': PROFILE_FIELDS,
    }
    if friends_only:
        params['filter'] = 'friends'
        print(f'Downloading members of {group_id} (friends only)...')
    else:
        print(f'Downloading members of {group_id}...')

    try:
        response = tools.get_all_slow(
            method='groups.getMembers',
            max_count=1000,
            values=params,
        )['items']
    except ApiHttpError as e:
        print(f'Error getting members for {group_id}: {e.response.json()}')
        print_exc()
        return []
    except ApiError as e:
        print(f'Error getting members for {group_id}: {e.error['error_msg']}')
        return []
    except VkToolsException as e:
        print(f'Error getting members for {group_id}: {e.response.json()}')
        return []

    profile_cache.cache_profiles(response)
    json_path.write_text(json.dumps(response, indent='\t', ensure_ascii=False))

    if not profile_cache_passed:
        profile_cache.save()
        profile_cache.download_avatars()
    return response