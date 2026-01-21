import json
import ssl
from pathlib import Path
from traceback import print_exc

from vk_api import VkTools, ApiHttpError

from auth import VkOfficialClientSession
from auth import log_in_with_official_client
from download_media import download_media_attachment
from download_profile import PROFILE_FIELDS


def get_all_comments(owner_id, post_id, session: VkOfficialClientSession, tools: VkTools):
    comments = tools.get_all(
        'wall.getComments',
        max_count=100,
        values={'owner_id': user_id, 'post_id': post['id'], 'need_likes': 1, 'sort': 'asc', 'preview_length': 0}
    )['items']

    return comments

def download_wall(directory, owner_id, session: VkOfficialClientSession):
    directory = Path(directory)
    wall_dir = Path(directory) / 'wall'
    wall_dir.mkdir(parents=True, exist_ok=True)
    json_path = wall_dir / f'wall{owner_id}.json'
    api = session.api()
    tools = VkTools(api)
    print(f'Downloading wall for {owner_id}...')

    if json_path.exists():
        print(f'{json_path} already exists, proceeding to download attachments...')
        response = json.load(json_path.open())
    else:
        try:
            response = tools.get_all('wall.get', 50, {'owner_id': owner_id, 'extended': 1, 'copy_history_depth': 10, 'fields': PROFILE_FIELDS})['items']
        except ApiHttpError as e:
            print(f'Error getting wall for {owner_id}: {e.response.json()}')
            print_exc()
            return
        print(f'Downloaded posts for {owner_id}. Downloading comments...')

        for post in response:
            has_comments = 'comments' in post and 'count' in post['comments'] and post['comments']['count'] > 0
            if not has_comments:
                continue

            returned_comments = []
            if 'list' in post['comments']:
                returned_comments = post['comments']['list']
            elif 'activity' in post and 'comments' in post['activity']:
                returned_comments = post['activity']['comments']

            if len(returned_comments) < post['comments']['count']:
                print(f'Downloading comments for post {owner_id}_{post["id"]}...')
                all_comments = tools.get_all(
                    'wall.getComments',
                    max_count=100,
                    values={'owner_id': owner_id, 'post_id': post['id'], 'need_likes': 1, 'sort': 'asc', 'preview_length': 0, 'extended': 1, 'fields': PROFILE_FIELDS}
                )['items']
                if 'list' in post['comments']:
                    post['comments']['list'] = all_comments
                elif 'activity' in post:
                    post['activity']['comments'] = all_comments

    json_path.write_text(json.dumps(response, indent=4, ensure_ascii=False))
    print(f'Wall downloaded to {json_path}. Downloading attachments...')
    for post in response:
        if 'attachments' in post:
            print(f'Downloading attachments for post {post["id"]}...')
            for attachment in post['attachments']:
                download_media_attachment(directory, attachment, session)
        if 'copy_history' in post:
            for repost in post['copy_history']:
                if 'attachments' in repost:
                    for attachment in repost['attachments']:
                        download_media_attachment(directory, attachment, session)

if __name__ == '__main__':
    ssl._create_default_https_context = ssl._create_unverified_context
    session = log_in_with_official_client()
    user_id = input('User ID: ').strip()
    download_wall('.', user_id, session)