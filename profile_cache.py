import json
from pathlib import Path


class ProfileCache:
    def __init__(self, directory):
        directory = Path(directory)
        self.profiles_path = directory / 'profiles.json'
        self.groups_path = directory / 'groups.json'
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
        for group in groups:
            self.cache_group(group)