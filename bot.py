# https://realpython.com/how-to-make-a-discord-bot-python/
import os

import collections
import datetime
from io import BytesIO
import itertools
from PIL import Image
import psycopg2
import requests
import signal
import textwrap

import discord
from dotenv import load_dotenv
from discord.ext import tasks, commands

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


##### Database handling #####

db = None
cur = None

try:
    db = psycopg2.connect(
            database= os.getenv('DB_NAME'),
            user = os.getenv('DB_USERNAME'),
            password = os.getenv('DB_PASSWORD'),
            host = os.getenv('DB_HOST'),
            port = os.getenv('DB_PORT')
        )
    cur = db.cursor()
except Exception as e:
    print(e)
    print("\nCould not connect to database!\n")
else:
    print(f"Connected to {os.environ['DB_NAME']} database.\n")
finally:
    pass

def keyboardInterruptHandler(signal, frame):
    print(f"\nKeyboardInterrupt (ID: {signal}) has been caught.\n")
    if db and cur:
        cur.close()
        db.close()
        print(f"Disconnected from {os.environ['DB_NAME']} database.\n")
    exit(0)

signal.signal(signal.SIGINT, keyboardInterruptHandler)


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
    img.convert('RGB')

    pixel_list = []
    for x in itertools.product(range(19, 98), range(34, 61)):
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
    g = bot.guilds[0]
    print(g.name)
    async for m in g.fetch_members():
        #print(f'{m} {m.id} {m.roles}')
        print(f'{m} {m.id}')

@bot.event
async def on_member_join(member):
    global db, cur

    if db:
        sql = f"""INSERT INTO discord_user (discord_user_id, discord_user_name)
                  VALUES ('{member.id}', '{member}');"""
        
        cur.execute(sql)
        db.commit()

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send('You do not have the correct role for this command.')

    print(error)


##### Commands #####

@bot.command(name='test', help='A test command')
async def testing(ctx):
    log_channel = bot.get_channel(channel_id['log'])
    response = 'Welcome to the test screen!\nUmm...hi :)'
    await log_channel.send('Test successful')
    await ctx.send(response)

@bot.command(name='drink', help='Order a drink!')
async def order_drink(ctx, drink_choice):
    global db, cur

    sql = ''
    try:
        d_c = int(drink_choice)
    except ValueError:
        sql = f"""SELECT * FROM coffee WHERE
                  LOWER(REPLACE(coffee_name, ' ', '')) LIKE
                  LOWER('{drink_choice}%');"""
    else:
        sql = f"SELECT * FROM coffee WHERE coffee_id={d_c};"
    finally:
        pass

    cur.execute(sql)
    drink_rec = cur.fetchall()
    drink_len = len(drink_rec)

    e = None
    if drink_len == 1:
        e = discord.Embed(
                title = drink_rec[0][1],
                description = textwrap.fill(drink_rec[0][4], 23),
                color = drink_common_colour(drink_rec[0][2])
                )
        e.set_image(url = drink_rec[0][2])
        response = f"Here is your drink:"
    elif drink_len > 1:
        response = "My apologies, is the order one of the following?"
        for d in drink_rec:
            response += f"\n{d[0]} {d[1]}"
        #await ctx.send(response)
    else:
        response = "That drink is unavailable"

    await ctx.send(response, embed=e)


bot.run(TOKEN)
