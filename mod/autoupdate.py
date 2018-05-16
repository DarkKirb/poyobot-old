"""This module is responsible for automatically updating the bot every time
there is a new commit on upstream. It has no commands."""
from utils import Cog
import module
import discord
import subprocess
import asyncio
import shlex
import sys


__author__ = "Dark Kirb"
__license__ = "BSD-2clause"
__website__ = None
__version__ = "1.0"


def launch_process(*args):
    return asyncio.create_subprocess_shell(
        ' '.join([shlex.quote(x) for x in args]),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )


async def get_output(*args):
    process = await launch_process(*args)
    data = (await process.communicate())[0]
    if isinstance(data, bytes):
        return data.decode("UTF-8").trim()
    return data.trim()


class Autoupdate(Cog):
    def __init__(self):
        self.dont_update = False
        asyncio.ensure_future(self.update())

    def check_for_update(self):
        if not self.dont_update:
            asyncio.ensure_future(self.update())

    async def update(self):
        await self._update()
        asyncio.get_event_loop().call_later(300, self.check_for_update)

    async def _update(self):
        # 1) get the current local commit
        local_commit = await get_output("git", "rev-parse", "@")
        remote_commit = await get_output("git", "rev-parse", "origin/master")
        base = await get_output("git", "merge-base", "@", "origin/master")

        if local_commit == remote_commit:
            # nothing to do
            return

        if remote_commit == base:
            # we are ahead of master
            return
        if local_commit != base:
            # We have diverged from master
            return

        # pull from the origin

        game = discord.Game("updating...")
        await self.bot.change_presence(status=discord.Status.idle,
                                       activity=game)

        await get_output("git", "pull", "origin", "master")

        # get all the files that got changed by the commits

        file_output = await get_output("git", "diff-tree", "--no-commit-id",
                                       "--name-only", "-r",
                                       f"{local_commit}~1..HEAD")

        files = file_output.split("\n")

        for fname in files:
            if fname == "requirements.txt":
                await get_output("pip", "install", "-r", "requirements.txt")
            if fname.startswith("mod/"):
                # extract module name from it
                modname = fname.partition("/")[3].rpartition(".")[1]
                # check if module is loaded
                if f"mod.{modname}" in self.bot.extensions:
                    # reload the module
                    await module.cog.reload_mod(modname)
            if fname in ["main.py", "module.py", "database.py"]:
                # we can't reload the modules
                await self.bot.logoff()
                sys.exit(0)

        # bot was updated
        await self.bot.change_presence(status=discord.Status.online,
                                       activity=None)

    async def on_unload(self):
        self.dont_update = True

    def __global_check_once(self, ctx):
        return self.check_once(ctx)


def setup(bot):
    global cog
    cog = Autoupdate(bot)
