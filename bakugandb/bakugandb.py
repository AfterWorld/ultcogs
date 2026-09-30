"""Bakugan Anime Style card reference commands for Red."""
import asyncio
import io
import json
import logging
import re
import time
import uuid

import aiohttp

import discord
from redbot.core import Config, commands
from redbot.core.data_manager import cog_data_path

from .catalog import Catalog, normalize
from .catalog_check import check_website
from .deck_legality import validate_export
from .deck_image import render as render_deck_image
from .site_deck import DATA as SITE_CATALOG_DATA, resolve_deck, random_site_deck
from .public_decks import search_decks

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
        self.config.register_global(deck_posts=[], deck_index_migrated=False)
        self._deck_lock = asyncio.Lock()
        self.rules_cooldown = {}
        self.http = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15), trust_env=True)
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
        await self._migrate_deck_posts()
        async with self.config.deck_posts() as posts:
            for post in posts:
                if post.get('author_id') == user_id:
                    await self._remove_deck_image(post['id'])
            posts[:] = [p for p in posts if p.get('author_id') != user_id]

    def _deck_image_path(self, deck_id, suffix='png'):
        return cog_data_path(self) / 'shared_images' / f'{deck_id}.{suffix}'

    async def _save_deck_image(self, deck_id, suffix, data):
        path = self._deck_image_path(deck_id, suffix)
        def write():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        await asyncio.to_thread(write)

    async def _remove_deck_image(self, deck_id):
        for suffix in ('png', 'jpg', 'webp', 'gif'):
            await asyncio.to_thread(self._deck_image_path(deck_id, suffix).unlink, missing_ok=True)

    async def _send_deck_image(self, ctx, post, picture, suffix, export=None):
        filename = f'deck.{suffix}'
        embed = discord.Embed(title=post['title'], description=f"Shared by {post.get('author_name', 'a brawler')}", colour=discord.Colour.blue())
        embed.set_image(url='attachment://' + filename)
        files = [discord.File(io.BytesIO(picture), filename=filename)]
        if export:
            files.append(discord.File(io.BytesIO((json.dumps(export, indent=2) + '\n').encode('utf-8')),
                                      filename=f"shared-{post['id']}.deck.json"))
        await ctx.send(embed=embed, files=files, allowed_mentions=NONE)

    async def _migrate_deck_posts(self):
        """Move old per-server listings to the bot-wide index once."""
        async with self._deck_lock:
            if await self.config.deck_index_migrated():
                return
            posts = await self.config.deck_posts()
            seen = {p['id'] for p in posts}
            for guild_id, settings in (await self.config.all_guilds()).items():
                for post in settings.get('deck_posts', []):
                    if post.get('id') not in seen:
                        posts.append({**post, 'guild_id': int(guild_id)})
                        seen.add(post['id'])
            await self.config.deck_posts.set(posts)
            for guild_id, settings in (await self.config.all_guilds()).items():
                if settings.get('deck_posts'):
                    await self.config.guild_from_id(guild_id).deck_posts.set([])
            await self.config.deck_index_migrated.set(True)

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

    @commands.command()
    @commands.is_owner()
    @commands.bot_has_permissions(attach_files=True)
    async def bcatalogcheck(self, ctx):
        """Compare our snapshot with the website without changing any data."""
        try:
            report = await check_website(self.http)
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError, ValueError, KeyError) as exc:
            log.warning('Catalog drift check failed: %s', exc)
            await ctx.send('Could not read the website catalog. Check the bot logs and retry later.')
            return
        changes = report['changes']
        counts = report['counts']
        summary = f"Snapshot {report['snapshot']} · Website: {counts['bakugan']} Bakugan, {counts['abilities']} Abilities, {counts['gates']} Gates."
        if not changes:
            await ctx.send(summary + ' No catalog or restriction changes detected.')
        else:
            details = json.dumps(report, indent=2).encode('utf-8')
            await ctx.send(summary + f' {len(changes)} changes need review.',
                           file=discord.File(io.BytesIO(details), filename='bakugan-catalog-drift.json'))

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
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    async def brandom(self, ctx, *, options: str = ''):
        """Roll a deck: [p]brandom [attribute] [balanced|offense|defense|control]."""
        if not await self.ready(ctx):
            return
        try:
            terms = options.lower().split()
            if len(terms) > 2:
                raise ValueError('Use an attribute and an optional style: balanced, offense, defense or control.')
            attribute = next((term for term in terms if term in ('aquos', 'pyrus', 'ventus', 'subterra', 'haos', 'darkus')), None)
            style = next((term for term in terms if term in ('balanced', 'offense', 'defense', 'control')), 'balanced')
            if len(terms) != int(attribute is not None) + int(style in terms):
                raise ValueError('Use an attribute and an optional style: balanced, offense, defense or control.')
            deck, site_catalog, art, export = random_site_deck(attribute, style=style)
        except ValueError as exc:
            await ctx.send(str(exc), allowed_mentions=NONE)
            return
        try:
            picture = await render_deck_image(deck, site_catalog, self.http, art)
            embed = discord.Embed(title=f"Random {deck['attribute']} deck", colour=discord.Colour.blue())
            embed.set_image(url='attachment://bakugan-deck.png')
            deck_file = discord.File(io.BytesIO((json.dumps(export, indent=2) + '\n').encode('utf-8')),
                                     filename=f"random-{deck['attribute'].lower()}.deck.json")
            await ctx.send(embed=embed, files=[discord.File(io.BytesIO(picture), filename='bakugan-deck.png'), deck_file])
        except (OSError, ValueError, discord.HTTPException):
            log.exception('Could not render random deck image; sending text list')
            embed = discord.Embed(title=f"Random {deck['attribute']} deck", colour=discord.Colour.blue())
            embed.add_field(name='Bakugan', value='\n'.join(deck['bakugan']), inline=False)
            embed.add_field(name='Abilities', value='\n'.join(c['name'] for c in deck['abilities']), inline=False)
            embed.add_field(name='Gates', value='\n'.join(c['name'] for c in deck['gates']), inline=False)
            embed.set_footer(text=deck['note'])
            deck_file = discord.File(io.BytesIO((json.dumps(export, indent=2) + '\n').encode('utf-8')),
                                     filename=f"random-{deck['attribute'].lower()}.deck.json")
            await ctx.send(embed=embed, file=deck_file)

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
        for section in entry.get('sections', []):
            embed.add_field(name=section['heading'], value=section['text'][:1024], inline=False)
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
        if isinstance(data, dict) and data.get('error'):
            await ctx.send('The site could not find that public profile. Check the URL and try again.')
            return
        await self.config.user(ctx.author).profile_id.set(match.group(1))
        profile = data.get('profile') if isinstance(data, dict) else None
        if isinstance(profile, dict):
            await ctx.send('Saved public profile reference (ownership is not verified): ' + str(profile.get('display_name') or profile.get('username') or 'Brawler')[:80], allowed_mentions=NONE)
        else:
            await ctx.send('Saved your profile URL. The site lookup is unavailable from this bot right now, so the profile and its stats could not be verified. Try `bstats` later.', allowed_mentions=NONE)

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
        """Share a website JSON export or its downloaded deck image."""
        if not ctx.message.attachments:
            await ctx.send(f'Attach the website `.json` export or Share deck image to `{ctx.clean_prefix}bdeckshare My Deck`.')
            return
        attachment = ctx.message.attachments[0]
        title = title.strip()[:80]
        if not title:
            await ctx.send('Give the deck a name.')
            return
        website_deck = attachment.filename.lower().endswith('.json')
        if website_deck:
            if attachment.size > 1_000_000:
                await ctx.send('The website deck export must be under 1 MB.')
                return
            try:
                raw = await attachment.read()
                deck, site_catalog, art = resolve_deck(raw)
                original = json.loads(raw)
                export = {'version': 1, 'name': title, 'description': '',
                          'bakugans': original['bakugans'], 'abilities': original['abilities'],
                          'gates': original['gates']}
                picture = await render_deck_image(deck, site_catalog, self.http, art)
            except (ValueError, OSError, discord.HTTPException) as exc:
                await ctx.send(f'Could not render that website deck: {str(exc)[:300]}', allowed_mentions=NONE)
                return
            file = discord.File(io.BytesIO(picture), filename='deck.png')
            suffix = 'png'
        else:
            if attachment.size > 8_000_000:
                await ctx.send('Attach an image under 8 MB.')
                return
            suffix = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/webp': 'webp', 'image/gif': 'gif'}.get(attachment.content_type)
            if not suffix:
                await ctx.send('Use a website `.json` export or a PNG, JPG, WebP or GIF image.')
                return
            try:
                picture = await attachment.read()
                file = discord.File(io.BytesIO(picture), filename=f'deck.{suffix}')
            except discord.HTTPException:
                await ctx.send('Could not read that image. Try attaching it again.')
                return
        embed = discord.Embed(title=title, description=f'Shared by {ctx.author.display_name}', colour=discord.Colour.blue())
        embed.set_image(url=f'attachment://deck.{suffix}')
        if website_deck:
            for heading, entries in (('Bakugan', deck['bakugan']), ('Abilities', [c['name'] for c in deck['abilities']]), ('Gates', [c['name'] for c in deck['gates']])):
                embed.add_field(name=heading, value=', '.join(entries)[:1024], inline=False)
            embed.set_footer(text=deck['note'])
        sent = await ctx.send(embed=embed, file=file, allowed_mentions=NONE)
        entry = {'id': uuid.uuid4().hex[:12], 'title': title, 'author_id': ctx.author.id,
                 'author_name': ctx.author.display_name[:80], 'guild_id': ctx.guild.id,
                 'channel_id': ctx.channel.id, 'message_id': sent.id,
                 'export': export if website_deck else None,
                 'attribute': deck['attribute'].lower() if website_deck else None,
                 'search_text': ' '.join(deck['bakugan'] + [c['name'] for c in deck['abilities'] + deck['gates']])[:1000] if website_deck else ''}
        try:
            await self._save_deck_image(entry['id'], suffix, picture)
            entry['image_suffix'] = suffix
        except OSError:
            log.exception('Could not persist shared deck image %s', entry['id'])
        await self._migrate_deck_posts()
        async with self.config.deck_posts() as posts:
            posts.append(entry)
        hint = (f' Attach your website export to `{ctx.clean_prefix}bdeckattach {entry["id"]}` to add a downloadable JSON.'
                if not website_deck else '')
        await ctx.send(f"Saved to the public deck list as `{entry['id']}`. Use `{ctx.clean_prefix}bdecks` from any server to browse.{hint}")

    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    async def bdeckattach(self, ctx, deck_id: str):
        """Add a website JSON export to your existing public deck listing."""
        await self._migrate_deck_posts()
        deck_id = deck_id.lower()
        post = next((p for p in await self.config.deck_posts() if p['id'] == deck_id), None)
        if not post or post.get('author_id') != ctx.author.id:
            await ctx.send('Find your deck ID with `bdecks`, then attach its website export as its author.')
            return
        attachment = next((a for a in ctx.message.attachments if a.filename.lower().endswith('.json')), None)
        if not attachment or attachment.size > 1_000_000:
            await ctx.send(f'Attach the website `.json` file under 1 MB to `{ctx.clean_prefix}bdeckattach {deck_id}`.')
            return
        try:
            raw = await attachment.read()
            deck, catalog, art = resolve_deck(raw)
            original = json.loads(raw)
            export = {'version': 1, 'name': post['title'], 'description': original.get('description', ''),
                      'bakugans': original['bakugans'], 'abilities': original['abilities'], 'gates': original['gates']}
            picture = await render_deck_image(deck, catalog, self.http, art)
            await self._save_deck_image(deck_id, 'png', picture)
        except (OSError, ValueError, discord.HTTPException) as exc:
            await ctx.send(f'Could not add that website export: {str(exc)[:300]}', allowed_mentions=NONE)
            return
        async with self.config.deck_posts() as posts:
            current = next((p for p in posts if p['id'] == deck_id and p.get('author_id') == ctx.author.id), None)
            if current is None:
                await self._remove_deck_image(deck_id)
                await ctx.send('That deck was removed. Share it again to create a new listing.')
                return
            current.update(export=export, image_suffix='png', attribute=deck['attribute'].lower(),
                           search_text=' '.join(deck['bakugan'] + [c['name'] for c in deck['abilities'] + deck['gates']])[:1000])
        await ctx.send(f'Deck `{deck_id}` now shows its image and downloadable JSON from any server. Use `{ctx.clean_prefix}bdeckview {deck_id}`.')

    @commands.command()
    @commands.bot_has_permissions(embed_links=True)
    async def bdeckcheck(self, ctx):
        """Check an attached website JSON export against the captured game rules."""
        attachment = next((a for a in ctx.message.attachments if a.filename.lower().endswith('.json')), None)
        if not attachment or attachment.size > 1_000_000:
            await ctx.send(f'Attach a website `.json` file under 1 MB to `{ctx.clean_prefix}bdeckcheck`.')
            return
        try:
            exported = json.loads(await attachment.read())
            with SITE_CATALOG_DATA.open(encoding='utf-8') as stream:
                site = json.load(stream)
            issues = validate_export(exported, site)
        except (UnicodeDecodeError, ValueError, OSError):
            await ctx.send('That file is not a readable website deck JSON export.')
            return
        embed = discord.Embed(title='Deck check', colour=discord.Colour.red() if issues else discord.Colour.green())
        embed.description = ('\n'.join(f'• {discord.utils.escape_markdown(issue)}' for issue in issues[:20])[:3900]
                             + (f'\n…and {len(issues)-20} more.' if len(issues) > 20 else '')) if issues else 'No violations found in the captured rules and website restrictions.'
        embed.set_footer(text='Snapshot 2026-09-29 · import on the website for its current validation')
        await ctx.send(embed=embed, allowed_mentions=NONE)

    @commands.command()
    async def bdecks(self, ctx, *, filters: str = ''):
        """Search public decks: [p]bdecks [terms] [author:name] [page:2]."""
        await self._migrate_deck_posts()
        try:
            posts, page = search_decks(await self.config.deck_posts(), filters)
        except ValueError as exc:
            await ctx.send(str(exc))
            return
        max_page = max(1, (len(posts) + 7) // 8)
        if page < 1 or page > max_page:
            await ctx.send(f'Choose a page from 1 to {max_page}.')
            return
        lines = [f"`{p['id']}` **{discord.utils.escape_markdown(p['title'])}** by {discord.utils.escape_markdown(p.get('author_name', 'a brawler'))} — `{ctx.clean_prefix}bdeckview {p['id']}`"
                 for p in posts[(page-1)*8:page*8]]
        await ctx.send('Public decks (' + str(page) + '/' + str(max_page) + ', ' + str(len(posts)) + ' matches):\n' + ('\n'.join(lines) if lines else f'None yet. Use `{ctx.clean_prefix}bdeckshare <title>` with a website deck export.')[:1800], allowed_mentions=NONE)

    @commands.command()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    async def bdeckview(self, ctx, deck_id: str):
        """View a public deck by ID from any server using this bot."""
        await self._migrate_deck_posts()
        post = next((p for p in await self.config.deck_posts() if p['id'] == deck_id.lower()), None)
        if not post:
            await ctx.send('Deck not found. Use `bdecks` to browse.')
            return
        link = f"https://discord.com/channels/{post['guild_id']}/{post['channel_id']}/{post['message_id']}"
        suffix = post.get('image_suffix')
        if suffix in ('png', 'jpg', 'webp', 'gif'):
            try:
                picture = await asyncio.to_thread(self._deck_image_path(post['id'], suffix).read_bytes)
                await self._send_deck_image(ctx, post, picture, suffix, post.get('export'))
                return
            except OSError:
                log.warning('Shared deck image cache missing for %s', deck_id)
            except discord.HTTPException:
                log.exception('Could not send shared deck image %s', deck_id)
        if post.get('export'):
            try:
                deck, catalog, art = resolve_deck(json.dumps(post['export']).encode())
                picture = await render_deck_image(deck, catalog, self.http, art)
                await self._send_deck_image(ctx, post, picture, 'png', post['export'])
                try:
                    await self._save_deck_image(post['id'], 'png', picture)
                    async with self.config.deck_posts() as posts:
                        for entry in posts:
                            if entry['id'] == post['id']:
                                entry['image_suffix'] = 'png'
                                break
                except OSError:
                    log.exception('Could not cache shared deck image %s', deck_id)
                return
            except (OSError, ValueError, discord.HTTPException):
                log.exception('Could not render shared deck %s', deck_id)
                deck_file = discord.File(io.BytesIO((json.dumps(post['export'], indent=2) + '\n').encode('utf-8')),
                                         filename=f"shared-{post['id']}.deck.json")
                await ctx.send('The deck image could not be rendered right now. Its website JSON is attached.', file=deck_file)
                return
        else:
            try:
                channel = self.bot.get_channel(post['channel_id']) or await self.bot.fetch_channel(post['channel_id'])
                message = await channel.fetch_message(post['message_id'])
                if message.attachments and message.attachments[0].size <= 8_000_000:
                    source = message.attachments[0]
                    suffix = source.filename.rsplit('.', 1)[-1].lower()
                    if suffix in ('png', 'jpg', 'webp', 'gif'):
                        picture = await source.read()
                        await self._send_deck_image(ctx, post, picture, suffix)
                        try:
                            await self._save_deck_image(post['id'], suffix, picture)
                            async with self.config.deck_posts() as posts:
                                for entry in posts:
                                    if entry['id'] == post['id']:
                                        entry['image_suffix'] = suffix
                                        break
                        except OSError:
                            log.exception('Could not cache shared deck image %s', deck_id)
                        return
            except (discord.HTTPException, OSError):
                log.exception('Could not retrieve shared deck image %s', deck_id)
        await ctx.send(f"**{discord.utils.escape_markdown(post['title'])}** — {link}\nThis older image-only share has no saved image or deck JSON. The author can attach the website export to `{ctx.clean_prefix}bdeckattach {post['id']}` to restore both.", allowed_mentions=NONE)

    @commands.command()
    async def bdeckremove(self, ctx, deck_id: str):
        """Remove your public listing; origin-server managers can moderate it."""
        await self._migrate_deck_posts()
        async with self.config.deck_posts() as posts:
            post = next((p for p in posts if p['id'] == deck_id), None)
            if not post:
                await ctx.send('Deck listing not found.')
                return
            can_moderate = (ctx.guild is not None and ctx.guild.id == post.get('guild_id')
                            and ctx.author.guild_permissions.manage_messages)
            if post['author_id'] != ctx.author.id and not can_moderate:
                await ctx.send('Only its author or a moderator can remove that listing.')
                return
            posts.remove(post)
        await self._remove_deck_image(deck_id)
        await ctx.send('Deck listing removed. The original shared message remains in its channel.')
