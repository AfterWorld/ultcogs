"""Original procedural artwork. No downloaded assets, avatars, or franchise art."""
from functools import lru_cache
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

INK = "#111218"
PAPER = "#faf3e7"
RED = "#e63649"


def font(size):
    for name in ("DejaVuSans-Bold.ttf", "arialbd.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


def agent(draw, x, y, kind):
    """Three original geometric cartoon crew portraits, drawn at 2x resolution."""
    draw.ellipse((x-104, y-118, x+104, y+136), fill=RED if kind == 1 else PAPER)
    draw.polygon([(x-82,y+140),(x-65,y+50),(x,y+28),(x+65,y+50),(x+82,y+140)], fill=INK)
    draw.polygon([(x-40,y+53),(x,y+120),(x+40,y+53),(x,y+72)], fill=PAPER)
    draw.polygon([(x,y+76),(x-12,y+94),(x,y+135),(x+12,y+94)], fill=RED)
    draw.ellipse((x-57,y-74,x+57,y+62), fill=PAPER, outline=INK, width=7)
    if kind == 0:  # Compass-capped navigator with a red scarf.
        draw.pieslice((x-70,y-108,x+70,y-3), 180,360,fill=INK)
        draw.rounded_rectangle((x-82,y-56,x+72,y-39),8,fill=INK)
        draw.polygon([(x,y-91),(x-10,y-71),(x,y-76),(x+10,y-71)],fill=RED)
        draw.polygon([(x-55,y+41),(x+50,y+44),(x+35,y+67),(x-44,y+59)],fill=RED)
        draw.polygon([(x+35,y+59),(x+88,y+92),(x+77,y+53)],fill=RED)
        draw.line((x-31,y-8,x-13,y-16), fill=INK,width=6)
        draw.line((x+14,y-16,x+33,y-8), fill=INK,width=6)
    elif kind == 1:  # Infiltrator: angular hair and domino glasses.
        draw.polygon([(x-57,y-34),(x-73,y-69),(x-27,y-64),(x-15,y-106),
                      (x+11,y-73),(x+45,y-96),(x+62,y-33),(x+23,y-51)], fill=INK)
        draw.rounded_rectangle((x-49,y-22,x+49,y+8),9,fill=INK)
        draw.line((x-32,y-12,x-17,y-12),fill=PAPER,width=4)
        draw.line((x+17,y-12,x+32,y-12),fill=PAPER,width=4)
    else:  # White's anonymous blank mask and broad brim.
        draw.polygon([(x-61,y-50),(x-39,y-110),(x+36,y-99),(x+58,y-50)],fill=INK)
        draw.rectangle((x-53,y-65,x+52,y-51),fill=RED)
        draw.ellipse((x-88,y-54,x+88,y-32),fill=INK)
        draw.ellipse((x-33,y-9,x-20,y+2),fill=INK)
        draw.ellipse((x+20,y-9,x+33,y+2),fill=INK)
    draw.arc((x-20,y+9,x+21,y+33), 10,165,fill=INK,width=4)


@lru_cache(maxsize=8)
def render_banner(phase: str) -> bytes:
    """Bounded cache, public phase only: secret words never enter image metadata."""
    labels = {"joining": "ASSEMBLE YOUR CREW", "playing": "ONE CLUE. MANY SUSPECTS.",
              "voting": "TRUST NO DISGUISE", "guessing": "ONE LAST GUESS",
              "ended": "THE MASKS COME OFF"}
    image = Image.new("RGB", (1600, 760), INK)
    d = ImageDraw.Draw(image)
    for x in range(-700,1800,100):
        d.line((x,760,x+680,0),fill="#24252e",width=3)
    d.polygon([(0,0),(1060,0),(840,760),(0,760)],fill=PAPER)
    for x in range(40,860,32):
        for y in range(320,700,32):
            d.ellipse((x,y,x+3,y+3),fill="#d5cdc3")
    d.rounded_rectangle((52,45,456,103),12,fill=RED)
    d.text((74,55),"SECRET SEAS / DOSSIER 01",font=font(23),fill=PAPER)
    d.text((48,118),"MR. WHITE",font=font(111),fill=INK,stroke_width=1)
    d.text((56,250),labels.get(phase,labels["joining"]),font=font(31),fill=RED)
    for x,kind in ((210,0),(482,1),(754,2)):
        agent(d,x,474,kind)
    d.rounded_rectangle((51,645,825,704),12,fill=INK)
    d.text((77,661),"CIVILIAN   /   UNDERCOVER   /   MR. WHITE",font=font(25),fill=PAPER)
    # Original paper sailboat/compass insignia on the black dossier panel.
    d.ellipse((1060,98,1460,498),outline="#41424c",width=3)
    d.line((1260,75,1260,530),fill="#41424c",width=3)
    d.line((1032,298,1487,298),fill="#41424c",width=3)
    d.polygon([(1264,145),(1264,353),(1418,353)],fill=RED)
    d.polygon([(1247,190),(1110,353),(1247,353)],fill=PAPER)
    d.polygon([(1100,373),(1430,373),(1384,428),(1150,428)],fill=PAPER)
    d.text((1090,555),"BLEND IN.",font=font(49),fill=PAPER)
    d.text((1060,620),"FIND THEM OUT.",font=font(35),fill=RED)
    image = image.resize((1000,475),Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(output,format="PNG",optimize=True)
    return output.getvalue()
