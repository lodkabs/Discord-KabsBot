# https://realpython.com/how-to-make-a-discord-bot-python/
import os
from keep_alive import keep_alive

import collections
import datetime
from difflib import SequenceMatcher as SM
from io import BytesIO
import itertools
from PIL import Image
import requests
import textwrap

import discord
from dotenv import load_dotenv
from discord.ext import tasks, commands

from coffee_list import coffee_list

print(str(datetime.datetime.now()) + "\n")

load_dotenv()

super_admin_role = "Owner"
upper_admin_role = "Managers"
base_admin_role = "Staff"

upper_admins = {upper_admin_role, super_admin_role}
all_admins = {base_admin_role, upper_admin_role, super_admin_role}

intents = discord.Intents.all()
intents.members = True
help_command = commands.DefaultHelpCommand(no_category = 'Commands')
bot = commands.Bot(command_prefix="!", intents=intents, help_command=help_command)

channel_ids = {}
channels = {}
channel_names = {}
for c in ["log", "test", "drink"]:
    channel_ids[c] = int(os.getenv(c.upper() + "_CHANNEL_ID"))

daily_users = {}
test_users = {}
test_delay = 7

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

def logging_in_channel(ctx, e, usage="Unexpected error"):
    logging = "\n~~" + " " * 45 + "~~"

    logging += f"\nError detected at {str(datetime.datetime.now())}:"
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
    for c in ["log", "test", "drink"]:
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
          (datetime.datetime.now() - daily_users[user_id][0]).total_seconds() < 3600):
        if daily_users[user_id][1]:
            daily_users[user_id][1] = False
            await ctx.send(f"Drinks are free at the moment, please come back later for another drink, I hope you're enjoying your {daily_users[user_id][2]} in the meantime :)")
    elif (is_test and user_id in test_users and
          (datetime.datetime.now() - test_users[user_id][0]).total_seconds() < test_delay):
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
                    similarity_ratio = SM(isjunk=None, a=drink_choice, b=coffee["drink"]).ratio()
                    if similarity_ratio == 1:
                        del drink_rec
                        drink_rec = [(count, coffee)]
                        break
                    elif similarity_ratio >= 0.5:
                        drink_rec.append((count, coffee))
                    elif "alias" in coffee:
                        for alias in coffee["alias"]:
                            alias_ratio = SM(isjunk=None, a=drink_choice, b=alias).ratio()
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
                        test_users[ctx.message.author.id] = [datetime.datetime.now(), True, drink_rec[0][1]["drink"]]
                    else:
                        daily_users[ctx.message.author.id] = [datetime.datetime.now(), True, drink_rec[0][1]["drink"]]
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

keep_alive()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
