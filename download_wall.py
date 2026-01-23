import json
import ssl
from pathlib import Path
from traceback import print_exc

from vk_api import VkTools, ApiHttpError, VkToolsException

from auth import VkOfficialClientSession
from auth import log_in_with_official_client
from download_media import download_media_attachment
from download_photo import download_photo
from download_profile import PROFILE_FIELDS
from download_thing import download_thing
from profile_cache import ProfileCache
from vktools_with_profiles import VkToolsWithProfiles


def get_likes(tools: VkTools, owner_id, item_type, item_id, profile_cache: ProfileCache):
    likers = tools.get_all(
        method='likes.getList',
        max_count=100,
        values={
            'type': item_type,
            'owner_id': owner_id,
            'item_id': item_id,
            'extended': 1,
            'fields': PROFILE_FIELDS,
        },
    )

    liked_ids = []
    for liker in likers['items']:
        if liker['type'] == 'profile':
            del liker['type']
            liked_ids.append(liker['id'])
            profile_cache.cache_profile(liker)
        elif liker['type'] == 'group':
            del liker['type']
            liked_ids.append(-abs(liker['id']))
            liker['id'] = abs(liker['id'])
            profile_cache.cache_group(liker)
        else:
            continue

    return liked_ids

def get_reposts(tools: VkTools, owner_id, post_id, profile_cache: ProfileCache):
    reposts = tools.get_all(
        method='wall.getReposts',
        max_count=100,
        values={
            'owner_id': owner_id,
            'post_id': post_id,
            'fields': PROFILE_FIELDS,
        },
    )

    profile_cache.cache_profiles(reposts['profiles'])
    profile_cache.cache_groups(reposts['groups'])

    return reposts['items']

def download_wall(directory, owner_id, session: VkOfficialClientSession, with_likes = False):
    directory = Path(directory)
    wall_dir = directory / 'wall'
    wall_dir.mkdir(parents=True, exist_ok=True)
    posts_json_path = wall_dir / f'wall{owner_id}.posts.json'
    likes_json_path = wall_dir / f'wall{owner_id}.likes.json'
    reposts_json_path = wall_dir / f'wall{owner_id}.reposts.json'
    comments_json_path = wall_dir / f'wall{owner_id}.comments.json'
    comments_likes_json_path = wall_dir / f'wall{owner_id}.comments.likes.json'
    full_json_path = wall_dir / f'wall{owner_id}.json'
    api = session.api()
    tools = VkToolsWithProfiles(api)
    print(f'Downloading wall for {owner_id}...')

    profile_cache = ProfileCache(directory)

    if full_json_path.exists():
        print(f'{full_json_path} already exists, proceeding to download attachments...')
        response = json.load(full_json_path.open())
    else:
        if posts_json_path.exists():
            response = json.load(posts_json_path.open())
            print(f'{posts_json_path} already exists, proceeding to download {'likes' if with_likes else 'comments'}...')
        else:
            try:
                response = tools.get_all(
                    method='wall.get',
                    max_count=30,
                    values={
                        'owner_id': owner_id,
                        'extended': 1,
                        'copy_history_depth': 10,
                        'fields': PROFILE_FIELDS,
                    },
                    profile_cache=profile_cache,
                )
            except ApiHttpError as e:
                print(f'Error getting wall for {owner_id}: {e.response.json()}')
                print_exc()
                return

            for post in response['items']:
                if 'can_delete' in post:
                    del post['can_delete']
                if 'can_pin' in post:
                    del post['can_pin']
                if 'can_archive' in post:
                    del post['can_archive']
                if 'track_code' in post:
                    del post['track_code']
                if 'views' in post:
                    del post['views']
                if 'marked_as_ads' in post and post['marked_as_ads'] == 0:
                    del post['marked_as_ads']
                if 'hash' in post:
                    del post['hash']

            posts_json_path.write_text(json.dumps(response, indent=4, ensure_ascii=False))
            profile_cache.save()
            print(f'Downloaded posts for {owner_id}.')

        if with_likes:
            if likes_json_path.exists():
                response = json.load(likes_json_path.open())
                print(f'{likes_json_path} already exists, proceeding to download reposts...')
            else:
                print('Downloading likes for posts...')
                for post in response['items']:
                    if 'likes' not in post or 'count' not in post['likes'] or post['likes']['count'] == 0:
                        continue
                    print(f'Downloading likes for post {post['id']}...')
                    post['likes']['list'] = get_likes(tools, owner_id, 'post', post['id'], profile_cache)
                print('Downloaded likes.')
                likes_json_path.write_text(json.dumps(response, indent=4, ensure_ascii=False))
                profile_cache.save()

            if reposts_json_path.exists():
                response = json.load(reposts_json_path.open())
                print(f'{reposts_json_path} already exists, proceeding to download comments...')
            else:
                print('Downloading reposts...')
                for post in response['items']:
                    if 'reposts' not in post or 'count' not in post['reposts'] or post['reposts']['count'] == 0:
                        continue
                    print(f'Downloading reposts for post {post['id']}...')
                    try:
                        post['reposts']['list'] = get_reposts(tools, owner_id, post['id'], profile_cache)
                    except VkToolsException:
                        print(f'Could not download reposts for post {post['id']}')
                reposts_json_path.write_text(json.dumps(response, indent=4, ensure_ascii=False))
                profile_cache.save()

        if comments_json_path.exists():
            response = json.load(comments_json_path.open())
            print(f'{comments_json_path} already exists, proceeding to download likes for comments...')
        else:
            print('Downloading comments...')
            for post in response['items']:
                has_comments = 'comments' in post and 'count' in post['comments'] and post['comments']['count'] > 0
                if not has_comments:
                    continue

                print(f'Downloading comments for post {owner_id}_{post["id"]}...')
                post['comments']['list'] = tools.get_all(
                    method='wall.getComments',
                    max_count=100,
                    values={
                        'owner_id': owner_id,
                        'post_id': post['id'],
                        'need_likes': 1,
                        'sort': 'asc',
                        'preview_length': 0,
                        'extended': 1,
                        'fields': PROFILE_FIELDS,
                    },
                    profile_cache=profile_cache,
                )['items']
            comments_json_path.write_text(json.dumps(response, indent=4, ensure_ascii=False))
            profile_cache.save()

        if with_likes:
            if comments_likes_json_path.exists():
                response = json.load(comments_likes_json_path.open())
                print(f'{comments_likes_json_path} already exists, proceeding to download attachments...')
            else:
                for post in response['items']:
                    if 'comments' not in post or 'list' not in post['comments'] or len(post['comments']['list']) == 0:
                        continue
                    all_comments = post['comments']['list']
                    for comment in all_comments:
                        if 'likes' not in comment or 'count' not in comment['likes'] or comment['likes']['count'] == 0:
                            continue
                        print(f'Downloading likes for comment {comment['id']}...')
                        comment['likes']['list'] = get_likes(tools, owner_id, 'comment', comment['id'], profile_cache)
                comments_likes_json_path.write_text(json.dumps(response, indent=4, ensure_ascii=False))
                profile_cache.save()

        full_json_path.write_text(json.dumps(response, indent=4, ensure_ascii=False))
        comments_likes_json_path.unlink(missing_ok=True)
        comments_json_path.unlink(missing_ok=True)
        reposts_json_path.unlink(missing_ok=True)
        likes_json_path.unlink(missing_ok=True)
        posts_json_path.unlink(missing_ok=True)
        print(f'Wall downloaded to {full_json_path}. Downloading attachments...')

    for post in response['items']:
        if 'attachments' in post:
            print(f'Downloading attachments for post {post["id"]}...')
            for attachment in post['attachments']:
                download_media_attachment(directory, attachment, session)
        if 'copy_history' in post:
            for repost in post['copy_history']:
                if 'attachments' in repost:
                    for attachment in repost['attachments']:
                        download_media_attachment(directory, attachment, session)

        comments = []
        if 'list' in post['comments']:
            comments = post['comments']['list']
        elif 'activity' in post and 'comments' in post['activity']:
            comments = post['activity']['comments']

        for comment in comments:
            if 'attachments' in comment:
                print(f'Downloading attachments for comment {comment["id"]}...')
                for attachment in comment['attachments']:
                    download_media_attachment(directory, attachment, session)

    print('Downloading users\' avatars...' )
    for profile in response['profiles']:
        if 'crop_photo' in profile and 'photo' in profile['crop_photo']:
            download_photo(directory, profile['crop_photo']['photo'])
            continue

        if 'deactivated' in profile or not profile['has_photo']:
            continue

        if 'photo_max_orig' in profile:
            url = profile['photo_max_orig']
            if 'photo_id' not in profile:
                download_thing(directory, 'avatar', profile['id'], None, url, 'jpg')
            else:
                (photo_owner_id, photo_id) = profile['photo_id'].split('_')
                download_thing(directory, 'photo', photo_owner_id, photo_id, url, 'jpg')


    print('Downloading groups\' avatars...' )
    for group in response['groups']:
        if 'crop_photo' in group and 'photo' in group['crop_photo']:
            download_photo(directory, group['crop_photo']['photo'])
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
            download_thing(directory, 'avatar', -group['id'], None, url, 'jpg')
        else:
            download_thing(directory, 'photo', -group['id'], group['photo_id'], url, 'jpg')

def main():
    ssl._create_default_https_context = ssl._create_unverified_context
    session = log_in_with_official_client()
    user_id = input('User ID: ').strip()
    with_likes = input('With likes and reposts? (type anything, empty string means no) ').strip() != ""
    download_wall('.', user_id, session, with_likes)

if __name__ == '__main__':
    main()