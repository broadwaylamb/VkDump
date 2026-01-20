import json
from pathlib import Path

from vk_api import VkTools

from auth import VkOfficialClientSession
from auth import log_in_with_official_client
from download_profile import PROFILE_FIELDS

def get_all_comments(owner_id, post_id, session: VkOfficialClientSession, tools: VkTools):
    comments = tools.get_all(
        'wall.getComments',
        max_count=100,
        values={'owner_id': user_id, 'post_id': post['id'], 'need_likes': 1, 'sort': 'asc', 'preview_length': 0}
    )['items']

    return comments

def download_wall(directory, user_id, session: VkOfficialClientSession):
    api = session.api()
    tools = VkTools(api)
    response = tools.get_all('wall.get', 100, {'owner_id': user_id, 'extended': 1, 'fields': PROFILE_FIELDS})['items']
    print(f'Downloading the wall for {user_id}...')

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
            print(f'Downloading comments for post {user_id}_{post["id"]}...')
            all_comments = tools.get_all(
                'wall.getComments',
                max_count=100,
                values={'owner_id': user_id, 'post_id': post['id'], 'need_likes': 1, 'sort': 'asc', 'preview_length': 0, 'extended': 1, 'fields': PROFILE_FIELDS}
            )['items']
            post['activity']['comments'] = all_comments

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f'wall{user_id}.json'
    json_path.write_text(json.dumps(response, indent=4, ensure_ascii=False))


if __name__ == '__main__':
    session = log_in_with_official_client()
    user_id = input('User ID: ').strip()
    download_wall('.', user_id, session)