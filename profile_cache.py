import json
import ssl
from pathlib import Path

from vk_api import VkApiError
from vk_api.execute import VkFunction

from auth import log_in_with_official_client
from download_thing import download_thing, download_photo
from utils import PROFILE_FIELDS, chunks

_vk_load_users = VkFunction(
    args=('user_ids', 'fields'),
    clean_args=('fields',),
    code='''
    var result = [], i = 0, user_ids = %(user_ids)s, fields = "%(fields)s";
    while(i < user_ids.length) {
        result = result + API.users.get({"user_ids": user_ids[i], "fields": fields});
        i = i + 1;
    };

    return result;
''')

_vk_load_groups = VkFunction(
    return_raw=True,
    args=('group_ids', 'fields'),
    clean_args=('fields',),
    code='''
    var result = [], i = 0, group_ids = %(group_ids)s, fields = "%(fields)s";
    while(i < group_ids.length) {
        result = result + API.groups.getById({"group_ids": group_ids[i], "fields": fields});
        i = i + 1;
    };

    return result;
''')


def _distinct(profiles, seen):
    result = []
    for profile in profiles:
        if profile['id'] not in seen:
            seen.add(profile['id'])
            result.append(profile)
    return result

class ProfileCache:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.profiles_path = self.directory / 'profiles.json'
        self.groups_path = self.directory / 'groups.json'
        self.profiles = []
        self.groups = []
        self.seen_profiles = set()
        self.seen_groups = set()
        if self.profiles_path.exists():
            with self.profiles_path.open() as f:
                self.profiles = json.load(f)
        if self.groups_path.exists():
            with self.groups_path.open() as f:
                self.groups = json.load(f)
        self.profiles = _distinct(self.profiles, self.seen_profiles)
        self.groups = _distinct(self.groups, self.seen_groups)
        self.__profile_avatars_downloaded = len(self.profiles)
        self.__group_avatars_downloaded = len(self.groups)

    def save(self):
        self.profiles_path.write_text(json.dumps(self.profiles, indent='\t', ensure_ascii=False))
        self.groups_path.write_text(json.dumps(self.groups, indent='\t', ensure_ascii=False))

    def cache_profile(self, profile):
        if profile['id'] not in self.seen_profiles:
            self.seen_profiles.add(profile['id'])
            self.profiles.append(profile)

    def cache_profiles(self, profiles):
        for profile in profiles:
            self.cache_profile(profile)

    def cache_group(self, group):
        if group['id'] not in self.seen_groups:
            self.seen_groups.add(group['id'])
            self.groups.append(group)

    def cache_groups(self, groups):
        if isinstance(groups, str):
            return
        for group in groups:
            self.cache_group(group)

    @staticmethod
    def __reload(name, chunk_size, actors, execute):
        reloaded = []
        for actor in chunks(actors, chunk_size):
            print(f'Loading {name} {len(reloaded) + 1}-{len(reloaded) + len(actor)} out of {len(actors)}...')
            ids = [a['id'] for a in actor]
            response = execute(ids)
            if 'execute_errors' in response:
                raise VkApiError(response['execute_errors'])
            reloaded += response['response']
        return reloaded

    def reload_profiles(self, api):
        self.profiles = ProfileCache.__reload('profiles', 25, self.profiles, lambda ids: _vk_load_users(api, ids, PROFILE_FIELDS))
        self.__profile_avatars_downloaded = 0

    def reload_groups(self, api):
        self.groups = ProfileCache.__reload('groups', 5, self.groups, lambda ids: _vk_load_groups(api, ids, PROFILE_FIELDS))
        self.__group_avatars_downloaded = 0

    def download_avatars(self):
        print(f'Downloading avatars for {len(self.profiles) - self.__profile_avatars_downloaded} new profiles...')
        for profile in self.profiles[self.__profile_avatars_downloaded:]:
            if 'crop_photo' in profile and 'photo' in profile['crop_photo']:
                download_photo(self.directory, profile['crop_photo']['photo'])
                continue

            if 'deactivated' in profile or ('has_photo' in profile and not profile['has_photo']):
                continue

            if 'photo_max_orig' in profile:
                url = profile['photo_max_orig']
                if 'photo_id' not in profile:
                    download_thing(self.directory, 'avatar', profile['id'], None, url, 'jpg')
                else:
                    (photo_owner_id, photo_id) = profile['photo_id'].split('_')
                    download_thing(self.directory, 'photo', photo_owner_id, photo_id, url, 'jpg')
        self.__profile_avatars_downloaded = len(self.profiles)

        print(f'Downloading avatars for {len(self.groups) - self.__group_avatars_downloaded} new groups...')
        for group in self.groups[self.__group_avatars_downloaded:]:
            if 'crop_photo' in group and 'photo' in group['crop_photo']:
                download_photo(self.directory, group['crop_photo']['photo'])
                continue

            if 'deactivated' in group or ('has_photo' in group and not group['has_photo']):
                continue

            if 'photo_200' in group:
                url = group['photo_200']
            elif 'photo_100' in group:
                url = group['photo_100']
            elif 'photo_50' in group:
                url = group['photo_50']
            else:
                continue
            if 'photo_id' not in group:
                download_thing(self.directory, 'avatar', -group['id'], None, url, 'jpg')
            else:
                download_thing(self.directory, 'photo', -group['id'], group['photo_id'], url, 'jpg')
        self.__group_avatars_downloaded = len(self.groups)

def main():
    ssl._create_default_https_context = ssl._create_unverified_context
    api = log_in_with_official_client().api()
    profile_cache = ProfileCache(".")
    profile_cache.reload_groups(api)
    profile_cache.reload_profiles(api)
    profile_cache.download_avatars()
    profile_cache.save()

if __name__ == '__main__':
    main()
