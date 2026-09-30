"""Candy catalogue; local photos are shipped with the cog."""

CANDIES = {
    "corn": dict(name="Candy corn", aliases=["candy corn", "brachs candy corn"], points=10, weight=30, hint="A Halloween classic with three colors.", file="01.jpg", source="Candy-Corn.jpg", author="Evan-Amos", license="Public domain"),
    "bears": dict(name="Gummy bears", aliases=["gummy bears", "gummi bears", "gummy bear", "haribo", "haribo gummy bears"], points=15, weight=25, hint="Small, chewy animals.", file="02.jpg", source="Gummy bears.jpg", author="Thomas Rosenau", license="CC BY-SA 2.5", license_url="https://creativecommons.org/licenses/by-sa/2.5/"),
    "beans": dict(name="Jelly beans", aliases=["jelly beans", "jelly bean", "jelly belly", "jellybeans"], points=20, weight=20, hint="Tiny beans in many fruity flavors.", file="03.jpg", source="JellyBellyPile.JPG", author="Brandon Dilbeck", license="CC BY-SA 3.0", license_url="https://creativecommons.org/licenses/by-sa/3.0/"),
    "kitkat": dict(name="Kit Kat", aliases=["kit kat", "kitkat"], points=30, weight=15, hint="Take a break with chocolate and wafer.", file="04.jpg", source="Kit-Kat-Split.jpg", author="Evan-Amos", license="Public domain"),
    "snickers": dict(name="Snickers", aliases=["snickers", "snicker"], points=40, weight=8, hint="Peanuts, caramel, nougat, and chocolate.", file="05.jpg", source="Snickers-broken.JPG", author="Evan-Amos", license="Public domain"),
    "chunky": dict(name="Kit Kat Chunky assortment", aliases=["kit kat chunky", "kitkat chunky", "big kit kat", "chunky kit kat"], points=75, weight=2, hint="The bigger wafer bar, in several varieties.", file="06.jpg", source="Big-Kit-Kat-Array.jpg", author="Evan-Amos", license="CC0", license_url="https://creativecommons.org/publicdomain/zero/1.0/"),
}

# ID, display name, aliases, base points, rarity weight, clue, Commons filename, category.
ADDITIONS = [
    ("reeses", "Reese's Peanut Butter Cups", ["reeses", "reese's cups", "peanut butter cups", "reeses peanut butter cups"], 30, 8, "Chocolate cups with a peanut butter center.", "Reeses-PB-Cups.jpg", "chocolate"),
    ("pieces", "Reese's Pieces", ["reeses pieces", "reese's pieces"], 25, 8, "Orange, yellow, and brown peanut butter bites.", "Reeses-pieces-loose.JPG", "nutty"),
    ("skittles", "Skittles", ["skittles"], 20, 10, "Taste the rainbow.", "Skittles-Candies-Pile.jpg", "fruity"),
    ("twix", "Twix", ["twix"], 35, 7, "Two caramel cookie bars under chocolate.", "Twix-broken.jpg", "chocolate"),
    ("hershey", "Hershey's Chocolate Bar", ["hersheys", "hershey", "hershey bar", "hersheys chocolate bar"], 25, 8, "A classic segmented milk chocolate bar.", "Hershey-bar-open.JPG", "chocolate"),
    ("cookies", "Hershey's Cookies 'n' Creme", ["cookies and cream", "cookies n creme", "hersheys cookies n creme"], 35, 6, "White confection with crunchy cookie pieces.", "Candy-Hersheys-CookiesCreme-Broken.jpg", "chocolate"),
    ("almondjoy", "Almond Joy", ["almond joy"], 40, 5, "Coconut, chocolate, and a nut on top.", "Almond-joy-broken.jpg", "chocolate"),
    ("mounds", "Mounds", ["mounds"], 40, 5, "Dark chocolate around coconut, without the almond.", "Candy-Mounds-Broken.jpg", "chocolate"),
    ("butterfinger", "Butterfinger", ["butterfinger"], 40, 6, "A crisp, flaky peanut butter center.", "Butterfinger-broken.JPG", "chocolate"),
    ("crunch", "Crunch", ["crunch", "nestle crunch", "crunch bar"], 30, 7, "Milk chocolate with crispy rice.", "Nestle-crunch-broken.jpg", "chocolate"),
    ("musketeers", "3 Musketeers", ["3 musketeers", "three musketeers"], 40, 5, "A whipped chocolate nougat center.", "3-Musketeers-Broken.jpg", "chocolate"),
    ("milkyway", "Milky Way", ["milky way", "milkyway"], 45, 5, "A celestial name for a nougat and caramel bar.", "Milky-Way-Bars-USUK-Split.jpg", "chocolate"),
    ("payday", "PayDay", ["payday", "pay day"], 45, 5, "Salted peanuts around caramel; no chocolate coating.", "Candy-PayDay-Broken.jpg", "nutty"),
    ("york", "York Peppermint Pattie", ["york", "york peppermint pattie", "peppermint pattie", "peppermint patty"], 40, 5, "A cool mint center in dark chocolate.", "York-Peppermint-Pattie-Split.jpg", "chocolate"),
    ("rolo", "Rolo", ["rolo", "rolos"], 35, 6, "Little chocolate cups of caramel.", "Rolo-Candies-US.jpg", "chocolate"),
    ("nerds", "Nerds", ["nerds"], 25, 8, "Tiny crunchy, tangy candy pebbles.", "Nerds-Candies.jpg", "fruity"),
    ("starburst", "Starburst", ["starburst", "starbursts"], 25, 8, "Square fruit chews.", "Starburst-Candies.jpg", "fruity"),
    ("sourpatch", "Sour Patch Kids", ["sour patch kids", "sour patch", "sourpatch kids"], 30, 7, "First sour, then sweet little people.", "Sour-Patch-Kids.jpg", "fruity"),
    ("twizzlers", "Twizzlers", ["twizzlers", "twizzler"], 30, 7, "Twisted red chewy ropes.", "Twizzlers-Pile.jpg", "fruity"),
    ("tootsie", "Tootsie Roll", ["tootsie roll", "tootsie rolls"], 25, 8, "A chewy chocolate-flavored roll.", "Tootsie-Roll-WU.jpg", "chocolate"),
    ("blowpop", "Charms Blow Pop", ["blow pop", "blowpop", "charms blow pop"], 35, 6, "A lollipop hiding chewing gum.", "Charms-Blow-Pop-Green-Apple.jpg", "fruity"),
    ("dots", "Dots", ["dots", "tootsie dots"], 35, 6, "Little dome-shaped fruit gumdrops.", "Tootsie-Roll-Dots-Candy.jpg", "fruity"),
    ("junior", "Junior Mints", ["junior mints", "junior mint"], 40, 5, "Small chocolate-covered mint bites.", "Junior-Mints-Candy.jpg", "chocolate"),
    ("sweetarts", "SweeTarts", ["sweetarts", "sweet tarts"], 35, 6, "Sweet and tart colored candy tablets.", "Nestle-SweeTarts-Candies.jpg", "fruity"),
    ("mikeike", "Mike and Ike", ["mike and ike", "mike ike", "mike n ike"], 35, 6, "Two names on chewy fruit capsules.", "Mike-and-Ike-Candies.jpg", "fruity"),
    ("gobstopper", "Everlasting Gobstoppers", ["gobstopper", "gobstoppers", "everlasting gobstoppers"], 45, 4, "A layered jawbreaker from Wonka.", "Everlasting-Gobstoppers.jpg", "fruity"),
    ("butterscotch", "Butterscotch", ["butterscotch", "butterscotch candy"], 30, 6, "Golden hard candy with a buttery flavor.", "Butterscotch-Candies.jpg", "classic"),
    ("lollipop", "Rainbow Swirl Lollipop", ["lollipop", "rainbow lollipop", "swirl lollipop", "rainbow swirl lollipop"], 30, 6, "A colorful spiral on a stick.", "Lollipop-Rainbox-Swirl.jpg", "fruity"),
    ("bigcup", "Reese's Big Cup", ["reeses big cup", "reese big cup", "big cup"], 90, 8, "An oversized peanut butter cup. Halloween special!", "Reeses-PB-Big-Cup.jpg", "chocolate"),
    ("goldcoins", "Chocolate Gold Coins", ["chocolate gold coins", "gold coins", "chocolate coins", "chocolate gelt", "gelt"], 100, 8, "Edible treasure in golden foil. Halloween special!", "Chocolate-Gold-Coins.jpg", "chocolate"),
]

for index, (key, name, aliases, points, weight, hint, source, category) in enumerate(ADDITIONS, 7):
    CANDIES[key] = dict(name=name, aliases=aliases, points=points, weight=weight, hint=hint,
                       file=f"{index:02}.jpg", source=source, author="Evan-Amos",
                       license="Public domain", category=category, finale_only=key in ("bigcup", "goldcoins"))
for key, candy in CANDIES.items():
    candy.setdefault("category", "chocolate" if key in ("kitkat", "snickers", "chunky") else "classic" if key == "corn" else "fruity")
    candy.setdefault("finale_only", False)
    candy["changes"] = "Resized by Wikimedia to a 960px preview" if int(candy["file"].split(".")[0]) >= 16 else "None"
for key in ("milkyway", "rolo", "sourpatch", "lollipop", "bigcup", "goldcoins"):
    CANDIES[key].update(license="CC0", license_url="https://creativecommons.org/publicdomain/zero/1.0/")
for key in ("tootsie", "butterscotch"):
    CANDIES[key].update(license="CC BY-SA 3.0", license_url="https://creativecommons.org/licenses/by-sa/3.0/")

SIZES = {
    "fun": dict(label="Fun-size", multiplier=0.5, weight=35),
    "regular": dict(label="Regular", multiplier=1, weight=45),
    "king": dict(label="King-size", multiplier=2, weight=18),
    "jackpot": dict(label="Jackpot", multiplier=5, weight=2),
}

SETS = {
    "chocolate": dict(label="Chocolate Lovers", candies=["kitkat", "snickers", "reeses", "hershey", "twix"], bonus=250),
    "fruity": dict(label="Fruit Basket", candies=["bears", "beans", "skittles", "starburst", "sourpatch"], bonus=200),
    "halloween": dict(label="Halloween Classics", candies=["corn", "nerds", "tootsie", "blowpop"], bonus=150),
    "retro": dict(label="Old-School Treats", candies=["butterscotch", "dots", "sweetarts", "gobstopper"], bonus=200),
    "bigbars": dict(label="Big Bar Brigade", candies=["chunky", "butterfinger", "musketeers", "payday"], bonus=300),
}
