"""Original deck summary graphic using verified public card artwork."""
import asyncio
import io
import json
from pathlib import Path

import aiohttp
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError

ART = json.loads((Path(__file__).parent / 'data' / 'bakugan_art.json').read_text(encoding='utf-8'))
COLORS = {'Aquos': '#26aee8', 'Pyrus': '#f27155', 'Ventus': '#6dd6b1',
          'Subterra': '#d3a465', 'Haos': '#f4d978', 'Darkus': '#b68ce3'}


def font(size, bold=False):
    path = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf' if bold else '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def draw_tile(canvas, draw, x, y, width, height, name, image_bytes, accent, subtitle=''):
    draw.rounded_rectangle((x, y, x+width, y+height), radius=18, fill='#17253b', outline='#456079', width=2)
    art_height = height - 66
    if image_bytes:
        try:
            with Image.open(io.BytesIO(image_bytes)) as original:
                original.thumbnail((width-24, art_height-18), Image.Resampling.LANCZOS)
                picture = original.convert('RGBA')
                canvas.paste(picture, (x+(width-picture.width)//2, y+10+(art_height-picture.height)//2), picture)
        except (OSError, UnidentifiedImageError, ValueError):
            image_bytes = None
    if not image_bytes:
        draw.rounded_rectangle((x+12, y+12, x+width-12, y+art_height), radius=10, fill='#22334c')
        draw.text((x+width//2, y+art_height//2), 'ART UNAVAILABLE', font=font(16, True), fill='#9db1c7', anchor='mm')
    label = name if len(name) <= 24 else name[:22] + '…'
    draw.text((x+width//2, y+height-43), label, font=font(18, True), fill='#ffffff', anchor='mm')
    if subtitle:
        draw.text((x+width//2, y+height-17), subtitle, font=font(14), fill=accent, anchor='mm')


def compose(deck, images):
    accent = COLORS[deck['attribute']]
    canvas = Image.new('RGB', (1600, 1290), '#0b1424')
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((30, 25, 1570, 1260), radius=28, fill='#101d31', outline=accent, width=4)
    draw.text((65, 68), f"{deck['attribute'].upper()}  /  RANDOM DECK", font=font(42, True), fill=accent)
    draw.text((65, 110), 'BAKUGAN ANIME STYLE  •  3 BAKUGAN  /  6 ABILITIES  /  3 GATES', font=font(20), fill='#ced9e8')
    draw.text((65, 164), 'BAKUGAN', font=font(26, True), fill='#ffffff')
    for index, name in enumerate(deck['bakugan']):
        draw_tile(canvas, draw, 65+index*505, 200, 470, 240, name, images.get(name), accent,
                  'GUARDIAN' if index == 0 else 'GENERIC')
    draw.text((65, 495), 'ABILITY CARDS', font=font(26, True), fill='#ffffff')
    for index, card in enumerate(deck['abilities']):
        draw_tile(canvas, draw, 65+index*250, 530, 225, 320, card['name'], images.get(card['name']), accent, 'NORMAL')
    draw.text((65, 910), 'GATE CARDS', font=font(26, True), fill='#ffffff')
    for index, card in enumerate(deck['gates']):
        draw_tile(canvas, draw, 65+index*505, 945, 470, 240, card['name'], images.get(card['name']), accent,
                  'ATTRIBUTE' if index == 0 else 'COMMAND')
    draw.text((65, 1220), 'Sample deck • Check current card text and legality before play', font=font(18), fill='#ced9e8')
    output = io.BytesIO()
    canvas.save(output, format='PNG', optimize=True)
    return output.getvalue()


async def render(deck, catalog, session):
    urls = {card['name']: catalog.images[card['name']]['url'] for card in deck['abilities'] + deck['gates']
            if card['name'] in catalog.images}
    urls.update({name: ART[name] for name in deck['bakugan'] if name in ART})
    semaphore = asyncio.Semaphore(4)

    async def get(name, url):
        try:
            async with semaphore, session.get(url, timeout=12) as response:
                if response.status != 200 or not response.headers.get('content-type', '').startswith('image/'):
                    return name, None
                if int(response.headers.get('content-length', '0')) > 2_000_000:
                    return name, None
                body = await response.read()
                return name, body if len(body) <= 2_000_000 else None
        except (OSError, asyncio.TimeoutError, aiohttp.ClientError):
            return name, None

    pictures = dict(await asyncio.gather(*(get(name, url) for name, url in urls.items())))
    return await asyncio.to_thread(compose, deck, pictures)
