"""This module is for creating images that look like vaporwave"""
import discord
from utils import Cog, command
from discord.ext import commands
import asyncio
from PIL import Image
import opuslib
import aiohttp
import io
import threading


__author__ = "Dark Kirb"
__license__ = "BSD-2clause"
__website__ = None
__version__ = "1.0"


class Vaporwave(Cog):
    @command()
    async def mp3ify(self, ctx, fname: str = None):
        if fname is None:
            if len(ctx.message.attachments) == 0:
                await ctx.send("You have to include an image")
                return
            x = ctx.message.attachments[0]["url"]
        else:
            x = fname
        asyncio.ensure_future(self.mp3ify_task(ctx, x))

    async def mp3ify_task(self, ctx, fname):
        loop = asyncio.get_event_loop()
        event = asyncio.Event()

        async with aiohttp.ClientSession() as session:
            async with session.get(fname) as response:
                data = io.BytesIO(await response.read())

        f = None

        def worker():  # worker thread
            nonlocal loop, data, event, f
            data.seek(0)
            im = Image.open(data)
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
