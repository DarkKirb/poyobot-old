"""This module provides a command queue for commands that are expensive and \
can only run one at a time"""
from utils import Cog, command
from discord.ext import commands
import collections
import asyncio
import functools


__author__ = "Dark Kirb"
__license__ = "Public domain"
__website__ = "https://github.com/DarkKirb/poyobot/blob/master/mod/say.py"
__version__ = "1.0"


def queue_cmd(f):
    queue = collections.deque()

    async def queue_task():
        while len(queue) != 0:
            try:
                try:
                    self, ctx, args, kwargs = queue[0]
                    await f(self, ctx, *args, **kwargs)
                except commands.CommandError as e:
                    raise
                except Exception as e:
                    raise commands.CommandError(str(e)) from e
            except commands.CommandError as e:
                ctx.command.dispatch_error(ctx, e)
            queue.popleft()

    @functools.wraps(f)
    async def queue_handler(self, ctx, *args, **kwargs):
        queue.append((self, ctx, args, kwargs))
        if len(queue) > 1:
            await ctx.send(f"This command is currently being run elsewhere. \
Execution will wait until the {len(queue)-1} people in front of you finish")
        if len(queue) == 1:
            # start task
            asyncio.ensure_future(queue_task())

    return queue_handler


class Queue(Cog):
    pass


def setup(bot):
    global cog
    cog = Queue(bot)
