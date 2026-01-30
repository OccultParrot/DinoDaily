"""
We need to listen to the following events:
    - leaving a guild
    - when bot is ready

We need the following commands:
    - Setup
    - Configure
    - Remove
"""

import os
import random
from datetime import datetime
from typing import Optional, Dict, List
from zoneinfo import ZoneInfo, available_timezones
import asyncio

import discord
from bs4 import BeautifulSoup
from discord.ext import tasks
from discord import Client, app_commands, Interaction, Embed
from rich import print as print
import wikipediaapi
from urllib3 import request
import dotenv

import requests

import database_utils as db
import dinoInfo
import modals_n_views as mv

dotenv.load_dotenv()

# Refresh every 5 hours
CACHE_REFRESH_INTERVAL = 60 * 60 * 5
servers = []
daily_dino: dict = {}

interesting_sections = {
    'description': ["description", "distinguishing features", "appearance"],
    'discovery': ["discovery and naming", 'discovery', 'history of discovery', 'fossil history', 'history'],
    'classification': ['classification', 'taxonomy', 'phylogeny'],
    'paleobiology': ['paleobiology', 'biology', 'life history'],
    'size': ['size', 'dimensions'],
    'diet': ['diet', 'dietary history', 'feeding', 'feeding behavior'],
    'paleoecology': ['paleoecology', 'palaeocology', 'environment', 'habitat'],
    'locomotion': ['locomotion', 'movement', 'posture and gait'],
    'growth': ['growth', 'ontogeny', 'growth and reproduction'],
    'popular_culture': ['popular culture', 'in popular culture', 'cultural significance'],
}


# --- Testing / Seeding Functions ---
def make_false_servers(number_of_servers: int):
    for i in range(number_of_servers):
        db.add_server(random.randint(1, 10000), datetime.now().time(), ZoneInfo("America/Chicago"),
                      random.randint(1, 10000))


class DinoDaily(Client):

    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)

        self.tree = self.tree = app_commands.CommandTree(self)

    async def setup_hook(self) -> None:
        print("[blue]Syncing commands globally...")
        await self.tree.sync()
        print("[green]Commands synced globally! It may take a while for commands to populate on the server.[/green]")


client = DinoDaily()


@client.event
async def on_ready():
    print(f"[green]Connected as {client.user.display_name} ({client.user.id}[/green]")
    asyncio.create_task(refresh_cache_thread())
    print("Starting daily dino loop")
    asyncio.create_task(get_daily_dino_task())
    print("Starting daily message loop")
    asyncio.create_task(send_scheduled_messages())


@client.event
async def on_guild_join(guild: discord.Guild):
    print(f"[blue]Joining guild {guild.name}!")

    embed = Embed(
        title="Thanks for having me!",
        description="Howdy! Thanks for using DinoDaily! To set me up, run `/initialize` in any channel and enter the time you want my daily messages to send!"
    )
    embed.set_footer(text="Thanks for trying out DinoDaily! - OccultParrot")

    await guild.system_channel.send(embed=embed)


# --- Guild Leave Clean Up ---
@client.event
async def on_guild_remove(guild: discord.Guild):
    print(f"[red]{client.user.display_name} has been removed from {guild.name}. Cleaning up...")
    db.remove_server(guild.id)
    print(f"[green]Server has been removed from database! Refreshing cache...\n")
    refresh_cache()


# --- Set Up Command ---
@client.tree.command(name="initialize", description="Run this to set up the bot for the first time")
@app_commands.describe(
    time="The time you want the facts displayed at. In HH:MM format!",
    timezone="The timezone the server is in.",
    channel="The channel to send the messages in.",
    ampm="Select AM or PM for the time."
)
@app_commands.choices(
    ampm=[
        app_commands.Choice(name="Morning (AM)", value="AM"),
        app_commands.Choice(name="Evening (PM)", value="PM"),
    ]
)
@app_commands.checks.has_permissions(administrator=True)
async def initialize_command(interaction: discord.Interaction, time: str, timezone: str,
                             channel: discord.TextChannel, ampm: str = None):
    await interaction.response.defer(thinking=True, ephemeral=True)

    if "am" in time.lower() or "pm" in time.lower():
        embed = Embed(
            title="An Error Occurred!",
            description=f"Select AM or PM in the \"ampm\" option, do not put it in the time selection",
            color=discord.Colour.red()
        )
        await interaction.edit_original_response(embed=embed)

    try:
        if ":" not in time:
            print("No colon")
            raise ValueError("Time is in an incorrect format!")

        split_time = time.strip().split(":")

        if len(split_time) != 2:
            print("Does not split into two")
            raise ValueError("Time is in an incorrect format!")

        hours = int(split_time[0])
        minutes = int(split_time[1])

        if ampm == "PM":
            hours += 12

        if 1 > hours > 24 or 0 > minutes > 59:
            raise ValueError("Value has to be constrained to the correct amounts")

        selected_time = datetime.fromisoformat(f"2025-01-01T{hours:02d}:{minutes:02d}").time()

        db.add_server(interaction.guild_id, selected_time, ZoneInfo(timezone), channel.id)

        embed = Embed(
            title="Successfully Added Server!",
            description=f"Your server \"{interaction.guild.name}\" has been successfully added.\n\n"
                        f"**Time:** {time}{f" {ampm}" if ampm else ""}\n"
                        f"**Timezone:** {timezone}\n"
                        f"**Channel:** {channel.mention}",
            color=discord.Colour.green()
        )
        await interaction.edit_original_response(embed=embed)

        refresh_cache()

    except ValueError as e:
        embed = Embed(
            title="An Error Occurred!",
            description=f"Please make sure that you submit the time in the correct format: HH:MM\nNot: {time}",
            color=discord.Colour.red()
        )
        print(f"Error:[red]{e}[/red]\n{hours}:{minutes}")
        await interaction.edit_original_response(embed=embed)


@initialize_command.autocomplete("timezone")
async def timezone_autocomplete(interaction: Interaction, current: str):
    filtered = [
        tz for tz in available_timezones()
        if tz.startswith(current)
    ]

    return [
        app_commands.Choice(name=tz, value=tz)
        for tz in filtered[:25]
    ]


# --- Edit Command ---
@client.tree.command(name="edit-configuration", description="Run this to edit the configuration")
@app_commands.describe(
    time="The time you want the facts displayed at. In HH:MM format!",
    timezone="The timezone the server is in.",
    channel="The channel to send the messages in."
)
@app_commands.checks.has_permissions(administrator=True)
async def edit_command(interaction: discord.Interaction, time: str = None, timezone: str = None,
                       channel: discord.TextChannel = None):
    pass


# --- Remove Command ---
@client.tree.command(name="remove-server",
                     description="Run this to disable the bot. Also occurs when kicking bot from the server.")
@app_commands.checks.has_permissions(administrator=True)
async def remove_command(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    for server in servers:
        if server.get("guild_id") == interaction.guild.id:
            db.remove_server(server.get("guild_id"))
            await interaction.edit_original_response(embed=Embed(
                title="Successfully Removed Server!",
                description=f"Server \"{server.get('guild_id')}\" has been successfully removed.",
                color=discord.Colour.green()
            ))
            print(f"Guild {server.get('id')} has been successfully removed.")
            print("Refreshing cache...")
            refresh_cache()
            return
    await interaction.edit_original_response(embed=Embed(
        title="Server not in database.",
        description=f"Could not find the guild {interaction.guild.name} in database.",
        color=discord.Colour.red()
    ))


@client.tree.command(name="send-daily",
                     description="Run this to send the dino message to the server")
@app_commands.checks.has_permissions(administrator=True)
async def send_daily(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    for server in servers:
        if server.get("guild_id") == interaction.guild.id:
            await client.get_channel(server.get("channel_id")).send(embeds=dinoInfo.get_dino_fact_embeds(daily_dino))
            await interaction.edit_original_response(embed=Embed(title="Successfully Sent Dino Message!",
                                                                 description="Check the channel to see the new message"))
            return

    await interaction.edit_original_response(embed=Embed(title="Server not set up",
                                                         description="Hmm, the server is not quite set up, try running `/initialize`!"))


# --- Error Handling ---
@initialize_command.error
@edit_command.error
@remove_command.error
@send_daily.error
async def error_handler(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("You do not have permissions to do that.", ephemeral=True)
    else:
        await interaction.response.send_message("An error has occurred!!! DM OccultParrot if you can!", ephemeral=True)
        print(error)


# --- Post Task ---
async def send_scheduled_messages():
    await client.wait_until_ready()

    while True:
        for server in servers:
            await attempt_daily_send(server)
        await asyncio.sleep(60)


async def attempt_daily_send(server):
    # Catching invalid guilds
    if server.get("guild_id", 0) not in [guild.id for guild in client.guilds]:
        print(f"Invalid guild: {server.get('guild_id')}")
        return

    if server.get("scheduled_time") and server.get("time_zone"):
        server_tz = server.get("time_zone")
        current_time_in_tz = datetime.now(server_tz).time()
        scheduled_time = server.get("scheduled_time")

        scheduled_tuple = (scheduled_time.hour, scheduled_time.minute)
        current_tuple = (current_time_in_tz.hour, current_time_in_tz.minute)

        if current_tuple == scheduled_tuple:
            try:
                channel = client.get_channel(server.get("channel_id"))
                message = await channel.send(embeds=dinoInfo.get_dino_fact_embeds(daily_dino), view=mv.DinoPostView())
                await message.create_thread(name=f"Discuss {daily_dino.get('name')}")
            except discord.errors.Forbidden as e:
                print(
                    f"[red]Bot is missing permissions in guild: [/]{client.get_guild(server.get('guild_id')).name} ({client.get_guild(server.get('guild_id')).id})")
                return
            except Exception as e:
                print(f"Something went wrong in guild: {client.get_guild(server.get('guild_id')).name}!\n{e}")

        # print(
        #     f"{client.get_guild(server.get('guild_id')).name}'s scheduled time: ({scheduled_tuple})  | Current time: {current_tuple}")


async def get_daily_dino_task():
    global daily_dino
    while True:
        daily_dino = parse_daily_dino(db.get_random_dino())

        # 1 minute -> 1 hour -> 24 hours
        await asyncio.sleep(60 * 60 * 24)


def parse_daily_dino(dino: dict) -> Optional[Dict]:
    """
    This function receives the dino info from the DB, then parses the wiki page
    :param dino:
    :return:
    """
    wiki = wikipediaapi.Wikipedia('DinoDaily (stemlertho@gmail.com)', 'en')
    page = wiki.page(dino.get('page_name'))

    soup = BeautifulSoup(requests.get(dino['href'], headers={'User-Agent': 'DinoDaily/1.0 (Testing purposes)'}).text,
                         "html.parser")
    info_box = soup.find("table", {"class": "infobox"})
    img = info_box.find_next('img')
    print(img)
    if not page.exists():
        print(f"page '{dino.get('name')}' not found")
        return None

    thumbnail_url = img.attrs['src']
    if thumbnail_url.startswith("//"):
        thumbnail_url = "https:" + thumbnail_url

    dino_data = {
        'name': page.title,
        'url': dino.get('href'),
        'summary': page.summary,
        'thumbnail': thumbnail_url,
        'sections': extract_sections(page.sections)
    }

    print(dino_data)

    return dino_data


def extract_sections(sections, level: int = 0) -> Dict[str, str]:
    extracted = {}

    for section in sections:
        section_found = False

        for category, possible_titles in interesting_sections.items():
            if any(title.lower() in section.title.lower() for title in possible_titles):
                if category not in extracted:
                    extracted[category] = {
                        'title': section.title,
                        'text': section.text,
                        'subsections': []
                    }
                section_found = True
                break

        if section.sections:
            subsections = extract_sections(section.sections, level + 1)
            if section_found and subsections:
                for key in extracted:
                    if extracted[key]['title'] == section.title:
                        extracted[key]['subsections'] = subsections
            else:
                extracted.update(subsections)

    return extracted


# --- Cache Thread Stuff ---
async def refresh_cache_thread():
    print("Starting cache refresh thread...")
    while True:
        try:
            print("Refreshing cache...")
            refresh_cache()
            print(f"[green]Cache refreshed successfully. Loaded {len(servers)} servers.[/green]\n")
        except Exception as e:
            print(f"[red]Error refreshing cache: {e}[/red]\n")

        await asyncio.sleep(CACHE_REFRESH_INTERVAL)


def refresh_cache():
    global servers
    print("Calling db.get_servers()...")
    servers = db.get_servers()
    print(f"db.get_servers() returned {len(servers)} servers\n")


if __name__ == "__main__":
    client.run(os.getenv("DISCORD_TOKEN"))
