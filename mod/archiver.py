"""This is a module that archives channel contents and uploads them as one/
multiple tar.xz files"""
from utils import Cog, is_mod, command
from discord.ext import commands
import discord
import tempfile
import aiofiles
import os
import io
import hashlib
import tarfile


__author__ = "Dark Kirb"
__license__ = "BSD-2clause"
__website__ = "https://github.com/DarkKirb/poyobot/blob/master/mod/archiver.py"
__version__ = "1.0"


class Archiver(Cog):
    @command()
    async def archiver(self, ctx):
        """Archives the current channel (but doesn't delete it)"""
        if not await is_mod(ctx.message.guild, ctx.message.author,
                            ctx.message.channel):
            await ctx.send("You need to be moderator to archive a channel!")
        msg = await ctx.send("Archiving the channel. This might take a while")
        number = 0
        with tempfile.TemporaryDirectory() as tempdirname:
            archived_files = []
            os.makedirs(os.path.join(tempdirname, "imgs"), exist_ok=True)
            f = None
            last_day = None
            async for message in ctx.message.channel.history(
                    limit=None,
                    reverse=True):
                if last_day is None or last_day != message.created_at.date():
                    if f is not None:
                        await f.close()
                    last_day = message.created_at.date()
                    fname = os.path.join(tempdirname,
                                         last_day.isoformat() + ".log")
                    f = await aiofiles.open(fname, "w")
                    archived_files.append(fname)
                initial_str = (f"[{message.created_at.isoformat()}] " +
                               f"<{message.author.name}" +
                               f"#{message.author.discriminator}>")
                padding_len = len(initial_str)
                padding = ' ' * padding_len
                firstline = message.content.split("\n")[0]
                await f.write(f"{initial_str} {firstline}\n")
                for line in message.content.split("\n")[1:]:
                    await f.write(f"{padding} {line}\n")

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
                        fname = os.path.join(tempdirname,
                                             "imgs",
                                             f"{filehash}.{ext}"
                                             )
                        archived_files.append(fname)
                        async with aiofiles.open(fname, mode="wb") as f3:
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

            if f is not None:
                await f.close()
            await msg.edit(content="Archived all messages. Packing…\n")
            tar_count = 0
            tar_name_prefix = f"{ctx.message.created_at.isoformat()}-"
            tar_name_prefix = os.path.join(tempdirname, tar_name_prefix)
            tar_name_suffix = ".tar"
            tfn = f"{tar_name_prefix}{tar_count}{tar_name_suffix}"
            tf = tarfile.open(tfn, "w")
            size = 2 * 20 * 512
            for fname in archived_files:
                size += os.path.getsize(fname)
                size += 512 - (size % 512)
                if size > 8*1024*1024:  # file full.
                    tf.close()
                    tar_count += 1
                    await ctx.send(file=discord.File(tfn))
                    tfn = f"{tar_name_prefix}{tar_count}{tar_name_suffix}"
                    tf = tarfile.open(tfn, "w")
                    size = 2 * 20 * 512
                    size += os.path.getsize(fname)
                    size += 512 - (size % 512)
                tf.add(fname)
            tf.close()
            await ctx.send("done", file=discord.File(tfn))


def setup(bot):
    global cog
    cog = Archiver(bot)
