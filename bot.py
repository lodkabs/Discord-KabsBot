# https://realpython.com/how-to-make-a-discord-bot-python/
import os
import random

import discord
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
LOG_ID = int(os.getenv('LOG_CHANNEL_ID'))

super_admin_role = 'Owner'
upper_admin_role = 'Managers'
base_admin_role = 'Staff'

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    g = bot.guilds[0]
    print(g.name)
    async for m in g.fetch_members():
        print(f'{m} {m.id} {m.roles}')




@bot.command(name='test', help='A test command')
async def testing(ctx):
    log_channel = bot.get_channel(LOG_ID)
    response = 'Welcome to the test screen!\nUmm...hi :)'
    await log_channel.send('Test successful')
    await ctx.send(response)


@bot.command(name='roll_dice', help='Simulates rolling dice.')
async def roll(ctx, number_of_dice: int, number_of_sides: int):
    dice = [
        str(random.choice(range(1, number_of_sides + 1)))
        for _ in range(number_of_dice)
    ]
    await ctx.send(', '.join(dice))


@bot.command(name='create-channel')
@commands.has_role(super_admin_role)
async def create_channel(ctx, channel_name='real-python'):
    guild = ctx.guild
    existing_channel = discord.utils.get(guild.channels, name=channel_name)
    if not existing_channel:
        print(f'Creating a new channel: {channel_name}')
        await guild.create_text_channel(channel_name)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.errors.CheckFailure):
        await ctx.send('You do not have the correct role for this command.')

bot.run(TOKEN)
