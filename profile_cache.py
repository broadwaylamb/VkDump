import json
from pathlib import Path

from download_thing import download_thing, download_photo


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