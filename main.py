import discord
from discord.ext import commands
from utils import Cog
import traceback
import json
import datetime
import io
import importlib
import module


with open("config.json") as f:
    config = json.load(f)

bot = commands.AutoShardedBot(command_prefix=commands.when_mentioned_or("!"))


module.cog = module.ModuleCog(bot)


@bot.event
async def on_ready():
    for mod in config["autoload"]:
        await module.cog.load_mod(mod)


@bot.event
async def on_command_error(ctx, ex):
    if isinstance(ex, commands.CommandNotFound):
        try:
            if bot.user in ctx.message.mentions:
                await ctx.send("Command not found")
        except:
            pass
        return
    elif isinstance(ex, commands.MissingRequiredArgument):
        try:
            await ctx.send(str(ex))
        except:
            pass
        return
    elif isinstance(ex, commands.CheckFailure):
        return
    async with ctx.typing():
        date = datetime.datetime.utcnow().isoformat() + "Z"
        s = traceback.format_exception(type(ex), ex, ex.__traceback__)
        s = '\n'.join(s)
        message = f"""\
Exception occurred on {date}

{s}

Information about the error:

Error caused by message {ctx.message.id}, which has the following contents:

{ctx.message.content}
"""
    if ctx.message.attachments != []:
        for attachment in ctx.message.attachments:
            message += f"""\

Attachment: {attachment.url}
"""
    message += f"""
In case you need more information about this issue, {ctx.message.author.id}
({ctx.message.author.name}#{ctx.message.author.discriminator}) sent the message
in {ctx.message.channel.id} ({ctx.message.channel.name})
"""
    await ctx.send(f"An error has occurred. If you want to report to the bot \
owner, please send the attached file to Dark Kirb#8601 or open up an issue \
on the bot's github page", file=discord.File(
        io.BytesIO(message.encode()),
        filename=f"error-{date}.txt"))


@bot.event
async def on_message(message):
    for name, module in bot.extensions.items():
        cog = module.cog
        await cog.on_id(message)
        await cog.on_id(message.author)
        await cog.on_id(message.guild)
        await cog.on_id(message.channel)
    await bot.process_commands(message)


@bot.command()
@commands.is_owner()
async def pyeval(ctx, *, code: str):
    exec(f"""
import asyncio
import discord

async def code():
    {code}

asyncio.ensure_future(code())
""", {"ctx":ctx})


if __name__ == "__main__":
    bot.run(config["token"], bot=True)
