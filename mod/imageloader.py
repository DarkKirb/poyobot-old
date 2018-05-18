"""This module is a library module that makes modules able to take images from
certain sources, like for example embeds, uploads, links and channel history"""
from utils import Cog
import discord
import aiohttp
from PIL import Image
import io


__author__ = "Dark Kirb"
__license__ = "BSD-2clause"
__website__ = \
    "https://github.com/DarkKirb/poyobot/blob/master/mod/imageloader.py"
__version__ = "1.0"


class ImageLoader(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self._session = aiohttp.ClientSession()
        self._session_enter = self._session.__aenter__()
        self._session_exit = self._session.__aexit__
        self.session_awaited = False

    @property
    async def session(self):
        if not self.session_awaited:
            self._session = await self._session_enter
            self.session_awaited = True
        return self._session

    async def fetch_image(self, url):
        session = await self.session
        async with session.get(url) as resp:
            if not resp.headers["Content-Type"].startswith("image/"):
                return None
            bio = io.BytesIO()
            bio.write(await resp.read())
            bio.seek(0)
            return Image.open(bio)

    async def get_msg_image(self, msg):
        # 1) check the contents for any uploads
        for attachment in msg.attachments:
            if attachment.height is None:
                continue
            im = await self.fetch_image(attachment.url)
            if im is not None:
                return im
        # 2) check the contents for any embeds
        for embed in msg.embeds:
            if embed.image == discord.Embed.Empty:
                continue
            im = await self.fetch_image(embed.image.url)
            if im is not None:
                return im
        # 3) check the contents for any links
        ex = msg.content.split(" ")
        for word in ex:
            if word.startswith("http"):
                # try loading it
                im = await self.fetch_image(attachment.url)
                if im is not None:
                    return im

    async def get_latest_image(self, channel):
        async for msg in channel.history():
            im = await self.get_msg_image(msg)
            if im is not None:
                return im

    async def on_unload(self):
        await self._session_exit(None, None, None)


def setup(bot):
    global cog
    cog = ImageLoader(bot)
