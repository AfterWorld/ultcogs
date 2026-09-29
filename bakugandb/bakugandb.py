"""Bakugan Anime Style card reference commands for Red."""
import io
import logging
import re
import time
import uuid

import aiohttp

import discord
from redbot.core import Config, commands

from .catalog import Catalog, normalize
from .random_deck import build_random_deck

log = logging.getLogger('red.bakugandb')
EMOJI = {'Aquos':'🌊','Pyrus':'🔥','Ventus':'🌪️','Subterra':'🪨','Haos':'✨','Darkus':'🌑'}
NONE = discord.AllowedMentions.none()
SITE = 'https://bakuganbrawl.online'
RULE_URL = 'https://docs.google.com/document/d/1vVQ81bm2AU2dJRVYsSo5uYMOILDuvN8aJ16gaNXXKyM/edit?tab=t.0'
PROFILE_RE = re.compile(r'^https://bakuganbrawl\.online/u/([a-f0-9-]{36})/?$', re.I)


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
        self.config = Config.get_conf(self, identifier=8402765193, force_registration=True)
        self.config.register_user(profile_id=None)
        self.config.register_guild(deck_posts=[], rules_auto_channel=None)
        self.rules_cooldown = {}
        self.http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=12))
        try:
            self.catalog = Catalog()
        except (OSError, ValueError) as exc:
            log.exception('BakuganDB data unavailable')
            self.catalog = None
            self.load_error = str(exc)

    async def cog_unload(self):
        await self.http.close()

    async def red_delete_data_for_user(self, *, requester, user_id):
        await self.config.user_from_id(user_id).clear()
        for guild_id, settings in (await self.config.all_guilds()).items():
            posts = settings.get('deck_posts', [])
            if any(p.get('author_id') == user_id for p in posts):
                await self.config.guild_from_id(guild_id).deck_posts.set(
                    [p for p in posts if p.get('author_id') != user_id])

    async def site_json(self, path, *, payload=None):
        try:
            async with self.http.request('POST' if payload else 'GET', SITE + path, json=payload) as response:
                response.raise_for_status()
                return await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as exc:
            log.warning('Bakugan Brawl request failed: %s', exc)
            return None

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

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def brules(self, ctx, *, topic: str = ''):
        """Show rule topics or a source-linked rule summary."""
        if not await self.ready(ctx):
            return
        entries = self.catalog.rules.get('rules', [])
        if not topic:
            await ctx.send('Rule topics: ' + ', '.join(e['topic'] for e in entries)
                           + f'\nFull rules: {RULE_URL}', allowed_mentions=NONE)
            return
        key = normalize(topic)
        matches = [e for e in entries if key in normalize(e['topic'])]
        if not matches:
            await ctx.send(f'No matching rule topic. Use `{ctx.clean_prefix}brules` for the list.', allowed_mentions=NONE)
            return
        entry = matches[0]
        embed = discord.Embed(title=entry['topic'], description=entry['text'], colour=discord.Colour.blue(), url=RULE_URL)
        embed.set_footer(text='Post-New Vestroia Rules · ' + str(entry.get('page', entry.get('pages', '?'))))
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def brulesauto(self, ctx, enabled: bool):
        """Enable or disable rule-question replies in this channel."""
        await self.config.guild(ctx.guild).rules_auto_channel.set(ctx.channel.id if enabled else None)
        await ctx.send('Rule question replies ' + ('enabled here.' if enabled else 'disabled.'))

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.guild or message.author.bot or not self.catalog:
            return
        channel = await self.config.guild(message.guild).rules_auto_channel()
        if message.channel.id != channel or not re.search(r'\b(rules?|rulebook)\b', message.content, re.I):
            return
        if '?' not in message.content and not re.search(r'\b(how|where|what|can|does)\b', message.content, re.I):
            return
        now = time.monotonic()
        if now - self.rules_cooldown.get(channel, 0) < 300:
            return
        self.rules_cooldown[channel] = now
        try:
            await message.channel.send(f'Rules reference: {RULE_URL} · Use `brules <topic>` for a topic summary.', allowed_mentions=NONE)
        except discord.HTTPException:
            log.debug('Could not post rules reference in channel %s', channel)

    @commands.command()
    async def blinkprofile(self, ctx, url: str):
        """Link your public Bakugan Brawl profile URL to your Discord account."""
        match = PROFILE_RE.fullmatch(url)
        if not match:
            await ctx.send('Use your public profile URL: `https://bakuganbrawl.online/u/<profile-id>`.')
            return
        data = await self.site_json('/api/profile/public', payload={'userId': match.group(1)})
        if not isinstance(data, dict) or not isinstance(data.get('profile'), dict):
            await ctx.send('Could not verify that public profile right now. Try again later.')
            return
        await self.config.user(ctx.author).profile_id.set(match.group(1))
        await ctx.send('Saved public profile reference (ownership is not verified): ' + str(data['profile'].get('display_name') or data['profile'].get('username') or 'Brawler')[:80], allowed_mentions=NONE)

    @commands.command()
    async def bunlinkprofile(self, ctx):
        """Remove your linked public profile."""
        await self.config.user(ctx.author).profile_id.set(None)
        await ctx.send('Public profile link removed.')

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def bstats(self, ctx, member: discord.Member = None):
        """Show linked public Bakugan Brawl stats for yourself or a member."""
        target = member or ctx.author
        profile_id = await self.config.user(target).profile_id()
        if not profile_id:
            await ctx.send(f'No public profile linked. Use `{ctx.clean_prefix}blinkprofile <profile URL>` first.')
            return
        data = await self.site_json('/api/profile/public', payload={'userId': profile_id})
        if not isinstance(data, dict) or not isinstance(data.get('stats'), dict):
            await ctx.send('Profile stats are unavailable right now.')
            return
        stats = data['stats']
        profile = data.get('profile') or {}
        wins, losses = stats.get('wins', 0), stats.get('losses', 0)
        embed = discord.Embed(title=str(profile.get('display_name') or profile.get('username') or target.display_name)[:200],
                              url=f'{SITE}/u/{profile_id}', colour=discord.Colour.blue())
        embed.add_field(name='Wins / Losses', value=f'{wins} / {losses}')
        embed.add_field(name='1v1 / 2v2 matches', value=f"{stats.get('matches_1v1', '?')} / {stats.get('matches_2v2', '?')}")
        embed.add_field(name='Surrenders', value=str(stats.get('surrenders', '?')))
        embed.set_footer(text='Public site stats · Discord link does not verify account ownership')
        await ctx.send(embed=embed)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def bleaderboard(self, ctx):
        """Show the site's current public wins leaderboard."""
        rows = await self.site_json('/api/ranking')
        if not isinstance(rows, list):
            await ctx.send('The public leaderboard is unavailable right now.')
            return
        lines = [f"{i}. {discord.utils.escape_markdown(str(p.get('display_name') or p.get('username') or 'Brawler'))[:70]} — {p.get('wins', 0)}W / {p.get('losses', 0)}L"
                 for i, p in enumerate(rows[:10], 1) if isinstance(p, dict)]
        embed = discord.Embed(title='Bakugan Brawl leaderboard', description='\n'.join(lines) or 'No ranked players yet.', colour=discord.Colour.blue(), url=SITE)
        embed.set_footer(text='Live public ranking · wins order')
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    async def bdeckshare(self, ctx, *, title: str):
        """Post a share-deck image attached to your command and list it publicly."""
        if not ctx.message.attachments:
            await ctx.send(f'Attach the deck image from the site to your `{ctx.clean_prefix}bdeckshare My Deck` message.')
            return
        attachment = ctx.message.attachments[0]
        if not (attachment.content_type or '').startswith('image/') or attachment.size > 8_000_000:
            await ctx.send('Attach an image under 8 MB.')
            return
        title = title.strip()[:80]
        if not title:
            await ctx.send('Give the deck a name.')
            return
        suffix = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif'}.get(attachment.content_type)
        if not suffix:
            await ctx.send('Use a PNG, JPG, WebP or GIF image.')
            return
        try:
            file = discord.File(io.BytesIO(await attachment.read()), filename=f'deck.{suffix}')
        except discord.HTTPException:
            await ctx.send('Could not read that image. Try attaching it again.')
            return
        embed = discord.Embed(title=title, description=f'Shared by {ctx.author.display_name}', colour=discord.Colour.blue())
        embed.set_image(url=f'attachment://deck.{suffix}')
        sent = await ctx.send(embed=embed, file=file, allowed_mentions=NONE)
        entry = {'id': str(uuid.uuid4())[:8], 'title': title, 'author_id': ctx.author.id,
                 'channel_id': ctx.channel.id, 'message_id': sent.id}
        async with self.config.guild(ctx.guild).deck_posts() as posts:
            posts.append(entry)
            del posts[:-100]
        await ctx.send(f"Saved to public deck list as `{entry['id']}`. Use `{ctx.clean_prefix}bdecks` to browse.")

    @commands.command()
    @commands.guild_only()
    async def bdecks(self, ctx, page: int = 1):
        """List shared decks in this server."""
        posts = list(reversed(await self.config.guild(ctx.guild).deck_posts()))
        max_page = max(1, (len(posts) + 7) // 8)
        if page < 1 or page > max_page:
            await ctx.send(f'Choose a page from 1 to {max_page}.')
            return
        lines = [f"`{p['id']}` **{discord.utils.escape_markdown(p['title'])}** — https://discord.com/channels/{ctx.guild.id}/{p['channel_id']}/{p['message_id']}"
                 for p in posts[(page-1)*8:page*8]]
        await ctx.send('Public decks (' + str(page) + '/' + str(max_page) + '):\n' + ('\n'.join(lines) if lines else f'None yet. Attach a site deck image with `{ctx.clean_prefix}bdeckshare <title>`.')[:1800], allowed_mentions=NONE)

    @commands.command()
    @commands.guild_only()
    async def bdeckremove(self, ctx, deck_id: str):
        """Remove your listing; managers can remove any listing."""
        async with self.config.guild(ctx.guild).deck_posts() as posts:
            post = next((p for p in posts if p['id'] == deck_id), None)
            if not post:
                await ctx.send('Deck listing not found.')
                return
            if post['author_id'] != ctx.author.id and not ctx.author.guild_permissions.manage_messages:
                await ctx.send('Only its author or a moderator can remove that listing.')
                return
            posts.remove(post)
        await ctx.send('Deck listing removed. The original shared message remains in its channel.')
