"""This is a module that archives channel contents and uploads them as one/
multiple tar.xz files"""
from utils import Cog, is_mod, command
from discord.ext import commands
import os
import io
import hashlib
import datetime
import discord
from .tar import TARInstance


__author__ = "Dark Kirb"
__license__ = "BSD-2clause"
__website__ = "https://github.com/DarkKirb/poyobot/blob/master/mod/archiver.py"
__version__ = "1.0"


class Archiver(Cog):
    dependencies = ["tar"]

    @command()
    async def archiver(self, ctx, channel: discord.TextChannel = None,
                       include_images: bool = True):
        """Archives the current channel (but doesn't delete it)"""
        if channel is None:
            channel = ctx.message.channel
        if not await is_mod(ctx.message.guild, ctx.message.author,
                            channel):
            await ctx.send("You need to be moderator to archive a channel!")
        msg = await ctx.send("Archiving the channel. This might take a while")
        number = 0
        async with TARInstance(ctx, ctx.message.created_at.isoformat()) as tar:
            tar.mkdir("imgs")
            f = None
            last_day = None

            async def archive_message(message):
                nonlocal f, last_day, number
                if last_day is None or last_day != message.created_at.date():
                    if f is not None:
                        await f.flush()
                        await f.close()
                    last_day = message.created_at.date()
                    fname = os.path.join(last_day.isoformat() + ".log")
                    f = await tar[fname]
                initial_str = (f"[{message.created_at.isoformat()}] " +
                               f"<{message.author.name}" +
                               f"#{message.author.discriminator}>")
                padding_len = len(initial_str)
                padding = ' ' * padding_len
                firstline = message.content.split("\n")[0]
                await f.write(f"{initial_str} {firstline}\n")
                for line in message.content.split("\n")[1:]:
                    await f.write(f"{padding} {line}\n")

                if include_images:
                    for attachment in message.attachments:
                        f2 = io.BytesIO()
                        await attachment.save(f2)
                        filehash = hashlib.sha256(f2.read()).hexdigest()
                        fsize = f2.tell()
                        f2.seek(0)
                        ext = attachment.filename.rpartition('.')[2]
                        await f.write(
                            f"{padding} Attachment " +
                            f"{attachment.filename} {attachment.url} ")
                        if fsize < 8*1024*1024 - 4096:
                            fname = os.path.join("imgs", f"{filehash}.{ext}")
                            async with tar.open(fname, "wb") as f3:
                                await f3.write(f2.read())
                            await f.write(f"(saved as {fname})\n")
                        else:
                            await f.write(f"(too large to be saved 🙁)\n")
                        f2 = None  # save memory

                    for embed in message.embeds:
                        await f.write(f"{padding} EMBED: {embed.to_dict()}\n")
                number += 1
                if not number % 250:
                    await msg.edit(content=f"Archived {number} messages…\n")

            found = True
            message_ts = datetime.datetime.fromtimestamp(1420070400)
            while found:
                found = False
                async for message in channel.history(
                        limit=None,
                        reverse=True,
                        after=message_ts):
                    await archive_message(message)
                    found = True
                    message_ts = message.created_at
            if f is not None:
                await f.flush()
                await f.close()
            await msg.edit(content="Archived all messages. Packing…\n")
        await msg.delete()
        await ctx.send("Done.")


def setup(bot):
    global cog
    cog = Archiver(bot)
