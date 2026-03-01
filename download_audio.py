import json
from pathlib import PurePath, Path
from traceback import print_exc

from mutagen.easyid3 import EasyID3
from vk_api import VkTools, tools, VkToolsException

from auth import log_in_with_official_client, VkOfficialClientSession
import m3u8_converter

def download_mp3_from_m3u8(directory, owner_id, audio_id, m3u8_url, artist, title):
    mp3_path = PurePath(directory) / f'audio{owner_id}_{audio_id}.mp3'
    print(f'Downloading \'{artist} - {title}\' to {mp3_path}')
    if not m3u8_url:
        print('Audio url is empty, skipping')
        return
    m3u8_converter.m3u8_to_mp3_advanced(mp3_path, m3u8_url, sleep_ms=1000)

    # Set the mp3 metadata
    audio = EasyID3(mp3_path)
    audio['artist'] = artist
    audio['title'] = title
    audio.save()

def download_audio(directory, audio):
    directory = Path(directory) / 'audio' / f'audio{audio["owner_id"]}'
    directory.mkdir(parents=True, exist_ok=True)
    if (directory / f'audio{audio['owner_id']}_{audio['id']}.mp3').exists():
        print('Already downloaded, skipping')
        return
    try:
        download_mp3_from_m3u8(directory, audio['owner_id'], audio['id'], audio['url'], audio['artist'], audio['title'])
    except:
        print(f'Could not download audio "{audio['artist']} - {audio['title']}"')
        print_exc()

def download_mp3(directory, audio_owner, audio_id, session: VkOfficialClientSession):
    """
    Скачивает аудиозапись в указанную директорию с именем audio<audio_owner>_<audio_id>.mp3.

    Лучше скачивать используя российский IP, иначе многие треки будут недоступны.

    :param directory: Куда сохранить mp3-файл
    :param audio_owner: Идентификатор пользователя, загрузившего аудиозапись (первое число в ссылке на аудиозапись после слова audio)
    :param audio_id: Идентификатор аудиозаписи (второе число в ссылке на аудиозапись после слова audio)
    :return:
    """
    response = session.api().method('audio.getById', {'audios': f'{audio_owner}_{audio_id}'})
    url = response[0]['url']
    artist = response[0]['artist']
    title = response[0]['title']

    download_mp3_from_m3u8(directory, audio_owner, audio_id, url, artist, title)

class PatchedVkTools(VkTools):
    def get_all_iter(self, method, max_count, values=None, key='items',
                     limit=None, stop_fn=None, negative_offset=False):
        values = values.copy() if values else {}
        values['count'] = max_count

        offset = max_count if negative_offset else 0
        items_count = 0
        count = None

        while True:
            response = tools.vk_get_all_items(
                self.vk, method, key, values, count, offset,
                offset_mul=-1 if negative_offset else 1
            )

            if 'execute_errors' in response:
                raise VkToolsException(
                    'Could not load items: {}'.format(
                        response['execute_errors']
                    ),
                    response=response
                )

            response = response['response']

            items = response["items"]
            items_count += len(items)

            for item in items:
                yield item

            # if not response['more']:
            #     break

            if limit and items_count >= limit:
                break

            if stop_fn and stop_fn(items):
                break

            count = response['count']
            offset = response['offset']

def download_audio_list(directory, owner_id, session: VkOfficialClientSession):
    api = session.api()
    t = PatchedVkTools(api)
    print('Downloading audio list...')
    response = t.get_all('audio.get', max_count=100, values={'owner_id': owner_id}, stop_fn=lambda items: len(items) == 0)['items']

    # Удаляем ненужные поля
    for audio in response:
        del audio['ads']
        del audio['track_code']

    directory = Path(directory)
    audio_dir = directory / 'audio' / f'audio{owner_id}'
    audio_dir.mkdir(parents=True, exist_ok=True)
    json_path = audio_dir / f'audio{owner_id}.json'
    json_path.write_text(json.dumps(response, indent='\t', ensure_ascii=False))
    print('Saved audio list to {}'.format(json_path))
    print(f'Downloading mp3s into directory {audio_dir}')
    for i, audio in enumerate(response):
        print(f'Downloading {i + 1} out of {len(response)}...')
        download_audio(directory, audio)

def main():
    session = log_in_with_official_client()
    owner = input('Owner ID: ').strip()
    id = input('Audio ID (skip if you want to download all audios of the specified owner): ').strip()
    if id:
        download_mp3('.', owner, id, session)
    else:
        download_audio_list('.', owner, session)

if __name__ == '__main__':
    main()