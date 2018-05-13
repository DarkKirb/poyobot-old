from discord.ext import commands
import importlib


class SubcommandError(commands.CommandError):
    pass


class NotAdminError(commands.CheckFailure):
    pass


class NotModError(commands.CheckFailure):
    pass


class Cog():
    def __init__(self, bot):
        self.bot = bot
        self._module = importlib.import_module(self.__class__.__module__)
        self.global_enable = True
        self.overrides = {}
        bot.add_cog(self)

    def check_once(self, ctx):
        mod = self._module
        name = mod.__name__
        if name == "module":
            return True  # This module can't be deactivated ever

        if ctx.message.author.id in self.overrides:
            if not self.overrides[ctx.message.author.id]:
                return False

        enabled = self.global_enable
        if ctx.message.guild.id in self.overrides:
            enabled = self.overrides[ctx.message.guild.id]

        if ctx.message.channel.id in self.overrides:
            enabled = self.overrides[ctx.message.channel.id]

        for role in ctx.message.author.roles:
            if role.id in self.overrides:
                enabled = self.overrides[role.id]

        return enabled

    def __global_check_once(self, ctx):
        return self.check_once(ctx)


async def is_admin(guild, member):
    if guild.owner == member:
        return True
    permissions = member.guild_permissions
    if permissions.administrator:
        return True
    if permissions.manage_guild:
        return True
    return permissions.kick_members and permissions.ban_members


async def is_mod(guild, member, channel):
    if await is_admin(guild, member):
        return True
    permissions = channel.permissions_for(member)
    if permissions.manage_channels:
        return True
    return permissions.manage_messages
