# From https://github.com/JustChasti/m3u8-to-mp3-converter

import binascii
from pathlib import PurePath, Path
import time

import m3u8
from moviepy import AudioFileClip
from Crypto.Cipher import AES
from urllib.request import urlopen
import ssl

def __get_key(data):
    for i in range(data.media_sequence + 1):
        try:
            key_uri = data.keys[i].uri
            host_uri = "/".join(key_uri.split("/")[:-1])
            return host_uri
        except Exception as e:
            continue


def __read_keys(path):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    data_response = urlopen(path, context=ctx)
    content = data_response.read()

    return content


def __get_ts(url, sleep_ms) -> bytes:
    data = m3u8.load(url, verify_ssl=False)
    key_link = __get_key(data)
    ts_content = b""
    key = None

    for i, segment in enumerate(data.segments):
        decrypt_func = lambda x: x
        if segment.key.method == "AES-128":
            if not key:
                key_uri = segment.key.uri
                key = __read_keys(key_uri)
            ind = i + data.media_sequence
            iv = binascii.a2b_hex('%032x' % ind)
            cipher = AES.new(key, AES.MODE_CBC, iv=iv)
            decrypt_func = cipher.decrypt

        ts_url = f'{key_link}/{segment.uri}'

        time.sleep(sleep_ms / 1000)
        coded_data = __read_keys(ts_url)
        ts_content += decrypt_func(coded_data)
    return ts_content


def m3u8_to_mp3_converter(mp3_path, url, sleep_ms) -> None:
    ts_content = __get_ts(url, sleep_ms)
    mp3_path = Path(mp3_path)
    if ts_content is None:
        raise TypeError("Empty mp3 content to save.")
    with open(mp3_path, 'wb') as out:
        out.write(ts_content)


def m3u8_to_mp3_advanced(mp3_local_path, m3u8_url, sleep_ms) -> None:
    ts_content = __get_ts(m3u8_url, sleep_ms)
    mp3_local_path = Path(mp3_local_path)
    if ts_content is None:
        raise TypeError("Empty mp3 content to save.")
    
    mp3_path_x = mp3_local_path.with_suffix('.part')
    with open(mp3_path_x, 'wb') as out:
        out.write(ts_content)

    audioclip = AudioFileClip(mp3_path_x)
    try:
        audioclip.write_audiofile(mp3_local_path)
    finally:
        audioclip.close()
        mp3_path_x.unlink()


