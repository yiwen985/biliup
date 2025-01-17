import json
from urllib.parse import unquote

import requests
from . import logger, match1
from biliup.config import config
from ..engine.decorators import Plugin
from ..engine.download import DownloadBase
from biliup.plugins.Danmaku import DanmakuClient


@Plugin.download(regexp=r'(?:https?://)?(?:(?:www|m|live)\.)?douyin\.com')
class Douyin(DownloadBase):
    def __init__(self, fname, url, suffix='flv'):
        super().__init__(fname, url, suffix)
        self.douyin_danmaku = config.get('douyin_danmaku', False)
        self.fake_headers['Referer'] = "https://live.douyin.com/"
        self.fake_headers['Cookie'] = config.get('user', {}).get('douyin_cookie', '')

    def check_stream(self, is_check=False):
        if "/user/" in self.url:
            try:
                user_page = requests.get(self.url, headers=self.fake_headers, timeout=5).text
                user_page_data = unquote(
                    user_page.split('<script id="RENDER_DATA" type="application/json">')[1].split('</script>')[0])
                room_id = match1(user_page_data, r'"web_rid":"([^"]+)"')
                if room_id is None or not room_id:
                    logger.debug(f"{Douyin.__name__}: {self.url}: 未开播")
                    return False
            except:
                logger.warning(f"{Douyin.__name__}: {self.url}: 获取房间ID错误")
                return False
        else:
            try:
                room_id = self.url.split('douyin.com/')[1].split('/')[0].split('?')[0]
                if not room_id:
                    raise
            except:
                logger.warning(f"{Douyin.__name__}: {self.url}: 直播间地址错误")
                return False

        if room_id[0] == "+":
            room_id = room_id[1:]
        if room_id.isdigit():
            room_id = f"+{room_id}"

        try:
            page = requests.get(f"https://live.douyin.com/{room_id}", headers=self.fake_headers, timeout=5).text
            page_data = unquote(
                page.split('<script id="RENDER_DATA" type="application/json">')[1].split('</script>')[0])
            room_info = json.loads(page_data)['app']['initialState']['roomStore']['roomInfo']['room']
        except (KeyError, IndexError):
            logger.warning(f"{Douyin.__name__}: {self.url}: 获取错误,请检查Cookie设置")
            return False
        except:
            logger.warning(f"{Douyin.__name__}: {self.url}: 获取错误")
            return False

        try:
            if room_info.get('status') != 2:
                logger.debug(f"{Douyin.__name__}: {self.url}: 未开播")
                return False

            stream_data = json.loads(room_info['stream_url']['live_core_sdk_data']['pull_data']['stream_data'])['data']

            # 原画origin 蓝光uhd 超清hd 高清sd 标清ld 流畅md 仅音频ao
            quality_items = ['origin', 'uhd', 'hd', 'sd', 'ld', 'md']
            quality = config.get('douyin_quality', 'origin')
            if quality not in quality_items:
                quality = quality_items[0]

            # 如果没有这个画质则取相近的 优先低清晰度
            if quality not in stream_data:
                # 可选的清晰度 含自身
                optional_quality_items = [x for x in quality_items if x in stream_data.keys() or x == quality]
                # 自身在可选清晰度的位置
                optional_quality_index = optional_quality_items.index(quality)
                # 自身在所有清晰度的位置
                quality_index = quality_items.index(quality)
                # 高清晰度偏移
                quality_left_offset = None
                # 低清晰度偏移
                quality_right_offset = None

                if optional_quality_index + 1 < len(optional_quality_items):
                    quality_right_offset = quality_items.index(
                        optional_quality_items[optional_quality_index + 1]) - quality_index

                if optional_quality_index - 1 >= 0:
                    quality_left_offset = quality_index - quality_items.index(
                        optional_quality_items[optional_quality_index - 1])

                # 取相邻的清晰度
                if quality_right_offset <= quality_left_offset:
                    quality = optional_quality_items[optional_quality_index + 1]
                else:
                    quality = optional_quality_items[optional_quality_index - 1]

            self.raw_stream_url = stream_data[quality]['main']['flv']
            self.room_title = room_info['title']
        except:
            logger.warning(f"{Douyin.__name__}: {self.url}: 解析错误")
            return False
        return True

    def danmaku_download_start(self, filename):
        if self.douyin_danmaku:
            self.danmaku = DanmakuClient(self.url, filename + "." + self.suffix)
            self.danmaku.start()

    def close(self):
        if self.danmaku:
            self.danmaku.stop()
