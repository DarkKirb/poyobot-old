"""This module gives out roles depending on reactions on a message"""
from utils import Cog, is_mod, command
from discord.ext import commands
from discord.utils import find
import database


__author__ = "Dark Kirb"
__license__ = "BSD-2clause"
__website__ = None
__version__ = "1.0"


table = database.db.reaction_role


class ReactionRole(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.reaction_role_msgs = {}

    async def init(self):
        await super().init()
        async for document in table.find({}):
            key = document["message"]
            value = document["reactions"]
            self.reaction_role_msgs[key] = value

    @command()
    async def add_reaction_role(self, ctx, *, message: str):
        if not await is_mod(ctx.message.guild, ctx.message.author,
                            ctx.message.channel):
            await ctx.send("You need moderation permissions to do this.")
            return
        to_delete = []
        msg = await ctx.send(message)
        to_delete.append(await ctx.send("React to the last message and then \
send the name of the role you want it to give out. React with ❌ to stop"))

        def check(reaction, user):
            return user == ctx.message.author and \
                reaction.message.id == msg.id

        top_role = ctx.message.author.top_role
        emoji_role = {}
        while True:
            reaction, user = await self.bot.wait_for('reaction_add',
                                                     check=check)

            if reaction.emoji == '❌':
                break
            to_delete.append(await ctx.send("What role do you want to grant?"))

            def check2(m):
                return m.author == ctx.message.author \
                    and m.channel == ctx.message.channel
            while True:
                message = await self.bot.wait_for('message', check=check2)
                to_delete.append(message)

                found_role = None
                for role in ctx.message.guild.roles:
                    if role.name == message.content:
                        found_role = role
                        break
                    if str(role.id) == message.content:
                        found_role = role
                        break

                if found_role is None:
                    to_delete.append(await ctx.send("I didn't find that role"))
                    continue

                if found_role >= top_role and \
                        ctx.message.guild.owner != ctx.message.author:
                    to_delete.append(await ctx.send("You can't give out a role\
 with the same or higher rank as you!"))
                    continue

                if not isinstance(reaction.emoji, str):
                    emoji = str(reaction.emoji.id)
                else:
                    emoji = reaction.emoji
                emoji_role[emoji] = found_role.id
                break
            to_delete.append(await ctx.send("React to the last message and \
then send the name of the role you want it to give out. React with ❌ to \
stop"))

        for message in to_delete:
            await message.delete()

        await table.insert_one({"message": msg.id, "reactions": emoji_role})

        self.reaction_role_msgs[msg.id] = emoji_role

    async def on_reaction_add(self, reaction, user):
        if reaction.message.id not in self.reaction_role_msgs:
            return

        emoji = reaction.emoji
        if not isinstance(emoji, str):
            emoji = str(emoji.id)
        if emoji not in self.reaction_role_msgs[reaction.message.id]:
            return
        role_id = self.reaction_role_msgs[reaction.message.id][emoji]
        await user.add_roles(
            find(lambda x: x.id == role_id, reaction.message.guild.roles)
        )

    async def on_reaction_remove(self, reaction, user):
        if reaction.message.id not in self.reaction_role_msgs:
            return

        emoji = reaction.emoji
        if not isinstance(emoji, str):
            emoji = str(emoji.id)
        if emoji not in self.reaction_role_msgs[reaction.message.id]:
            return
        role_id = self.reaction_role_msgs[reaction.message.id][emoji]
        await user.remove_roles(
            find(lambda x: x.id == role_id, reaction.message.guild.roles)
        )


def setup(bot):
    global cog
    cog = ReactionRole(bot)
