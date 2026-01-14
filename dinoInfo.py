import discord
from discord import Embed
from typing import List, Dict, Optional
from graphviz import Digraph

def get_dino_fact_embeds(dino: dict) -> List[Embed]:
    embeds = [Embed(
        title = dino.get('name'),
        description=dino.get('summary'),
        color=discord.Colour.greyple()
    )]

    embeds[0].set_image(url = dino.get('thumbnail'))
    # for section in dino.get('sections'):
    #     embed = Embed(title=dino['sections'][section]['title'], description=dino['sections'][section]['text'], color=discord.Colour.green())
    #     embeds.append(embed)

    return embeds