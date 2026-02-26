import json
import ssl
from pathlib import Path

from download_media import download_media_attachment
from auth import log_in_with_official_client, VkOfficialClientSession
from download_profile import PROFILE_FIELDS
from download_thing import download_thing
from profile_cache import ProfileCache
from vktools_with_profiles import VkToolsWithProfiles


def get_chat_name(conversation, profile_cache: ProfileCache):
    chat_type = conversation['peer']['type']
    if chat_type == 'chat':
        return conversation['chat_settings']['title']
    elif chat_type == 'group':
        for group in profile_cache.groups:
            if group['id'] == conversation['peer']['local_id']:
                return group['name']
    elif chat_type == 'user':
        for profile in profile_cache.profiles:
            if profile['id'] == conversation['peer']['local_id']:
                return profile['first_name'] + ' ' + profile['last_name']
    return None

def download_chat(directory, conversation, tools: VkToolsWithProfiles, session: VkOfficialClientSession, profile_cache: ProfileCache):
    messages_dir = Path(directory) / 'messages'
    peer_id = conversation['peer']['id']
    messages_dir.mkdir(parents=True, exist_ok=True)
    conversations_json = messages_dir / f'conversation{peer_id}.json'
    chat_name = get_chat_name(conversation, profile_cache) or peer_id
    if conversations_json.exists():
        print(f'{conversations_json} already exists, proceeding to downloading attachments...')
        response = json.load(conversations_json.open())
    else:
        print(f'Downloading messages for {chat_name}...')
        response = tools.get_all(
            method='messages.getHistory',
            max_count=50,
            values={
                'peer_id': peer_id,
                'rev': 1,
                'extended': 1,
                'fields': PROFILE_FIELDS,
            },
            profile_cache=profile_cache,
        )
        print(f'Finished downloading messages for {peer_id}...')
        profile_cache.save()
        conversations_json.write_text(json.dumps(response, indent='\t', ensure_ascii=False))

    print(f'Downloading attachments for {chat_name}...')
    for message in response['items']:
        if 'attachments' in message:
            for attachment in message['attachments']:
                download_media_attachment(directory, attachment, session)

def download_messages(directory, session: VkOfficialClientSession):
    directory = Path(directory)
    messages_dir = directory / 'messages'
    messages_dir.mkdir(parents=True, exist_ok=True)
    api = session.api()
    tools = VkToolsWithProfiles(api)
    profile_cache = ProfileCache(directory)
    conversations_json = messages_dir / 'conversations.json'
    if conversations_json.exists():
        print(f'{conversations_json} already exists, proceeding to download messages...')
        conversations = json.load(conversations_json.open())
    else:
        conversations0_json = messages_dir / 'conversations.0.json'
        if conversations0_json.exists():
            print(f'{conversations0_json} already exists, proceeding to download member lists...')
            conversations = json.load(conversations0_json.open())
        else:
            print('Downloading the list of conversations...')
            items = tools.get_all(
                method='messages.getConversations',
                max_count=200,
            )['items']
            conversations = [item['conversation'] for item in items]
            conversations0_json.write_text(json.dumps(conversations, indent='\t', ensure_ascii=False))
            print('Finished downloading the list of conversations...')

        for conversation in conversations:
            if conversation['peer']['type'] != 'chat':
                continue
            chat_state = conversation['chat_settings']['state']
            if chat_state != 'in':
                continue
            print(f"Downloading conversation members for '{conversation['chat_settings']['title']}'...")
            response = api.method(
                'messages.getConversationMembers',
                {
                    'peer_id': conversation['peer']['id'],
                    'fields': PROFILE_FIELDS
                }
            )
            conversation['members'] = response['items']
            if 'profiles' in response:
                profile_cache.cache_profiles(response['profiles'])
            if 'groups' in response:
                profile_cache.cache_groups(response['groups'])
        profile_cache.save()
        conversations_json.write_text(json.dumps(conversations, indent='\t', ensure_ascii=False))
        conversations0_json.unlink(missing_ok=True)

    print('Downloading chat cover images...')
    for conversation in conversations:
        if conversation['peer']['type'] != 'chat':
            continue
        if 'photo' not in conversation['chat_settings']:
            continue
        photos = conversation['chat_settings']['photo']
        if 'photo_200' in photos:
            url = photos['photo_200']
        elif 'photo_100' in photos:
            url = photos['photo_100']
        elif 'photo_50' in photos:
            url = photos['photo_50']
        else:
            continue
        download_thing(messages_dir, 'cover', conversation['peer']['id'], None, url, 'jpg')

    print('Downloading messages...')
    for conversation in conversations:
        download_chat(directory, conversation, tools, session, profile_cache)

    profile_cache.download_avatars()


def main():
    ssl._create_default_https_context = ssl._create_unverified_context
    session = log_in_with_official_client()
    download_messages('.', session)

if __name__ == '__main__':
    main()