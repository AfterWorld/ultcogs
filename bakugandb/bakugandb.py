"""Bakugan Anime Style card reference commands for Red."""
import logging

import discord
from redbot.core import commands

from .catalog import Catalog, normalize
from .random_deck import build_random_deck

log = logging.getLogger('red.bakugandb')
EMOJI = {'Aquos':'🌊','Pyrus':'🔥','Ventus':'🌪️','Subterra':'🪨','Haos':'✨','Darkus':'🌑'}
NONE = discord.AllowedMentions.none()


def label_attributes(items):
    return ', '.join(f'{EMOJI.get(a, "")} {a}'.strip() for a in items) or 'Unknown'


def card_embed(card, image=None):
    embed = discord.Embed(title=card['name'].upper(), colour=discord.Colour.blue())
    embed.add_field(name='Type', value=card['type'], inline=True)
    embed.add_field(name='Bakugan', value=', '.join(card['bakugan']) or 'Unknown', inline=True)
    embed.add_field(name='Attributes', value=label_attributes(card['attributes']), inline=False)
    if card['requires']:
        embed.add_field(name='Requires', value=', '.join(card['requires']), inline=False)
    effect = card.get('effect') or 'Unknown / pending source verification.'
    embed.add_field(name='Effect', value=effect[:1024], inline=False)
    if card.get('unresolved_requires'):
        embed.add_field(name='Unresolved prerequisite', value=', '.join(card['unresolved_requires'])[:1024], inline=False)
    if image:
        embed.set_image(url=image['url'])
    source = card.get('source') or {}
    embed.set_footer(text=f"{source.get('document', 'Unknown source')} · {card.get('status', 'unknown')}" + (f" · p. {source['page']}" if source.get('page') else '') + (' · Image: Bakugan Brawl Online' if image else ''))
    return embed


class Results(discord.ui.View):
    def __init__(self, owner, cards, title):
        super().__init__(timeout=180)
        self.owner, self.cards, self.title, self.page = owner, cards, title, 0
        self.message = None
        self.refresh()

    def refresh(self):
        self.previous.disabled = self.page == 0
        self.next.disabled = (self.page + 1) * 8 >= len(self.cards)

    def embed(self):
        page = self.cards[self.page*8:self.page*8+8]
        embed = discord.Embed(title=self.title, description='\n'.join(f"**{self.page*8+i+1}. {discord.utils.escape_markdown(c['name'])}** — {c['type']}" for i,c in enumerate(page)), colour=discord.Colour.blue())
        embed.set_footer(text=f'Page {self.page+1}/{(len(self.cards)+7)//8} · {len(self.cards)} matches · use [p]bcard <name>')
        return embed

    async def interaction_check(self, interaction):
        if interaction.user.id != self.owner:
            await interaction.response.send_message('These controls belong to the person who searched. Run your own search.', ephemeral=True)
            return False
        return True

    @discord.ui.button(label='Previous', style=discord.ButtonStyle.secondary)
    async def previous(self, interaction, button):
        self.page -= 1
        self.refresh()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    @discord.ui.button(label='Next', style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        self.page += 1
        self.refresh()
        await interaction.response.edit_message(embed=self.embed(), view=self)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass


class BakuganDB(commands.Cog):
    """Search Bakugan Anime Style cards, gates, fusions and Bakugan profiles."""
    def __init__(self, bot):
        self.bot = bot
        try:
            self.catalog = Catalog()
        except (OSError, ValueError) as exc:
            log.exception('BakuganDB data unavailable')
            self.catalog = None
            self.load_error = str(exc)

    async def ready(self, ctx):
        if self.catalog:
            return True
        await ctx.send('BakuganDB data is unavailable. Ask the bot owner to check the cog logs.')
        return False

    async def list_results(self, ctx, cards, title):
        if not cards:
            await ctx.send('No matches. Try a card name, attribute, Bakugan or card type.')
        elif len(cards) == 1:
            await ctx.send(embed=card_embed(cards[0], self.catalog.images.get(cards[0]['name'])))
        else:
            view = Results(ctx.author.id, cards, title)
            view.message = await ctx.send(embed=view.embed(), view=view, allowed_mentions=NONE)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def bcard(self, ctx, *, name: str):
        """Show a card by name, including partial names."""
        if not await self.ready(ctx): return
        card = self.catalog.lookup(name)
        if card:
            await ctx.send(embed=card_embed(card, self.catalog.images.get(card['name'])))
            return
        partial = [c for c in self.catalog.cards if normalize(name) in normalize(c['name'])]
        if partial:
            return await self.list_results(ctx, partial, 'Matching cards')
        suggestions = self.catalog.suggest(name)
        await ctx.send('Card not found.' + (' Did you mean: ' + ', '.join(suggestions) + '?' if suggestions else ''), allowed_mentions=NONE)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def bcards(self, ctx, *, query: str = ''):
        """Filter abilities by type, attribute, Bakugan and name (combine words)."""
        if await self.ready(ctx): await self.list_results(ctx, self.catalog.filter(query), 'Ability cards' + (': ' + query if query else ''))

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def bsearch(self, ctx, *, text: str):
        """Search card names, text, types and fusion prerequisites."""
        if await self.ready(ctx): await self.list_results(ctx, self.catalog.search(text), 'Search: ' + text[:150])

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def bgates(self, ctx, *, query: str = ''):
        """Filter gate cards by type, name and attribute."""
        if await self.ready(ctx): await self.list_results(ctx, self.catalog.filter(query, gates=True), 'Gate cards' + (': ' + query if query else ''))

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def bfusion(self, ctx, *, name: str):
        """Find fusion cards by their name or prerequisite."""
        if await self.ready(ctx): await self.list_results(ctx, self.catalog.fusion(name), 'Fusion chain: ' + name[:150])

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def bbakugan(self, ctx, *, name: str):
        """Show a Bakugan's known profile and related cards."""
        if not await self.ready(ctx): return
        profile = self.catalog.lookup(name, self.catalog.bakugan)
        if not profile:
            await ctx.send('Bakugan not found.' + (' Try: ' + ', '.join(self.catalog.suggest(name, self.catalog.bakugan)) if self.catalog.suggest(name, self.catalog.bakugan) else ''), allowed_mentions=NONE)
            return
        cards = [c for c in self.catalog.cards if any(normalize(profile['name']) == normalize(n) for n in c['bakugan'])]
        embed = discord.Embed(title=profile['name'], description=profile['classification'], colour=discord.Colour.blue())
        embed.add_field(name='Base G-Power', value=str(profile['base_g_power']) if profile['base_g_power'] is not None else 'Unknown')
        embed.add_field(name='Attributes', value=label_attributes(profile['attributes']), inline=False)
        if profile['traits']: embed.add_field(name='Traits / source notes', value='\n'.join(profile['traits'])[:1024], inline=False)
        for kind in ('Normal Ability','Signature Ability','Fusion Ability','Gate'):
            names = [c['name'] for c in cards if kind in c['type']]
            if names: embed.add_field(name=kind+'s', value=', '.join(names)[:1024], inline=False)
        embed.set_footer(text='Relationships from catalog tags · unlisted details are unknown')
        await ctx.send(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def brandom(self, ctx, attribute: str = None):
        """Roll a sample deck, optionally for one attribute: [p]brandom aquos."""
        if not await self.ready(ctx):
            return
        try:
            deck = build_random_deck(self.catalog, attribute)
        except ValueError as exc:
            await ctx.send(str(exc), allowed_mentions=NONE)
            return
        embed = discord.Embed(title=f"Random {deck['attribute']} deck", colour=discord.Colour.blue())
        embed.add_field(name='Bakugan (1 Guardian, 2 Generic)', value='\n'.join(deck['bakugan']), inline=False)
        embed.add_field(name='Abilities (6 Normal)', value='\n'.join(c['name'] for c in deck['abilities']), inline=False)
        embed.add_field(name='Gates (1 Attribute, 2 Command)', value='\n'.join(c['name'] for c in deck['gates']), inline=False)
        embed.set_footer(text=deck['note'])
        await ctx.send(embed=embed)
