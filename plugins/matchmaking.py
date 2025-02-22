import discord
from discord.ext import commands, tasks
import configparser

from utils import common

LFG_COMMAND = "lfg"

CONFIG_GAMES_COMMANDS = "GamesCommands"
CONFIG_GAMES_NAMES = "GamesFullNames"
CONFIG_GAMES_ROLES = "GamesRoles"
CONFIG_GAMES_ICONS = "GamesIcons"
CONFIG_GAMES_COLORS = "GamesColors"

EMOJI_JOIN = "👍"
EMOJI_NOTIFY = "🔔"
EMOJI_CLOSE = "✅"
EMOJIS_VALID = [EMOJI_JOIN, EMOJI_NOTIFY, EMOJI_CLOSE]

DEFAULT_AVATAR_URL = "https://i.imgur.com/xClQZ1Q.png"

class matchmaking(commands.Cog):
    
    def __init__(self, bot, config = None):
        print("Match making plugin started.")
        self.bot = bot
        self.config = config
        self.threads = []
        activity_text = str(self.bot.command_prefix) + LFG_COMMAND
        activity = self.bot.activity
        if (activity is None):
            activity = discord.Game(name=activity_text)
        else:
            activity.name += " | " + activity_text
        self.bot.activity = activity
        ## New feature to converge
        # self.refresh_threads.start()
        
    def cog_unload(self):
        # self.refresh_threads.cancel()
        super().cog_unload()
    
    def get_configured_games(self, guild_id, *args):
        guild = common.get_guild_from_config(self.config, guild_id)
        
        result = []
        for arg in args:
            result.append(common.split_config_list(self.config.get(guild, arg, fallback=None)))
        
        return tuple(result)
    
    @tasks.loop(hours=23)
    async def refresh_threads(self):
        valid_threads = []
        for thread in self.threads:
            try:
                if (not(thread.archived)):
                    await thread.send(content="Daily refresh! Enjoy!\nIf this game is over, please let me know!")
                    valid_threads.append(thread)
            except Exception as error:
                print(error)
        self.threads = valid_threads
        print("Refreshed threads:\n", self.threads)
    
    async def lfg_help(self, ctx):
        text = "Syntax:\n"
        text += "`" + ctx.prefix + LFG_COMMAND
        text += " <game> <description>` where `<game>` is a game available on the server with a corresponding role to ping.\n"
        text += "or\n"
        text += "`" + ctx.prefix + LFG_COMMAND
        text += " <description>` for a custom game (no automatic ping).\n"
        
        games, gamesNames = self.get_configured_games(ctx.guild.id, CONFIG_GAMES_COMMANDS, CONFIG_GAMES_NAMES)
        
        commands_list = []
        align = len(max(games, key=len))
        for game in games:
            index = games.index(game)
            command_text = "• `"
            command_text += game
            command_text += " " * (align-len(game)) + "`"
            if (len(gamesNames) == len(games) and len(gamesNames[index])):
                command_text += " : Looking for "
                command_text += common.indefinite_article(gamesNames[index]) + " "
                command_text += "**" + gamesNames[index] + "** game."
            command_text += "\n"
            commands_list.append(command_text)
        
        embed = discord.Embed(description="".join(commands_list))
        text += "\nGames available on your server:\n"
        
        await ctx.send(text,embed=embed)
    
    @commands.command(name=LFG_COMMAND)
    async def lfg(self, ctx, *desc):
        if (not(len(desc)) or desc[0] == common.HELP_COMMAND):
            return await self.lfg_help(ctx)
        else:
            return await self.lfg_v2(ctx, *desc)
    
    @commands.command()
    async def lfg_v2(self, ctx, *desc):
        games, gamesNames, gamesRoles, gamesIcons, gamesColors = \
        self.get_configured_games(ctx.guild.id, CONFIG_GAMES_COMMANDS, \
                                  CONFIG_GAMES_NAMES, CONFIG_GAMES_ROLES, \
                                  CONFIG_GAMES_ICONS, CONFIG_GAMES_COLORS)
                
        gameWanted = "custom"
        gameRole = ""
        gameIcon = ""
        gameColor = ""
        if (len(desc) and desc[0] in games):
            index = games.index(desc[0])
            if (len(gamesNames) == len(games) and len(gamesNames[index])):
                gameWanted = gamesNames[index]
            if (len(gamesRoles) == len(games) and len(gamesRoles[index])):
                gameRole = gamesRoles[index]
            if (len(gamesIcons) == len(games) and len(gamesIcons[index])):
                gameIcon = gamesIcons[index]
            if (len(gamesColors) == len(games) and len(gamesColors[index])):
                gameColor = gamesColors[index]
            desc = desc[1:]
        
        text = ""
        if (len(desc)):
            text += " ".join(desc)
        embed = discord.Embed(description=text)
        embed.set_footer(text="For discussion about this game, please use a thread.")
        
        if (len(gameRole)):
            embed.add_field(name="Target", value=gameRole, inline=True)
        
        # Member and User return different mentions for server nicknames...
        #☺ So this :
        # field_text = ctx.message.author.mention
        # can give exclamation marks on the IDs
        # and can break comparisons of mentions when reacting
        # We need the User object
        user = self.bot.get_user(int(ctx.message.author.id))
        field_text = user.mention
        embed.add_field(name="Host", value=field_text, inline=True)
        
        author_avatar = DEFAULT_AVATAR_URL
        display_avatar = ctx.message.author.display_avatar
        if (display_avatar is not None):
            author_avatar = display_avatar.url
        embed.set_author(name=ctx.message.author.display_name,
                         icon_url=author_avatar)
        
        embed.title = "Looking for " 
        embed.title += common.indefinite_article(gameWanted)
        embed.title += " " + gameWanted + " game"
        
        if (not(len(gameIcon))):
            gameIcon = DEFAULT_AVATAR_URL
        embed.set_thumbnail(url=gameIcon)
        
        if (not(len(gameColor))):
            gameColor = ctx.message.author.colour
        embed.colour = gameColor
        
        try:
            if (len(gameRole)):
                bot_message = await ctx.send(content=gameRole)
                await bot_message.edit(content="", embed=embed)
            else:
                bot_message = await ctx.send(content="", embed=embed)
            await bot_message.add_reaction(EMOJI_JOIN)
            await bot_message.add_reaction(EMOJI_NOTIFY)
            await bot_message.add_reaction(EMOJI_CLOSE)
        except Exception as error:
            print(error)
        
        try:
            await ctx.message.delete()
        except Exception as error:
            print(error)
    
    @commands.Cog.listener(name = "on_raw_reaction_add")
    @commands.Cog.listener(name = "on_raw_reaction_remove")
    async def refresh_message_embed(self, payload):
        if int(payload.user_id) == int(self.bot.user.id):
            return False
        
        if str(payload.emoji.name) not in EMOJIS_VALID:
            return False
        
        user = self.bot.get_user(int(payload.user_id))
        channel = self.bot.get_channel(int(payload.channel_id))
        message = await channel.fetch_message(int(payload.message_id))
        if (message.author.id != self.bot.user.id):
            return False
        
        title = ""
        if (len(message.embeds)):
            title = str(message.embeds[0].title)
        if (not(title.startswith("Looking for a"))):
            return False
            
        embed = message.embeds[0]
        
        
        fields = embed.fields
        host = ""
        for field in fields:
            if (field.name == "Host"):
                host = field.value
                break
        if (not(len(message.reactions))):
            return False # Game already closed, reactions cleaned
        
        players = []
        users_to_notify = []
        for reaction in message.reactions:
            reaction_users = await reaction.users().flatten()
            if ((self.bot.user not in reaction_users) \
                and (str(reaction) in EMOJIS_VALID)):
                return False # Game already closed, reactions cleaned
            reaction_users.remove(self.bot.user)
            if str(reaction) == EMOJI_JOIN:
                players = reaction_users
            if str(reaction) == EMOJI_NOTIFY:
                users_to_notify = reaction_users

        if (str(payload.emoji.name) == EMOJI_JOIN):
            embed.clear_fields()
            number = 1
            for field in fields:
                if (field.name == "Target" or field.name == "Host"):
                    embed.add_field(name = field.name, value=field.value, inline=True)
                elif (field.name[:5] == "Guest"):
                    if (not(field.name[6:].isdigit())):
                        continue
                    if (field.value != user.mention):
                        embed.add_field(name = "Guest " + str(number), value=field.value, inline=True)
                        number += 1
            if (user in players and user.mention != host):
                embed.add_field(name="Guest " + str(number), value=user.mention, inline=True)
                for user_to_notify in users_to_notify:
                    if (user_to_notify == user):
                        continue
                    try:
                        message_to_send = "A new user (" + str(user) + ")"
                        message_to_send += " has joined your game!\n"
                        message_to_send += "Head to the LFG channel ("
                        message_to_send += channel.mention
                        message_to_send += ") of "
                        message_to_send += "**" + str(channel.guild) + "**"
                        message_to_send += " to start the discussion."
                        await user_to_notify.send(message_to_send)
                    except Exception as e:
                        print(e)
                        print("Failed to DM " + str(user_to_notify))
            try:
                await message.edit(embed=embed)
            except Exception as error:
                print(error)
                
        if (str(payload.emoji.name) == EMOJI_CLOSE and user.mention == host):
            emoji_url = payload.emoji.url
            if (not(len(emoji_url))):
                emoji_url = common.get_default_emoji_url(payload.emoji.name)
            embed.set_footer(text="Game closed/full. Sorry!", icon_url=emoji_url)
            try:
                await message.edit(embed=embed)
                await message.clear_reactions()
            except Exception as error:
                print(error)
            ## New feature to converge
            # try:
            #     thread = await message.create_thread(name="Game thread")
            #     self.threads.append(thread)
            # except Exception as e:
            #     print(e)
            # print(self.threads)
    
def setup(bot):
    config = configparser.ConfigParser()
    config.read('config/games.ini')
    bot.add_cog(matchmaking(bot, config))