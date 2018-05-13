from utils import Cog, is_admin, is_mod, NotAdminError, NotModError
from discord.ext import commands
class ModuleCog(Cog):
    def __init__(self, bot):
        super().__init__(bot)


    @commands.group(invoke_without_command=True)
    async def module(self, ctx):
        """Module command

Depending on your permissions, some of these commands might be unavailable."""
        await ctx.send("You need to specify a subcommand (load, unload, \
reload, list, activate, deactivate, info)")



    @module.command()
    @commands.is_owner()
    async def load(self, ctx, name: str):
        """Loads a module"""
        self.bot.load_extension(f"mod.{name}")
        await ctx.send("👌")

    @module.command()
    @commands.is_owner()
    async def unload(self, ctx, name: str):
        """Unloads a module"""
        self.bot.unload_extension(f"mod.{name}")
        await ctx.send("👌")

    @module.command()
    @commands.is_owner()
    async def reload(self, ctx, name: str):
        """Reloads a module"""
        self.bot.unload_extension(f"mod.{name}")
        self.bot.load_extension(f"mod.{name}")
        await ctx.send("👌")

    @module.command()
    async def list(self, ctx):
        """Lists loaded modules"""
        data = "```"
        async with ctx.typing():
            for modname, mod in self.bot.extensions.items():
                line = f"{modname} - enabled here: {mod.cog.check_once(ctx)}\n"
                if len(data) + len(line) + 3 >= 2000:
                    await ctx.send(data + "```")
                    data = "```"
                data += line
        if data != "```":
            await ctx.send(data + "```")

    async def set_perm(self, ctx, name: str, global_: bool, user: bool,
                       server: bool, channel: bool, enable: bool):
        mod = self.bot.extensions[f"mod.{name}"]
        cog = mod.cog
        if global_ and not await self.bot.is_owner(ctx.message.author):
            raise commands.NotOwner("You need to be owner to do that")
        if server and not await is_admin(ctx.message.guild,
                                         ctx.message.author):
            raise NotAdminError("You need to have one of the following to do \
that: be owner, admin, manage guild, kick and ban members")
        if channel and not await is_mod(ctx.message.guild,
                                        ctx.message.author,
                                        ctx.message.channel):
            raise NotModError("You need to have one of the following to do \
that: be owner, admin, manage guild, kick and ban members, manage channels, \
manage messages")

        if global_:
            cog.global_enable = enable
        if user:
            cog.overrides[ctx.message.author.id] = enable
        if server:
            cog.overrides[ctx.message.guild.id] = enable
        if channel:
            cog.overrides[ctx.message.channel.id] = enable

    @module.command()
    async def enable(self, ctx, name: str, type: str):
        """Enables a module"""
        types = {"global": (True, False, False, False),
                 "user": (False, True, False, False),
                 "server": (False, False, True, False),
                 "channel": (False, False, False, True)}
        await self.set_perm(ctx, name, *types[type], True)
        await ctx.send("👌")

    @module.command()
    async def disable(self, ctx, name: str, type: str):
        """Disables a module"""
        types = {"global": (True, False, False, False),
                 "user": (False, True, False, False),
                 "server": (False, False, True, False),
                 "channel": (False, False, False, True)}
        await self.set_perm(ctx, name, *types[type], False)
        await ctx.send("👌")

    @module.command()
    async def info(self, ctx, name: str):
        """Displays information about a loaded module"""
        mod = self.bot.extensions[f"mod.{name}"]

        outstr = f"""\
Module {mod.__name__} version {mod.__version__}

{mod.__doc__}

This module was written by {mod.__author__} and is released under \
{mod.__license__} on {mod.__website__}
        """
        await ctx.send(outstr)
