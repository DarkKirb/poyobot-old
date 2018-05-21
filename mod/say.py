"""This module is an example module that is a base skeleton for many other
modules. It has a single command that simply says its arguments"""
from utils import Cog, command
from discord.ext import commands


__author__ = "Dark Kirb"
__license__ = "Public domain"
__website__ = "https://github.com/DarkKirb/poyobot/blob/master/mod/say.py"
__version__ = "1.0"


class Say(Cog):
    @command()
    async def say(self, ctx, *, msg: str):
        """Output the arguments as a message"""
        if "@everyone" in msg:
            await ctx.send("No")
            return
        if "@here" in msg:
            await ctx.send("No")
            return
        await ctx.send(msg)


def setup(bot):
    global cog
    cog = Say(bot)
