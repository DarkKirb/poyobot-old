"""This module contains an 8ball"""
from utils import Cog, command
from discord.ext import commands
import hashlib
import random
import datetime
import re


__author__ = "Dark Kirb"
__license__ = "BSD-2clause"
__website__ = "https://github.com/DarkKirb/poyobot/blob/master/mod/8ball.py"
__version__ = "1.0"


class EightBall(Cog):
    @command(name="8ball")
    async def _8ball(self, ctx, *, msg: str):
        """Predicts the outcome of a message"""
        messages = ["It is certain",
                    "It is decidedly so",
                    "Without a doubt",
                    "Yes definitely",
                    "You may rely on it",
                    "You may count on it",
                    "As I see it, yes",
                    "Most likely",
                    "Outlook good",
                    "Yes",
                    "Signs point to yes",
                    "Absolutely",
                    "Don't count on it",
                    "My reply is no",
                    "My sources say no",
                    "Outlook not so good",
                    "Very doubtful",
                    "Chances aren't good"]
        neutral_messages = ["Reply hazy try again",
                            "Ask again later",
                            "Better not tell you now",
                            "Cannot predict now",
                            "Concentrate and ask again"]
        random.seed(ctx.message.id)
        if random.randrange(0, 23) < 5:
            await ctx.send(random.choice(neutral_messages))
            return
        content = msg
        # Replace message contents to seem more random
        regexes = {
            r'(I|Me)\W': str(ctx.message.author.id),
            r'^(i|me)\W': str(ctx.message.author.id),
            r'\W(i|me)\W': str(ctx.message.author.id),
            r'(Now)\W': datetime.datetime.utcnow().isoformat(),
            r'^(now|rn)\W': datetime.datetime.utcnow().isoformat(),
            r'\W(now|rn)\W': datetime.datetime.utcnow().isoformat(),
            r'(Today)\W': datetime.time.today().isoformat(),
            r'^(today)\W': datetime.time.today().isoformat(),
            r'\W(today)\W': datetime.time.today().isoformat(),
        }
        for regex, repl in regexes.items():
            content = re.sub(regex, repl, content)
        print(f"Mangled input from {msg} to {content}.")
        random.seed(hashlib.sha512(content.encode()).digest())
        await ctx.send(random.choice(messages))


def setup(bot):
    global cog
    cog = EightBall(bot)
