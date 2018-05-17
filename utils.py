from discord.ext import commands
import discord
import importlib
import database
import asyncio


class SubcommandError(commands.CommandError):
    pass


class NotAdminError(commands.CheckFailure):
    pass


class NotModError(commands.CheckFailure):
    pass


def get_module(name):
    return importlib.import_module(name)


def command(*args, **kwargs):
    def wrapper(f):
        def check(ctx):
            return get_module(f.__module__).cog.check_once(ctx)
        if "checks" in kwargs:
            checks = kwargs.pop("checks").copy()
            checks.append(check)
        else:
            checks = [check]
        cmd = commands.command(*args, **kwargs)(f)
        cmd.checks += checks
        return cmd
    return wrapper


def group(*args, **kwargs):
    def wrapper(f):
        def check(ctx):
            return get_module(f.__module__).cog.check_once(ctx)
        if "checks" in kwargs:
            checks = kwargs.pop("checks").copy()
            checks.append(check)
        else:
            checks = [check]
        grp = commands.group(*args, **kwargs)(f)
        grp.checks += checks
        return grp
    return wrapper


class Cog():
    auto_enable = True

    def __init__(self, bot):
        self.bot = bot
        self._module = importlib.import_module(self.__class__.__module__)
        self.global_enable = self.auto_enable
        self.overrides = {}
        self.no_overrides = []
        bot.add_cog(self)
        asyncio.ensure_future(self.init())

    async def init(self):
        # fetch stuff like global enables and overrides from the database
        global_enable_tbl = database.db.global_enable
        global_enable = await global_enable_tbl.find_one(
            {
                "name": self._module.__name__
            }
        )
        if global_enable is None:
            global_enable_tbl.insert_one({"name": self._module.__name__,
                                          "enabled": self.auto_enable})
        else:
            self.global_enable = global_enable["enabled"]

    async def on_id(self, obj):  # this code is called for every ID encountered
        if not isinstance(obj, (discord.User, discord.Member, discord.Guild,
                                discord.TextChannel)):
            return
        if obj.id in self.overrides:
            return
        if obj.id in self.no_overrides:
            return
        doc = await database.db.enable.find_one({"name": self._module.__name__,
                                                 "id": obj.id})
        if doc is None:
            self.no_overrides.append(obj.id)
        else:
            print(f"Doc for {obj} found: {doc}")
            self.overrides[obj.id] = doc["enabled"]

    def check_once(self, ctx):
        mod = self._module
        name = mod.__name__
        if name == "module":
            print(f"{name}: True")
            return True  # This module can't be deactivated ever

        if ctx.message.author.id in self.overrides:
            if not self.overrides[ctx.message.author.id]:
                print(f"{name}: False")
                return False

        enabled = self.global_enable
        if ctx.message.guild.id in self.overrides:
            enabled = self.overrides[ctx.message.guild.id]

        if ctx.message.channel.id in self.overrides:
            enabled = self.overrides[ctx.message.channel.id]

        for role in ctx.message.author.roles:
            if role.id in self.overrides:
                enabled = self.overrides[role.id]

        print(f"{name}: {enabled}")
        return enabled

    async def on_unload(self):
        pass

    async def on_disable(self, where):
        pass


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
