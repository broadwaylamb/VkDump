import json
import re
import ssl
from pathlib import Path

from auth import log_in_with_official_client
from download_thing import download_thing, download_photo
from utils import PROFILE_FIELDS


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

    def download_avatars(self):
        print('Downloading users\' avatars...')
        for profile in self.profiles:
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

        print('Downloading groups\' avatars...')
        for group in self.groups:
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

def reload_profile(owner_id, profile_cache: ProfileCache, session):
    owner_id = int(owner_id)
    api = session.api()
    if owner_id > 0:
        result = api.method( 'users.get', {'user_ids': owner_id, 'fields': PROFILE_FIELDS })[0]
        for (i, profile) in enumerate(profile_cache.profiles):
            if profile['id'] == owner_id:
                profile_cache.profiles[i] = result
                return
    else:
        result = api.method('groups.getById', {'group_id': -owner_id, 'fields': PROFILE_FIELDS})[0]
        for (i, group) in enumerate(profile_cache.groups):
            if group['id'] == -owner_id:
                profile_cache.groups[i] = result
                return


if __name__ == '__main__':
    ssl._create_default_https_context = ssl._create_unverified_context
    session = log_in_with_official_client()
    profile_cache = ProfileCache(".")
    for wall_f in Path("./wall").iterdir():
        m = re.match("wall(-?\\d+).json", str(wall_f.name))
        if m is not None:
            owner_id = int(m.group(1))
            print(f"Reloading profile {owner_id}...")
            reload_profile(owner_id, profile_cache, session)

    profile_cache.save()