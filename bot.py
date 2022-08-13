# https://realpython.com/how-to-make-a-discord-bot-python/
import os

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

print(str(datetime.datetime.now()) + '\n')

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
channel_id = {}
for c in ['log', 'test', 'drink']:
    channel_id[c] = int(os.getenv(c.upper() + '_CHANNEL_ID'))

super_admin_role = 'Owner'
upper_admin_role = 'Managers'
base_admin_role = 'Staff'

upper_admins = {upper_admin_role, super_admin_role}
all_admins = {base_admin_role, upper_admin_role, super_admin_role}

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

log_channel = bot.get_channel(channel_id['log'])


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
    hex_colour = ''

    res = requests.get(url)
    img = Image.open(BytesIO(res.content))
    h = img.height
    img.convert('RGB')

    pixel_list = []
    for x in itertools.product(range(19, 98), range(h - 80, h - 54)):
        pixel_list.append(img.getpixel(x))

    colour_count = collections.Counter(pixel_list)
    high_colour = colour_count.most_common(1)[0][0]

    ret_colour = discord.Colour.from_rgb(high_colour[0], high_colour[1], high_colour[2])

    return ret_colour

# https://stackoverflow.com/questions/64167141/how-do-i-schedule-a-function-to-run-everyday-at-a-specific-time-in-discord-py
def seconds_until(hours, minutes):
    given_time = datetime.time(hours, minutes)
    now = datetime.datetime.now()
    future_exec = datetime.datetime.combine(now, given_time)
    if (future_exec - now).days < 0:
        future_exec = datetime.datetime.combine(now + datetime.timedelta(days=1), given_time)

    return (future_exec - now).total_seconds()


def logging_in_channel(ctx, e, usage="Unexpected error"):
    logging = f"Error detected at {str(datetime.datetime.now())}:"
    logging += f"\n\tUser: {ctx.author.name}"
    logging += f"\n\tChannel: {ctx.channel.name}"

    logging += f"\n\n\tUsage: {usage}"
    logging += f"\n\tReason: {e}"

    return logging

##### Tasks #####

@tasks.loop(hours=24)
async def my_job_forever(self):
    while True:
        await asyncio.sleep(seconds_until(0, 0))
        print("See you in 24 hours from exactly now")
        log_channel = bot.get_channel(channel_id['log'])
        await log_channel.send('Test: it should be 00:00 now')
        await asyncio.sleep(60)


##### Events #####

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!\n')
    # g = bot.guilds[0]
    # print(g.name)
    # async for m in g.fetch_members():
    #     #print(f'{m} {m.id} {m.roles}')
    #     print(f'{m} {m.id}')

@bot.event
async def on_command_error(ctx, error):
    log_channel = bot.get_channel(channel_id['log'])

    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send('You do not have the correct role for this command.')
    else:
        await log_channel.send(logging_in_channel(ctx, str(error)))

    print(error)


##### Commands #####

@bot.command(name='test', help='A test command')
async def testing(ctx):
    log_channel = bot.get_channel(channel_id['log'])
    response = 'Welcome to the test screen!\nUmm...hi :)'
    await log_channel.send('Test successful')
    await ctx.send(response)

@bot.command(name='drink', help='Order a drink!')
async def order_drink(ctx, *args):
    response = ""
    em = None

    if args:
        drink_choice = " ".join(args)
        drink_rec = []

        try:
            d_c = int(drink_choice)
        except ValueError:
            for count, coffee in enumerate(coffee_list):
                similarity_ratio = SM(isjunk=None, a=drink_choice, b=coffee["drink"]).ratio()
                if similarity_ratio >= 0.5:
                    drink_rec.append((count, coffee))
        except Exception as e:
            await log_channel.send(logging_in_channel(ctx, e, "Drink choice validation"))
            response = "Umm, there is something wrong with the till, could you let a manager please?"
        else:
            if 0 < d_c <= len(coffee_list):
                try:
                    drink_rec.append((d_c - 1, coffee_list[d_c - 1]))
                except IndexError:
                    response = "Sorry, we don't have that many drinks!"
                except Exception as e:
                    await log_channel.send(logging_in_channel(ctx, e, "Coffee by number"))
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
            elif drink_len > 1:
                response = "My apologies, is the order one of the following?"
                for d in drink_rec:
                    response += f"\n\t{d[0] + 1}) {d[1]['drink']}"
            else:
                response = "That drink is unavailable"

    else:
        response = "Welcome! What drink would you like today?"

    await ctx.send(response, embed=em)


bot.run(TOKEN)
