import discord
import os
import dotenv
from discord import Embed
from typing import List, Dict, Optional
from graphviz import Digraph

dotenv.load()


def get_dino_fact_embeds(dino: dict) -> List[Embed]:
    embeds = [Embed(
        title=dino.get('name'),
        description=dino.get('summary'),
        color=discord.Colour.greyple()
    ),
        Embed(
            title=f"Information",
            description=f"[Wikipedia Page]({dino.get('url')})\n\nWant to use this bot on your sever? [Here's the install link!]({os.getenv("BOT_INSTALL")})"
        )
    ]

    embeds[0].set_image(url=dino.get('thumbnail'))
    # for section in dino.get('sections'):
    #     embed = Embed(title=dino['sections'][section]['title'], description=dino['sections'][section]['text'], color=discord.Colour.green())
    #     embeds.append(embed)

    return embeds
