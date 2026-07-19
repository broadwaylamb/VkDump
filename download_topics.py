import json
import ssl
from pathlib import Path

from vk_api import VkTools

from auth import log_in_with_official_client, VkOfficialClientSession
from download_media import download_media_attachment
from profile_cache import ProfileCache
from vktools_with_profiles import VkToolsWithProfiles


def download_topic(directory, owner_id, topic_id, session: VkOfficialClientSession, profile_cache: ProfileCache = None):
    directory = Path(directory)
    board_dir = directory / 'boards' / f'board{owner_id}'
    board_dir.mkdir(parents=True, exist_ok=True)
    should_save_profile_cache = profile_cache is None
    if profile_cache is not None:
        profile_cache = ProfileCache(directory)
    api = session.api()
    tools = VkToolsWithProfiles(api)
    topic_json = board_dir / f'topic{owner_id}_{topic_id}.json'
    if topic_json.exists():
        print(f'{topic_json} already exists, proceeding to downloading attachments')
        comments = json.load(topic_json.open())
    else:
        print(f'Downloading comments for topic {owner_id}_{topic_id}...')
        comments = tools.get_all(
            method='board.getComments',
            max_count=100,
            values={
                'group_id': owner_id,
                'topic_id': topic_id,
                'extended': 1,
                'sort': 'asc',
            },
            profile_cache=profile_cache,
        )
        profile_cache.save()
        topic_json.write_text(json.dumps(comments, indent='\t', ensure_ascii=False))

    for comment in comments['items']:
        if 'attachments' in comment:
            print(f'Downloading attachments for comment {owner_id}_{topic_id}_{comment["id"]}...')
            for attachment in comment['attachments']:
                download_media_attachment(directory, attachment, session, profile_cache)

    if should_save_profile_cache:
        profile_cache.save()
        profile_cache.download_avatars()


def download_topic_list(directory, owner_id, session: VkOfficialClientSession):
    directory = Path(directory)
    board_dir = directory / 'boards' / f'board{owner_id}'
    board_dir.mkdir(parents=True, exist_ok=True)
    api = session.api()
    topics_json = board_dir / f'topics{owner_id}.json'
    tools = VkTools(api)
    if topics_json.exists():
        print(f'{topics_json} already exists, proceeding to download comments...')
        topics = json.loads(topics_json.read_text())
    else:
        print(f'Downloading the list of topics...')
        topics = tools.get_all(
            method='board.getTopics',
            max_count=100,
            values={
                'group_id': owner_id,
            }
        )['items']
        topics_json.write_text(json.dumps(topics, indent='\t', ensure_ascii=False))
        print('Finished downloading the list of topics.')

    profile_cache = ProfileCache(directory)
    for topic in topics:
        download_topic(directory, owner_id, topic['id'], session, profile_cache)

    profile_cache.save()
    profile_cache.download_avatars()


def main():
    ssl._create_default_https_context = ssl._create_unverified_context
    session = log_in_with_official_client()
    owner_id = input('Group ID: ').strip()
    owner_id = abs(int(owner_id))
    topic_id = input('Topic ID (skip if you want to download all topics of the specified group): ').strip()
    if topic_id:
        download_topic('.', owner_id, id, session)
    else:
        download_topic_list('.', owner_id, session)

if __name__ == '__main__':
    main()
