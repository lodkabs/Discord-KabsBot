# https://realpython.com/how-to-make-a-discord-bot-python/
import os

import collections
from datetime import datetime
from difflib import SequenceMatcher as SM
from io import BytesIO
import itertools
from PIL import Image
import requests
import textwrap
import time

import discord
from dotenv import load_dotenv
from discord.ext import tasks, commands
from twitchAPI.twitch import Twitch

from coffee_list import coffee_list

print(str(datetime.now()) + "\n")

load_dotenv()

super_admin_role = "Owner"
upper_admin_role = "Managers"
base_admin_role = "Staff"

upper_admins = {upper_admin_role, super_admin_role}
all_admins = {base_admin_role, upper_admin_role, super_admin_role}

intents = discord.Intents.all()
intents.members = True
intents.reactions = True
intents.messages = True
help_command = commands.DefaultHelpCommand(no_category = 'Commands')
bot = commands.Bot(command_prefix="!", intents=intents, help_command=help_command)

channel_ids = {}
channels = {}
channel_names = {}
for c in ["log", "delete", "test", "drink", "clip"]:
    channel_ids[c] = int(os.getenv(c.upper() + "_CHANNEL_ID"))

customers_role_id = int(os.getenv("CUSTOMERS_ROLE_ID"))
kabs_go_live_id = int(os.getenv("KABS_GO_LIVE_ID"))
events_role_id = int(os.getenv("EVENTS_ROLE_ID"))
announce_role_id = int(os.getenv("ANNOUNCE_ROLE_ID"))
doopu_go_live_id = int(os.getenv("DOOPU_GO_LIVE_ID"))

notif_role_vote_id = int(os.getenv("NOTIF_ROLE_VOTE_ID"))

daily_users = {}
test_users = {}
test_delay = 7

twitch = Twitch(os.environ['CLIENT_ID'], os.environ['CLIENT_SECRET'])

##### Functions #####

def check_admin(ctx):
    ret = False
    user_roles = {str(role) for role in ctx.message.author.roles}

    if user_roles.intersection(all_admins):
        ret = True

    return ret

def check_upper_admin(ctx):
    ret = False
    user_roles = {str(role) for role in ctx.message.author.roles}

    if user_roles.intersection(upper_admins):
        ret = True

    return ret

def drink_common_colour(url):
    hex_colour = ""

    res = requests.get(url)
    img = Image.open(BytesIO(res.content))
    h = img.height
    img.convert("RGB")

    pixel_list = []
    for x in itertools.product(range(19, 98), range(h - 80, h - 54)):
        pixel_list.append(img.getpixel(x))

    colour_count = collections.Counter(pixel_list)
    high_colour = colour_count.most_common(1)[0][0]

    ret_colour = discord.Colour.from_rgb(high_colour[0], high_colour[1], high_colour[2])
    return ret_colour

def contains_twitch_clip(text):
    return ("https://clips.twitch.tv/" in text or ("https://www.twitch.tv/" and "/clip/" in text))

def clip_url_info(url):
    ret = ""
    pathinfo = ""
    comps = url.split("/")

    if comps[2] == "clips.twitch.tv" or (comps[2] == "www.twitch.tv" and comps[4] == "clip"):
        pathinfo = comps[-1]

    if pathinfo:
        clip_filters = pathinfo.split("?")
        id_comp = clip_filters[0]

        clip_dict = twitch.get_clips(clip_id=id_comp)
        clip_info = clip_dict["data"][0]
        clip_datetime = datetime.strptime(clip_info["created_at"], '%Y-%m-%dT%H:%M:%SZ')

        ret += f"Clip title: {clip_info['title']}"
        ret += f"\nClip link: <{clip_info['url']}>"
        ret += f"\nCreated on: <t:{int(time.mktime(clip_datetime.timetuple()))}>"
        ret += f"\nCreated by: {clip_info['creator_name']}"
        ret += f"\n\nStreamer: {clip_info['broadcaster_name']}"
        ret += f"\nTwitch: <https://www.twitch.tv/{clip_info['broadcaster_name']}>"

    return ret

def logging_in_channel(ctx, e, usage="Unexpected error", log_type="Error"):
    logging = "\n~~" + " " * 45 + "~~"

    logging += f"\n{log_type} detected at <t:{int(time.time())}>:"
    logging += f"\n\tUser: {ctx.author.name}"
    logging += f"\n\tChannel: {ctx.channel.name}"
    logging += f"\n\tMessage: `{ctx.message.content}`"

    logging += f"\n\n\tUsage: {usage}"
    logging += f"\n\tReason: {e}"

    return logging

##### Tasks #####


##### Events #####

@bot.event
async def on_ready():
    print(f"{bot.user.name} has connected to Discord!\n")

    await bot.wait_until_ready()
    for c in ["log", "delete", "test", "drink", "clip"]:
        channels[c] = bot.get_channel(channel_ids[c])
        channel_names[c] = channels[c].name

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send("You do not have the correct role for this command.")
    if isinstance(error, commands.errors.CommandNotFound):
        pass
    else:
        await channels["log"].send(logging_in_channel(ctx, str(error)))

    print(error)

@bot.event
async def on_member_join(member):
    customers_role = discord.utils.get(member.guild.roles, id=customers_role_id)
    await member.add_roles(customers_role)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id == notif_role_vote_id:
        emoji_name = str(payload.emoji)
        if emoji_name == "🎬":
            await payload.member.add_roles(discord.utils.get(payload.member.guild.roles, id=kabs_go_live_id))
        elif emoji_name == "🎏":
            await payload.member.add_roles(discord.utils.get(payload.member.guild.roles, id=events_role_id))
        elif emoji_name == "📣":
            await payload.member.add_roles(discord.utils.get(payload.member.guild.roles, id=announce_role_id))
        elif emoji_name == "☕":
            await payload.member.add_roles(discord.utils.get(payload.member.guild.roles, id=doopu_go_live_id))

@bot.event
async def on_raw_reaction_remove(payload):
    if payload.message_id == notif_role_vote_id:
        current_guild = bot.get_guild(payload.guild_id)
        current_member = current_guild.get_member(payload.user_id)
        emoji_name = payload.emoji.name
        if emoji_name == "🎬":
            await current_member.remove_roles(discord.utils.get(current_guild.roles, id=kabs_go_live_id))
        elif emoji_name == "🎏":
            await current_member.remove_roles(discord.utils.get(current_guild.roles, id=events_role_id))
        elif emoji_name == "📣":
            await current_member.remove_roles(discord.utils.get(current_guild.roles, id=announce_role_id))
        elif emoji_name == "☕":
            await current_member.remove_roles(discord.utils.get(current_guild.roles, id=doopu_go_live_id))

@bot.event
async def on_message(message):
    if message.author.id != bot.user.id:
        ctx = await bot.get_context(message)
        if message.channel.id in [channel_ids["clip"], channel_ids["test"]]:
            ret = ""
            for word in message.content.split():
                if contains_twitch_clip(word):
                    try:
                        info = clip_url_info(word.strip("<>"))
                    except Exception as e:
                        await channels["log"].send(logging_in_channel(ctx, e, "Clip information retrieval"))
                        continue
                    finally:
                        pass

                    if info:
                        if ret:
                            ret += "\n~~" + " " * 45 + "~~\n"
                        ret += info

            if ret:
                await message.reply(ret)

    await bot.process_commands(message)

@bot.event
async def on_message_delete(message):
    if message.channel.id in [channel_ids["clip"], channel_ids["test"]] and contains_twitch_clip(message.content):
        async for msg in message.channel.history():
            if msg.author.id == bot.user.id and msg.reference.message_id == message.id:
                new_content = "**Original post removed, links may not be server appropriate, please proceed with caution.**\n\n"
                orig_content = msg.content
                await msg.edit(content=new_content + orig_content)
                break

    ctx = await bot.get_context(message)
    await channels["delete"].send(logging_in_channel(ctx, "_Reply to this message with reason, if necessary_", "Message deletion", "Deletion"))

##### Commands #####

@bot.command(name="test", help="A test command", hidden=True)
@commands.has_any_role(upper_admins)
async def testing(ctx):
    response = "Welcome to the test screen!\nUmm...hi :)"
    await channels["log"].send("Test successful")
    await ctx.send(response)

@bot.command(name="drink",
             brief="Order a drink!",
             help=f"""Ask me for a drink at the barrista counter:\n
                      \t!drink <drink>\n
                      I'm sure we'll find a drink that works for you~
                  """
            )
async def order_drink(ctx, *args):
    response = ""
    em = None

    valid_channels = [channel_ids["drink"], channel_ids["test"]]
    user_id = ctx.message.author.id
    is_test = (ctx.channel.id == channel_ids["test"])

    if ctx.channel.id not in valid_channels:
        pass
    elif (ctx.channel.id == channel_ids["drink"] and
          user_id in daily_users and
          (datetime.now() - daily_users[user_id][0]).total_seconds() < 3600):
        if daily_users[user_id][1]:
            daily_users[user_id][1] = False
            await ctx.send(f"Drinks are free at the moment, please come back later for another drink, I hope you're enjoying your {daily_users[user_id][2]} in the meantime :)")
    elif (is_test and user_id in test_users and
          (datetime.now() - test_users[user_id][0]).total_seconds() < test_delay):
        if test_users[user_id][1]:
            test_users[user_id][1] = False
            await ctx.send(f"Test delay of {test_delay} seconds, current drink: {test_users[user_id][2]}")
    else:
        if args:
            drink_choice = " ".join(args)
            drink_rec = []

            try:
                d_c = int(drink_choice)
            except ValueError:
                for count, coffee in enumerate(coffee_list):
                    similarity_ratio = SM(isjunk=None, a=drink_choice.lower(), b=coffee["drink"].lower()).ratio()
                    if similarity_ratio == 1:
                        del drink_rec
                        drink_rec = [(count, coffee)]
                        break
                    elif similarity_ratio >= 0.6:
                        drink_rec.append((count, coffee))
                    elif "alias" in coffee:
                        for alias in coffee["alias"]:
                            alias_ratio = SM(isjunk=None, a=drink_choice.lower(), b=alias.lower()).ratio()
                            if alias_ratio >= 0.8:
                                drink_rec.append((count, coffee))
                                break

            except Exception as e:
                await channels["log"].send(logging_in_channel(ctx, e, "Drink choice validation"))
                response = "Umm, there is something wrong with the till, could you let a manager know please?"
            else:
                if is_test:
                    if 0 < d_c <= len(coffee_list):
                        try:
                            drink_rec.append((d_c - 1, coffee_list[d_c - 1]))
                        except IndexError:
                            response = "Sorry, we don't have that many drinks!"
                        except Exception as e:
                            await channels["log"].send(logging_in_channel(ctx, e, "Coffee by number"))
                            response = "Ah, there seems to be a problem with the coffee machine, could you get in touch with a manager please?"
                        finally:
                            pass
                    else:
                        response = "That one is not on the menu!"
            finally:
                pass

            if not response:
                drink_len = len(drink_rec)
                if drink_len == 1:
                    em = discord.Embed(
                            title = textwrap.fill(drink_rec[0][1]["drink"], 17),
                            description = textwrap.fill(drink_rec[0][1]["desc"], 23),
                            color = drink_common_colour(drink_rec[0][1]["pic"])
                            )
                    em.set_image(url = drink_rec[0][1]["pic"])
                    response = f"Here is your drink:"
                    if is_test:
                        test_users[ctx.message.author.id] = [datetime.now(), True, drink_rec[0][1]["drink"]]
                    else:
                        daily_users[ctx.message.author.id] = [datetime.now(), True, drink_rec[0][1]["drink"]]
                elif drink_len > 1:
                    response = "My apologies, is the order one of the following?"
                    for d in drink_rec:
                        response += "\n\t"
                        if is_test:
                            response += f"{d[0] + 1}) "
                        response += d[1]['drink']
                else:
                    response = "That drink is unavailable"
        else:
            response = "Welcome! What drink would you like today?"

        await ctx.send(response, embed=em)

TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
