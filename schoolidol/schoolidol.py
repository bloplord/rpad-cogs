from _collections import OrderedDict
import difflib
import json
import os
from time import time

import aiohttp
import discord
from discord.ext import commands

from __main__ import send_cmd_help, set_cog
from cogs.utils import checks
from cogs.utils.chat_formatting import pagify, box
from cogs.utils.dataIO import dataIO

from .rpadutils import Menu, char_to_emoji
from .utils.chat_formatting import *


FIRST_REQ = 'https://schoolido.lu/api/cards/?page_size=100'


class SchoolIdol:
    """SchoolIdol."""

    def __init__(self, bot):
        self.bot = bot
        self.card_data = []
        self.menu = Menu(bot)
        self.regular_emoji = char_to_emoji('r')
        self.idol_emoji = char_to_emoji('i')

    async def reload_sif(self):
        await self.bot.wait_until_ready()
        
        next_req = FIRST_REQ
        async with aiohttp.ClientSession() as session:
            while next_req:
                print(next_req)
                async with session.get(next_req) as resp:
                    raw_resp = await resp.text()
                    js_resp = json.loads(raw_resp)
                    next_req = js_resp['next']
                    self.card_data.extend(js_resp['results'])
        print('done retrieving cards: {}'.format(len(self.card_data)))
        
        
        self.id_to_card = {c['id']: c for c in self.card_data}
        name_to_card = {'{}'.format(c['idol']['name']).lower(): c for c in self.card_data}
        firstname_to_card = {c['idol']['name'].lower().split(' ')[0]: c for c in self.card_data}
        collection_name_to_card = {'{} {}'.format(c['translated_collection'], c['idol']['name']).lower(): c for c in self.card_data}
        collection_firstname_to_card = {'{} {}'.format(c['translated_collection'], c['idol']['name'].split(' ')[0]).lower(): c for c in self.card_data}
        self.names_to_card = {**firstname_to_card, **name_to_card, **collection_name_to_card, **collection_firstname_to_card}
        

    @commands.command(pass_context=True)
    async def sifid(self, ctx, *, query: str):
        """SIF query."""
        query = query.lower().strip()
        c = None
        if query.isdigit():
            c = self.id_to_card.get(int(query), None)
        else:
            c = self.names_to_card.get(query, None)
            if c is None:
                matches = difflib.get_close_matches(query, self.names_to_card.keys(), n=1, cutoff=.6)
                if len(matches):
                    c = self.names_to_card[matches[0]]
                    
        if c:
            await self.do_menu(ctx, c)
        else:
            await self.bot.say(inline('no matches'))


    async def do_menu(self, ctx, c):
        emoji_to_embed = OrderedDict()
        emoji_to_embed[self.regular_emoji] = make_card_embed(c, IMAGE_FIELD)
        emoji_to_embed[self.idol_emoji] = make_card_embed(c, IDOL_IMAGE_FIELD)
        starting_menu_emoji = self.regular_emoji
        return await self._do_menu(ctx, starting_menu_emoji, emoji_to_embed)
    
    async def _do_menu(self, ctx, starting_menu_emoji, emoji_to_embed):
        remove_emoji = self.menu.emoji['no']
        emoji_to_embed[remove_emoji] = self.menu.reaction_delete_message

        try:
            result_msg, result_embed = await self.menu.custom_menu(ctx, emoji_to_embed, starting_menu_emoji, timeout=20)
            if result_msg and result_embed:
                # Message is finished but not deleted, clear the footer
                result_embed.set_footer(text=discord.Embed.Empty)
                await self.bot.edit_message(result_msg, embed=result_embed)
        except Exception as ex:
            print('Menu failure', ex)
            

def make_card_embed(c, url_field):
    embed = discord.Embed()
    embed.title = toHeader(c)
    embed.url = get_info_url(c)
    embed.set_image(url='http:{}'.format(c[url_field]))
    embed.set_footer(text='Requester may click the reactions below to switch tabs')
    return embed
    

IMAGE_FIELD = 'transparent_image'
IDOL_IMAGE_FIELD = 'transparent_idolized_image'

def toHeader(c):
    cid = c['id']
    collection = c['translated_collection']
    name = c['idol']['name']
    if collection:
        return 'No. {} {} {}'.format(cid, collection, name)
    else:
        return 'No. {} {}'.format(cid, name)

def get_info_url(c):
    return 'https://schoolido.lu/cards/{}/'.format(c['id'])

def check_folders():
    pass

def check_files():
    pass


def setup(bot):
    check_folders()
    check_files()
    n = SchoolIdol(bot)
    bot.add_cog(n)
    bot.loop.create_task(n.reload_sif())
