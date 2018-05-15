"""This module is for playing music in the vc"""
from utils import Cog
from discord.ext import commands
import asyncio
import discord
import glob
import random
import youtube_dl
import functools


__author__ = "Dark Kirb"
__license__ = "BSD-2clause"
__website__ = None
__version__ = "1.0"


if not discord.opus.is_loaded():
    discord.opus.load_opus('opus')

filenames = glob.glob('music/**/*', recursive=True)


class VoiceEntry:
    def __init__(self, message, player):
        self.requester = message.author
        self.channel = message.channel
        self.player = player

    def __str__(self):
        fmt = '*{0.title}* uploaded by {0.uploader} and requested by \
{1.display_name}'
        duration = self.player.duration
        if duration:
            fmt += ' [length: {0[0]}m {0[1]}s]'.format(divmod(duration, 60))
        return fmt.format(self.player, self.requester)


class AutoplayEntry:
    def __init__(self, player):
        self.requester = None
        self.channel = None
        self.player = player

    def __str__(self):
        fmt = '*{0.title}* (autoplay)'
        return fmt.format(self.player)


class VoiceState:
    def __init__(self, bot):
        self.current = None
        self.voice = None
        self.channel = None
        self.bot = bot
        self.play_next_song = asyncio.Event()
        self.start_loop = asyncio.Event()
        self.songs = asyncio.Queue()
        self.skip_votes = set()  # a set of user_ids that voted
        self.audio_player = self.bot.loop.create_task(self.audio_player_task())
        self.idle_play = True

    @property
    def player(self):
        return self.current.player

    def skip(self):
        self.skip_votes.clear()
        self.player.cleanup()
        self.play_next_song.set()

    def toggle_next(self, error):
        self.bot.loop.call_soon_threadsafe(self.play_next_song.set)

    async def audio_player_task(self):
        await self.start_loop.wait()
        while True:
            self.play_next_song.clear()
            if self.songs.empty():
                print("empty")
                self.idle_play = True
                fname = random.choice(filenames)
                print(fname)
                try:
                    player = discord.FFmpegPCMAudio(fname)
                    player = discord.PCMVolumeTransformer(player)
                    self.voice.play(
                        player,
                        after=self.toggle_next
                    )
                    player.title = fname
                    self.current = AutoplayEntry(player)
                except Exception as e:
                    print(e)
                print(player)
            else:
                print("not empty")
                self.idle_play = False
                self.current = await self.songs.get()
                self.voice.play(
                    self.current.player,
                    after=self.toggle_next
                )
                await self.current.channel.send(
                    'Now playing ' + str(self.current)
                )
            try:
                self.current.player.start()
            except Exception as e:
                print(e)
            print("Started")
            await self.play_next_song.wait()
            print("Stopped")


class Audio(Cog):
    def __init__(self, bot):
        super().__init__(bot)
        self.voice_states = {}

    def get_voice_state(self, guild):
        state = self.voice_states.get(guild.id)
        if state is None:
            state = VoiceState(self.bot)
            self.voice_states[guild.id] = state
        return state

    async def create_voice_client(self, channel):
        voice = await channel.connect()
        state = self.get_voice_state(channel.guild)
        state.voice = voice
        state.channel = channel
        state.start_loop.set()

    async def playing_handler(self, ctx):
        state = self.get_voice_state(ctx.message.guild)
        if state.current is None:
            await ctx.send("Not playing anything")
        else:
            skip_count = len(state.skip_votes)
            skip_needed = int(2/3 * (len(state.channel.members)-1) + 2/3)
            await ctx.send("Now playing {} [skips: {}/{}]".format(
                state.current,
                skip_count,
                skip_needed
            ))

    async def join_handler(self, ctx, channel):
        try:
            await self.create_voice_client(channel)
        except discord.ClientException:
            await ctx.send("Already in a voice channel")
        except discord.InvalidArgument:
            await ctx.send("This is not a voice channel")
        else:
            await ctx.send("Ready to play audio in " + channel.name)

    @commands.group(invoke_without_subcommand=True)
    async def audio(self, ctx):
        """Audio commands"""
        pass

    @audio.command()
    async def join(self, ctx, channel: discord.VoiceChannel):
        """Makes the bot join the specified voice channel"""
        await self.join_handler(ctx, channel)

    async def summon_handler(self, ctx):
        summoned_channel = ctx.message.author.voice
        if summoned_channel is None:
            await ctx.send("You are not in a voice channel!")
            return False

        summoned_channel = summoned_channel.channel

        state = self.get_voice_state(ctx.message.guild)
        if state.voice is None:
            await self.join_handler(ctx, summoned_channel)
        else:
            await state.voice.move_to(summoned_channel)
            state.channel = summoned_channel
        return True

    @audio.command()
    async def summon(self, ctx):
        """Makes the bot join the current voice channel"""
        await self.summon_handler(ctx)

    @audio.command()
    async def play(self, ctx, song: str):
        """Plays a song

        If there is a song currently in the queue, then it is
        queued until the next song is done playing.

        This command automatically searches as well from YouTube.
        The list of supported sites can be found here:
        https://rg3.github.io/youtube-dl/supportedsites.html
        """

        state = self.get_voice_state(ctx.message.guild)
        opts = {
                'default_search': 'auto',
                'quiet': True,
                'format': 'webm[abr>0]/bestaudio/best',
                }

        if state.voice is None:
            success = await self.summon_handler(ctx)
            if not success:
                return

        try:
            ydl = youtube_dl.YoutubeDL(opts)
            func = functools.partial(ydl.extract_info, song, download=False)
            info = await self.bot.loop.run_in_executor(None, func)
            if "entries" in info:
                info = info['entries'][0]
            download_url = info['url']
            player = discord.FFmpegPCMAudio(download_url)
            player = discord.PCMVolumeTransformer(player)
            player.duration = info.get("duration")
            player.uploader = info.get('uploader')

            is_twitch = 'twitch' in song
            if is_twitch:
                # twitch has 'title' and 'description' sort of mixed up.
                player.title = info.get('description')
            else:
                player.title = info.get('title')

        except Exception as e:
            fmt = 'An error occurred while processing this request: \
```py\n{}: {}\n```'
            await ctx.send(fmt.format(type(e).__name__, e))
            return
        player.volume = 0.6
        entry = VoiceEntry(ctx, player)
        await ctx.send('Enqueued ' + str(entry))
        await state.songs.put(entry)

    @audio.command()
    async def volume(self, ctx, value: int):
        """Sets the volume of the currently playing song"""
        state = self.get_voice_state(ctx.message.guild)
        player = state.player
        player.volume = value / 100
        await ctx.send("Set the volume to {:.0%}".format(player.volume))

    @audio.command()
    async def stop(self, ctx):
        """Stops playing audio and leaves the voice channel"""
        server = ctx.message.guild
        state = self.get_voice_state(server)

        player = state.player
        player.cleanup()

        try:
            state.audio_player.cancel()
            del self.voice_states[server.id]
            await state.voice.disconnect()
        except Exception as e:
            print(e)

    @audio.command()
    async def skip(self, ctx):
        """Vote to skip a song. The song requester can automatically skip.

        ⅔ of all the listeners have to agree skipping to the song.
        """
        state = self.get_voice_state(ctx.message.guild)
        if state.idle_play:
            await ctx.send('Skipping song...')
            state.skip()
            return

        voter = ctx.author
        if voter == state.current.requester:
            await ctx.send('Requester requested skipping song...')
            state.skip()
        elif voter.id not in state.skip_votes:
            state.skip_votes.add(voter.id)
            total_votes = len(state.skip_votes)
            votes_needed = int(2/3 * (len(state.channel.members)-1)+2/3)
            if total_votes >= votes_needed:
                await ctx.send('Skip vote passed, skipping song...')
                state.skip()
            else:
                await ctx.send('Skip vote added, currently at [{}/{}]'
                               .format(total_votes, votes_needed))
        else:
            votes_needed = int(2/3 * (len(state.channel.members)-1)+2/3)
            if total_votes >= votes_needed:
                await ctx.send('Skip vote passed, skipping song...')
            else:
                await ctx.send('You have already voted to skip this song.')

    @audio.command()
    async def playing(self, ctx):
        """Displays what song is currently playing"""
        await self.playing_handler(ctx)

    def __global_check_once(self, ctx):
        return self.check_once(ctx)


def setup(bot):
    global cog
    cog = Audio(bot)
