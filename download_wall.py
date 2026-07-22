import json
import ssl
from pathlib import Path
from traceback import print_exc

from vk_api import VkTools, ApiHttpError, VkToolsException

from auth import VkOfficialClientSession
from auth import log_in_with_official_client
from download_media import download_media_attachment
from profile_cache import ProfileCache
from utils import PROFILE_FIELDS
from utils import get_likes
from vktools_with_profiles import VkToolsWithProfiles


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
                    max_count=10,
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
                if 'ads_easy_promote' in post:
                    del post['ads_easy_promote']

            posts_json_path.write_text(json.dumps(response, indent='\t', ensure_ascii=False))
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
                likes_json_path.write_text(json.dumps(response, indent='\t', ensure_ascii=False))
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
                reposts_json_path.write_text(json.dumps(response, indent='\t', ensure_ascii=False))
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
                try:
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
                except Exception:
                    print(f'Could not download comments for post {post["id"]}...')
                    continue
            comments_json_path.write_text(json.dumps(response, indent='\t', ensure_ascii=False))
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
                comments_likes_json_path.write_text(json.dumps(response, indent='\t', ensure_ascii=False))
                profile_cache.save()

        full_json_path.write_text(json.dumps(response, indent='\t', ensure_ascii=False))
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
                download_media_attachment(directory, attachment, session, profile_cache)
        if 'copy_history' in post:
            for repost in post['copy_history']:
                if 'attachments' in repost:
                    for attachment in repost['attachments']:
                        download_media_attachment(directory, attachment, session, profile_cache)

        comments = []
        if 'comments' in post and 'list' in post['comments']:
            comments = post['comments']['list']
        elif 'activity' in post and 'comments' in post['activity']:
            comments = post['activity']['comments']

        for comment in comments:
            if 'attachments' in comment:
                print(f'Downloading attachments for comment {comment["id"]}...')
                for attachment in comment['attachments']:
                    download_media_attachment(directory, attachment, session, profile_cache)

    profile_cache.download_avatars()

def main():
    ssl._create_default_https_context = ssl._create_unverified_context
    session = log_in_with_official_client()
    user_ids = [user_id.strip() for user_id in input('Owner IDs (space-separated): ').split()]
    with_likes = input('With likes and reposts? (type anything, empty string means no) ').strip() != ""
    for user_id in user_ids:
        download_wall('.', user_id, session, with_likes)

if __name__ == '__main__':
    main()
