import json
from pathlib import Path

import vk_api
from vkaudiotoken.supported_clients import VK_OFFICIAL

import auth
from auth import VkOfficialClientSession

PROFILE_FIELDS = ('about,'
                  'activities,'
                  'bdate,'
                  'blacklisted,'
                  'blacklisted_by_me,'
                  'books,'
                  'career,'
                  'city,'
                  'common_count,'
                  'connections,'
                  'contacts,'
                  'counters,'
                  'country,'
                  'crop_photo,'
                  'domain,'
                  'education,'
                  'exports,'
                  'followers_count,'
                  'games,'
                  'has_mobile,'
                  'has_photo,'
                  'home_town,'
                  'interests,'
                  'is_favorite,'
                  'is_hidden_from_feed,'
                  'is_no_index,'
                  'last_seen,'
                  'maiden_name,'
                  'military,'
                  'movies,'
                  'music,'
                  'nickname,'
                  'occupation,'
                  'personal,'
                  'photo_id',
                  'photo_400_orig,'
                  'photo_max_orig,'
                  'quotes,'
                  'relatives,'
                  'relation,'
                  'schools,'
                  'screen_name,'
                  'sex,'
                  'site,'
                  'status,'
                  'tv,'
                  'universities,'
                  'verified,'
                  'wall_default')

def download_profile(directory, user_id, session: VkOfficialClientSession):
    """
    Сохраняет информацию о профиле пользователя в указанную директорию в файл с именем user<user_id>.json.
    :param directory: Куда сохранить JSON-файл.
    :param user_id: Идентификатор пользователя.
    """

    api = vk_api.VkApi(
        token=session.access_token,
        session=session.session,
        api_version='5.95',
        app_id=VK_OFFICIAL.client_id,
    )
    result = api.method(
        'users.get',
        {
            'user_ids': user_id,
            'fields': PROFILE_FIELDS
        }
    )
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f'user{user_id}.json'
    json_path.write_text(json.dumps(result[0], indent=4, ensure_ascii=False))


if __name__ == '__main__':
    session = auth.log_in_with_official_client()
    user_id = input('User ID: ').strip()
    download_profile('.', user_id, session)