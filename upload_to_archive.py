import functools
import getpass
import json
import os.path
from pathlib import Path
import re
import time

import requests

from profile_cache import ProfileCache

VKARCHIVE_HOST = 'localhost:4567'

class VkArchiveSession:
    def __log_in(self) -> str:
        token_txt = Path('vkarchive_token.txt')
        try:
            access_token = token_txt.read_text().strip()
            if access_token:
                return access_token
        except OSError:
            pass

        login = input('Email or username: ').strip()
        password = getpass.getpass('Password: ').strip()
        session = requests.Session()
        res = session.post(
            f'http://{VKARCHIVE_HOST}/oauth/token',
            params=[
                ('grant_type', 'password'),
                ('client_id', f'https://{VKARCHIVE_HOST}/apps/1'),
                ('username', login),
                ('password', password),
            ]
        ).json()
        if 'access_token' not in res:
            raise Exception(json.dumps(res))

        access_token = res['access_token']
        token_txt.write_text(access_token)
        return access_token

    def __init__(self):
        self.token = self.__log_in()
        self.session = requests.Session()
        self.session.headers['Authorization'] = f'Bearer {self.token}'

    def call_api_method(self, name: str, **kwargs):
        res = self.session.post(
            f'http://{VKARCHIVE_HOST}/api/method/{name}',
            params=[('v', '1.0')],
            headers={'Content-Type': 'application/json'},
            json=kwargs,
        ).json()

        if 'error' in res:
            raise Exception(json.dumps(res))

        return res['response']

    def upload_photo(self, path: Path, url):
        res = self.session.post(url, files={'photo': (path.name, open(path, 'rb'), 'image/jpeg')}).json()
        if 'error' in res:
            raise Exception(json.dumps(res))
        return res

    def __getattr__(self, name):
        return functools.partial(self.call_api_method, 'archive.' + name)

def rename_key(dict, old, new):
    if old in dict:
        dict[new] = dict[old]
        del dict[old]

def use_bool(dict, key):
    if key in dict:
        dict[key] = bool(dict[key])

GENDER_MAP = {1: 'female', 2: 'male'}

RELATION_MAP = {1: 'single',
                2: 'in_relationship',
                3: 'engaged',
                4: 'married',
                5: 'complicated',
                6: 'actively_searching',
                7: 'in_love'}

POLITICAL_MAP = {1: 'communist',
                 2: 'socialist',
                 3: 'moderate',
                 4: 'liberal',
                 5: 'conservative',
                 6: 'monarchist',
                 7: 'ultraconservative',
                 8: 'libertarian'}

PEOPLE_MAIN_MAP = {1: 'intellect_creativity',
                   2: 'kindness_honesty',
                   3: 'health_beauty',
                   4: 'wealth_power',
                   5: 'courage_persistence',
                   6: 'humor_life_love'}

LIFE_MAIN_MAP = {1: 'family_children',
                 2: 'career_money',
                 3: 'entertainment_leisure',
                 4: 'science_research',
                 5: 'improving_world',
                 6: 'personal_development',
                 7: 'beauty_art',
                 8: 'fame_influence'}

HABITS_MAP = {1: 'very_negative',
              2: 'negative',
              3: 'tolerant',
              4: 'neutral',
              5: 'positive'}

def prepare_user(session, user):
    try:
        user['archived_at'] = int(os.path.getctime(f'wall/wall{user['id']}.json'))
    except OSError:
        user['archived_at'] = int(time.time())
    if 'sex' in user and user['sex'] in GENDER_MAP:
        user['sex'] = GENDER_MAP[user['sex']]
    else:
        user.pop('sex')
    user.pop('domain', None)
    if 'bdate' in user and re.match('^\\d\\d?\\.\\d\\d?$', user['bdate']) is not None:
        user['bdate'] = user['bdate'] + '.1900'
    if 'city' in user:
        user['city'] = user['city']['title']
        if 'country' in user:
            user['city'] += ', ' + user['country']['title']

    if 'relation' in user and user['relation'] in RELATION_MAP:
        user['relation'] = RELATION_MAP[user['relation']]
    else:
        user.pop('relation', None)

    connections = {'vkontakte': user['screen_name'] if 'screen_name' in user else f'id{user['id']}'}
    def add_connection(name):
        if name in user:
            connections[name] = user[name]
            del user[name]
    add_connection('instagram')
    add_connection('skype')
    add_connection('livejournal')

    if 'contacts' in user:
        if 'home_phone' in user['contacts']:
            connections['phone_number'] = user['contacts']['home_phone']
        if 'mobile_phone' in user['contacts']:
            connections['phone_number'] = user['contacts']['mobile_phone']
        del user['contacts']

    user['connections'] = connections

    if 'personal' in user:
        personal = user['personal']
        if 'political' in personal and personal['political'] in POLITICAL_MAP:
            personal['political'] = POLITICAL_MAP[personal['political']]
        if 'people_main' in personal and personal['people_main'] in PEOPLE_MAIN_MAP:
            personal['people_main'] = PEOPLE_MAIN_MAP[personal['people_main']]
        if 'life_main' in personal and personal['life_main'] in LIFE_MAIN_MAP:
            personal['life_main'] = LIFE_MAIN_MAP[personal['life_main']]
        if 'smoking' in personal and personal['smoking'] in HABITS_MAP:
            personal['smoking'] = HABITS_MAP[personal['smoking']]
        if 'alcohol' in personal and personal['alcohol'] in HABITS_MAP:
            personal['alcohol'] = HABITS_MAP[personal['alcohol']]
    use_bool(user, 'online')
    use_bool(user, 'online_mobile')
    use_bool(user, 'has_photo')

    if 'last_seen' in user:
        ls = user['last_seen']
        if ls['platform'] == 7:
            ls['platform'] = 'desktop'
        else:
            ls['platform'] = 'mobile'

    user.pop('photo_50', None)
    user.pop('photo_100', None)
    user.pop('photo_200', None)
    user.pop('photo_200_orig', None)
    user.pop('photo_400', None)
    user.pop('photo_400_orig', None)
    user.pop('is_favorite', None)
    user.pop('is_hidden_from_feed', None)

    def get_ava_upload_url():
        return session.call_api_method('photos.getOwnerPhotoUploadServer', user_id=user['id'])['upload_url']

    ava_upload_result = None
    if 'photo_id' in user:
        ava_path = Path(f'photo/photo{user['id']}/photo{user['photo_id']}.jpg')
        if ava_path.exists():
            print(f'Uploading avatar for {user['id']} ({user['first_name']} {user['last_name']}) from {ava_path}')
            try:
                ava_upload_result = session.upload_photo(ava_path, get_ava_upload_url())
            except Exception:
                del user['photo_id']
    else:
        ava_path = Path(f'avatar/avatar{user["id"]}.jpg')
        if ava_path.exists():
            print(f'Uploading avatar for {user['id']} ({user['first_name']} {user['last_name']}) from {ava_path}')
            try:
                ava_upload_result = session.upload_photo(ava_path, get_ava_upload_url())
            except Exception:
                pass

    if ava_upload_result is not None:
        user['avatar_file_id'] = ava_upload_result['id']
        user['avatar_hash'] = ava_upload_result['hash']

    def fix_crop_rect(crop):
        crop['x1'] = crop['x'] / 100
        del crop['x']
        crop['y1'] = crop['y'] / 100
        del crop['y']
        crop['x2'] = crop['x2'] / 100
        crop['y2'] = crop['y2'] / 100

    if 'crop_photo' in user:
        crop_photo = user['crop_photo']
        if 'crop' in crop_photo:
            fix_crop_rect(crop_photo['crop'])
        if 'rect' in crop_photo:
            fix_crop_rect(crop_photo['rect'])

    return user


def main():
    session = VkArchiveSession()
    pc = ProfileCache(".")
    res = session.createAccounts(users=[prepare_user(session, profile) for profile in pc.profiles[:1]])
    for error in res:
        print(f'Error uploading user {error['user_id']}: {error["error_description"]}')



if __name__ == '__main__':
    main()