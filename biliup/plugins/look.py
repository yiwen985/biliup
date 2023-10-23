import json
import re

import requests

from ..engine.decorators import Plugin
from . import logger
from ..engine.download import DownloadBase

import base64
import binascii
# import json
import random

# import requests
from Crypto.Cipher import AES

modulus = '00e0b509f6259df8642dbc35662901477df22677ec152b5ff68ace615bb7b725152b3ab17a876aea8a5aa76d2e417629ec4ee34' \
          '1f56135fccf695280104e0312ecbda92557c93870114af6c9d05c4f7f0c3685b7a46bee255932575cce10b424d813cfe4875d3e' \
          '82047b97ddef52741d546b8e289dc6935b3ece0462db0a22b8e7'
nonce = b'0CoJUm6Qyw8W8jud'
pubKey = '010001'

# !!!仅支持听听
# 格式
# 手机分享
#   https://h5.look.163.com/live?liveId=68995949&id=532194959&pageType=1&ud=5AB50D7A1045FC0144209F1CDFB570AA
# PC
#   https://look.163.com/live?id=388415721
@Plugin.download(regexp=r'(?:https?://)?h5\.look\.163\.com')
@Plugin.download(regexp=r'(?:https?://)?look\.163\.com')
class Look(DownloadBase):
    def __init__(self, fname, url, suffix='mp4'):
        super().__init__(fname, url, suffix)
        self.liveStreamType = -1
    
    def check_stream(self, is_check=False):
        rid = re.search(r'id=(\d*)', self.url).group(1)
        try:
            # {'httpPullUrl': 'http://pull0583d674.live.126.net/live/90b7b4b5f46f43c4aebd21eb74ea1a00.flv?netease=pull0583d674.live.126.net', 
            # 'hlsPullUrl': 'http://pull0583d674.live.126.net/live/90b7b4b5f46f43c4aebd21eb74ea1a00/playlist.m3u8', 
            # 'rtmpPullUrl': 'rtmp://pull0583d674.live.126.net/live/90b7b4b5f46f43c4aebd21eb74ea1a00'}
            
            # self.raw_stream_url = self.get_real_url(rid)['hlsPullUrl']
            # self.raw_stream_url = self.get_real_url(rid)['httpPullUrl']
            # self.raw_stream_url = self.get_real_url(rid)['rtmpPullUrl']
            three_urls = self.get_real_url(rid)
            # 轮播状态，退出
            if self.liveStreamType == 10:
                return False
            if requests.get(three_urls['httpPullUrl'], stream=True).status_code != 404:
                self.raw_stream_url = three_urls['httpPullUrl']
                return True
            elif requests.get(three_urls['hlsPullUrl'], stream=True).status_code != 404:
                self.raw_stream_url = three_urls['hlsPullUrl']
                return True
            else:
                return False
        except Exception as e:
            print('Exception：', e)
            return False
    
    def get_real_url(self, rid):
        try:
            request_data = encrypted_request({"liveRoomNo": rid})
            response = requests.post(url='https://api.look.163.com/weapi/livestream/room/get/v3', data=request_data)
            real_url = response.json()['data']['roomInfo']['liveUrl']
            self.liveStreamType = response.json()['data']['roomInfo']['liveStreamType']
            # if liveStreamType == 10:
            #     raise Exception("当前为录播")
        except Exception:
            raise Exception('直播间不存在或未开播')
        self.room_title = response.json()['data']['roomInfo']['title']
        return real_url
    
        

def aes_encrypt(text, seckey):
    pad = 16 - len(text) % 16

    # aes加密需要byte类型。
    # 因为调用两次，下面还要进行补充位数。
    # 直接用try与if差不多。

    try:
        text = text.decode()
    except Exception as e:
        print(e)

    text = text + pad * chr(pad)
    try:
        text = text.encode()
    except Exception as e:
        print(e)

    encryptor = AES.new(seckey, 2, bytes('0102030405060708', 'utf-8'))
    ciphertext = encryptor.encrypt(text)
    ciphertext = base64.b64encode(ciphertext)
    return ciphertext


def create_secret_key(size):
    # 2中 os.urandom返回是个字符串。3中变成bytes。
    # 不过加密的目的是需要一个字符串。
    # 因为密钥之后会被加密到rsa中一起发送出去。
    # 所以即使是个固定的密钥也是可以的。

    # return (''.join(map(lambda xx: (hex(ord(xx))[2:]), os.urandom(size))))[0:16]
    return bytes(''.join(random.sample('1234567890qwertyuipasdfghjklzxcvbnm', size)), 'utf-8')


def rsa_encrypt(text, pub_key, mod):
    text = text[::-1]
    # 3中将字符串转成hex的函数变成了binascii.hexlify, 2中可以直接 str.encode('hex')
    rs = int(binascii.hexlify(text), 16) ** int(pub_key, 16) % int(mod, 16)
    return format(rs, 'x').zfill(256)


def encrypted_request(text):
    # 这边是加密过程。
    text = json.dumps(text)
    sec_key = create_secret_key(16)
    enc_text = aes_encrypt(aes_encrypt(text, nonce), sec_key)
    enc_sec_key = rsa_encrypt(sec_key, pubKey, modulus)
    # 在那个js中也可以找到。
    # params加密后是个byte，解下码。
    return {'params': enc_text.decode(), 'encSecKey': enc_sec_key}

# def get_real_url(rid):
#     try:
#         request_data = encrypted_request({"liveRoomNo": rid})
#         response = requests.post(url='https://api.look.163.com/weapi/livestream/room/get/v3', data=request_data)
#         real_url = response.json()['data']['roomInfo']['liveUrl']
#     except Exception:
#         raise Exception('直播间不存在或未开播')
#     return real_url