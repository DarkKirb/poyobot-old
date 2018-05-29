"""This module is for creating images that look like vaporwave"""
import discord
from utils import Cog, command
from discord.ext import commands
import asyncio
from PIL import Image
import opuslib
import io
import threading
from . import imageloader


__author__ = "Dark Kirb"
__license__ = "BSD-2clause"
__website__ = \
    "https://github.com/DarkKirb/poyobot/blob/master/mod/vaporwave.py"
__version__ = "1.0"
dependencies = ["imageloader"]


class Vaporwave(Cog):
    @command()
    async def mp3ify(self, ctx):
        im = await imageloader.cog.get_latest_image(ctx.message.channel)
        if im is None:
            await ctx.send("You have to include an image as no recent image \
was found")
            return

        asyncio.ensure_future(self.mp3ify_task(ctx, im))

    async def mp3ify_task(self, ctx, im):
        loop = asyncio.get_event_loop()
        event = asyncio.Event()

        f = None

        def worker():  # worker thread
            nonlocal loop, im, event, f
            pcm = im.tobytes()
            if len(pcm) % 2:
                pcm = b'\0' + pcm
            encoder = opuslib.Encoder(48000, 1, 'restricted_lowdelay')
            frames = []
            for x in range(0, len(pcm), 960*2):
                frames.append(encoder.encode(pcm[x:x+960*2], 960))
            opcmlen = len(pcm)
            decoder = opuslib.Decoder(48000, 1)
            data = b''
            for frame in frames:
                data += decoder.decode(frame, 960)
            im = Image.frombytes(im.mode, im.size, data[len(data)-opcmlen:])
            im = im.convert("RGB")

            f = io.BytesIO()
            im.save(f, "JPEG")
            f.seek(0)
            loop.call_soon_threadsafe(event.set)
        t = threading.Thread(target=worker)
        t.start()
        await event.wait()
        t.join()
        await ctx.send("", file=discord.File(f, filename="mp3.jpg"))


def setup(bot):
    global cog
    cog = Vaporwave(bot)
