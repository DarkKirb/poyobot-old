"""This is a moderation module meant to log user activity such as avatars,
nicknames, deleted and edited messages, ..."""
from utils import Cog, command, group, is_admin, NotAdminError
from discord.ext import commands
from discord.utils import find
import discord
from async_lru import alru_cache
import collections
import database


__author__ = "Dark Kirb"
__license__ = "BSD-2clause"
__website__ = "https://github.com/DarkKirb/poyobot/blob/master/mod/log.py"
__version__ = "0.1"


table = database.db.log_table


class Log(Cog):
    auto_enable = False

    def __init__(self, bot):
        super().__init__(bot)
        self.messages = collections.deque()

    @alru_cache()
    async def can_monitor_server(self, id):
        doc = await table.find_one({"guild": id})
        if doc is None:
            return False
        return doc["enabled"]

    @alru_cache()
    async def can_monitor_event(self, id, event):
        doc = await table.find_one({"guild": id})
        if event + "_enabled" not in doc:
            return False
        return doc[event + "_enabled"]

    @alru_cache()
    async def get_event_channel(self, id, event):
        doc = await table.find_one({"guild": id})
        guild = find(lambda x: x.id == id, self.bot.guilds)
        if event + "_channel" in doc:
            channel_id = doc[event + "_channel"]
        else:
            channel_id = doc["channel"]
        channel = find(lambda x: x.id == channel_id, guild.channels)
        return channel

    async def on_message(self, message):  # add messages into cache
        if not await self.can_monitor_server(message.guild.id):
            return
        self.messages.append((message, message.content))
        if len(self.messages) > 10000:
            self.messages.popleft()

    async def on_raw_message_delete(self, event):
        if not await self.can_monitor_server(event.guild_id):
            return
        try:
            msg = find(lambda x: x[0].id == event.message_id, self.messages)
            if msg is None:
                raise ValueError("not found")
            index = self.messages.index(msg)
            del self.messages[index]
            msg = msg[0]
        except ValueError as e:
            print(e)
            index = None
            msg = None
        if not await self.can_monitor_event(event.guild_id, "delete"):
            return
        channel = await self.get_event_channel(event.guild_id, "delete")
        if msg is None:
            src_channel = find(lambda x: x.id == event.channel_id,
                               channel.guild.channels)
            e = discord.Embed()
            e.color = 0xFF0000
            e.title = "Message deleted in " + src_channel.name
        else:
            e = discord.Embed()
            e.color = 0xFF0000
            e.title = "Message deleted in " + msg.channel.name
            e.add_field(name="Contents", value=msg.content)
            e.add_field(name="Name",
                        value=f"{msg.author.name}#{msg.author.discriminator}")
        await channel.send(embed=e)

    async def on_raw_bulk_message_delete(self, event):
        if not await self.can_monitor_server(event.guild_id):
            return
        for msg in event.message_ids:
            msg = find(lambda x: x[0].id == msg, self.messages)
            if msg is None:
                continue
            index = self.messages.index(msg)
            del self.messages[index]
        if not await self.can_monitor_event(event.guild_id, "delete"):
            return
        channel = await self.get_event_channel(event.guild_id, "delete")
        src_channel = find(lambda x: x.id == event.channel_id,
                           channel.guild.channels)
        e = discord.Embed()
        e.color = 0xFF0000
        e.title = "Bulk delete in " + msg.channel.name
        e.set_footer(text=str(len(event.message_ids)) + " messages deleted")
        await channel.send(embed=e)

    async def on_raw_message_edit(self, payload):
        if "content" not in payload.data:
            return
        # find message id
        msg = find(lambda x: x[0].id == payload.message_id, self.messages)
        if msg is None:
            return
        if not await self.can_monitor_server(msg[0].guild.id):
            return
        if not await self.can_monitor_event(msg[0].guild.id, "edit"):
            return
        channel = await self.get_event_channel(msg[0].guild.id, "edit")

        e = discord.Embed()
        e.color = 0xFF
        e.title = "Edit in " + msg[0].channel.name
        e.add_field(name="Before", value=msg[1])
        e.add_field(name="Current", value=payload.data["content"])
        idx = self.messages.index(msg)
        self.messages[idx] = (msg[0], payload.data["content"])
        await channel.send(embed=e)

    async def on_member_join(self, member):
        if not await self.can_monitor_server(member.guild.id):
            return
        if not await self.can_monitor_event(member.guild.id, "join"):
            return
        channel = await self.get_event_channel(msg.guild.id, "join")

        e = discord.Embed()
        e.color = 0xFF00
        e.title = "Member joined"
        e.add_field(name="Name", value=f"{member.name}#{member.discriminator}")
        e.add_field(name="ID", value=member.id)
        e.add_field(name="Created at", value=member.created_at.isoformat())
        await channel.send(embed=e)

    async def on_member_remove(self, member):
        if not await self.can_monitor_server(member.guild.id):
            return
        if not await self.can_monitor_event(member.guild.id, "leave"):
            return
        channel = await self.get_event_channel(member.guild.id, "leave")

        e = discord.Embed()
        e.color = 0xFF0000
        e.title = "Member left"
        e.add_field(name="Name", value=f"{member.name}#{member.discriminator}")
        e.add_field(name="ID", value=member.id)
        e.add_field(name="Created at", value=member.created_at.isoformat())
        e.add_field(name="Joined at", value=member.joined_at.isoformat())
        await channel.send(embed=e)

    async def on_member_update(self, before, after):
        if not await self.can_monitor_server(before.guild.id):
            return
        if before.nick != after.nick and await self.can_monitor_event(
                before.guild.id, "rename"):
            channel = await self.get_event_channel(before.guild.id, "rename")
            e = discord.Embed()
            e.title = "Nickname changed"
            e.add_field(name="Name",
                        value=f"{before.name}#{before.discriminator}")
            e.add_field(name="Before", value=before.nick)
            e.add_field(name="After", value=after.nick)
            await channel.send(embed=e)
        if ((before.name != after.username) or (before.discriminator !=
                after.discriminator)) and await self.can_monitor_event(
                before.guild.id, "rename"):
            channel = await self.get_event_channel(before.guild.id, "rename")
            e = discord.Embed()
            e.title = "Identity changed"
            e.add_field(name="ID", value=before.id)
            e.add_field(name="Before",
                        value=f"{before.name}#{before.discriminator}")
            e.add_field(name="After",
                        value=f"{after.name}#{after.discriminator}")
            await channel.send(embed=e)
        if before.avatar != after.avatar and await self.can_monitor_event(
                before.guild.id, "avatar"):
            channel = await self.get_event_channel(before.guild.id, "rename")
            e = discord.Embed()
            e.title = "Avatar changed"
            e.add_field(name="Name",
                        value=f"{after.name}#{after.discriminator}")
            e.set_image(url=after.avatar_url)
            await channel.send(embed=e)

    @group()
    async def logger(self, ctx):
        """Command for configuring the logger"""
        if not await is_admin(ctx.message.guild, ctx.message.author):
            raise NotAdminError()

    @logger.command()
    async def enable(self, ctx):
        """Enables the logger on the server. No data will be collected/sent \
unless this command has been run first"""
        doc = await table.find_one({"guild": ctx.message.guild.id})
        if doc is None:
            create = True
            doc = {"guild": ctx.message.guild.id,
                   "enabled": True}
            await table.insert_one(doc)
        else:
            doc["enabled"] = True
            await table.replace_one({"_id": doc["_id"]}, doc)

        self.can_monitor_server.invalidate(ctx.message.guild.id)
        await ctx.send("👌")

    @logger.command()
    async def disable(self, ctx):
        """Disables the logger on the server. This means that new data will \
no longer be collected/sent after the command has been run"""
        doc = await table.find_one({"guild": ctx.message.guild.id})
        if doc is not None:
            doc["enabled"] = False
            await table.replace_one({"_id": doc["_id"]}, doc)
            self.can_monitor_server.invalidate(ctx.message.guild.id)
        await ctx.send("👌")

    @logger.command()
    async def enable_log(self, ctx, kind: str, channel: discord.TextChannel):
        """Enables logging a specific kind of event. Available are delete, \
edit, join, leave, rename and avatar, although more events might become \
available in the future."""
        doc = await table.find_one({"guild": ctx.message.guild.id})
        if doc is None or not doc["enabled"]:
            await ctx.send("You need to enable the log first!")
            return
        doc[kind + "_enabled"] = True
        doc[kind + "_channel"] = channel.id
        await table.replace_one({"_id": doc["_id"]}, doc)
        self.can_monitor_event.invalidate(ctx.message.guild.id, kind)
        self.get_event_channel.invalidate(ctx.message.guild.id, kind)
        await ctx.send("👌")

    @logger.command()
    async def disable_log(self, ctx, kind: str):
        """Disables logging a specific kind of event."""
        doc = await table.find_one({"guild": ctx.message.guild.id})
        if doc is None or not doc["enabled"]:
            await ctx.send("You need to enable the log first!")
            return
        doc[kind + "_enabled"] = False
        await table.replace_one({"_id": doc["_id"]}, doc)
        self.can_monitor_event.cache_clean()
        await ctx.send("👌")


def setup(bot):
    global cog
    cog = Log(bot)
