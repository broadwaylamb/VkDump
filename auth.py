import getpass
import pathlib

import requests
import vk_api
from vkaudiotoken import CommonParams, TokenReceiverOfficial, supported_clients, TokenException, TwoFAHelper


class VkOfficialClientSession:
    def __init__(self, access_token):
        self.session = requests.session()
        self.session.headers.update({'User-Agent': supported_clients.VK_OFFICIAL.user_agent})
        self.access_token = access_token

    def api(self):
        return vk_api.VkApi(
            token=self.access_token,
            session=self.session,
            api_version='5.95',
            app_id=supported_clients.VK_OFFICIAL.client_id,
        )


def log_in_with_official_client() -> VkOfficialClientSession:
    token_txt = pathlib.Path('official_client_token.txt')
    try:
        access_token = token_txt.read_text().strip()
        if access_token:
            return VkOfficialClientSession(access_token)
    except OSError:
        pass

    login = input('Email or phone number: ')
    password = getpass.getpass('Password: ')

    access_token = None
    while True:
        auth_code = input('2FA code:')

        # TwoFAHelper also works with TokenReceiver class and Kate User-Agent. See example_microg.py
        params = CommonParams(supported_clients.VK_OFFICIAL.user_agent)
        receiver = TokenReceiverOfficial(login, password, params, auth_code)
        try:
            access_token = receiver.get_token()['access_token']
            break
        except TokenException as err:
            if err.code == TokenException.TWOFA_REQ and 'validation_sid' in err.extra:
                TwoFAHelper(params).validate_phone(err.extra['validation_sid'])
                print('SMS should be sent')
                continue
            elif err.code == TokenException.TOKEN_NOT_RECEIVED and err.extra['error_type'] == 'wrong_otp':
                print('Wrong 2FA code')
                continue
            else:
                raise

    token_txt.write_text(access_token)
    return VkOfficialClientSession(access_token)

if __name__ == '__main__':
    log_in_with_official_client()