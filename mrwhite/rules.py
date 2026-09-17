"""A compact public field guide with private, on-demand rule details."""
import discord


def rules_page(page: str, prefix: str) -> discord.Embed:
    embed = discord.Embed(color=0xE63649)
    embed.set_author(name="SECRET SEAS  /  FIELD GUIDE")
    embed.set_footer(text="MR. WHITE • Blend in. Find them out.")
    if page == "overview":
        embed.title = "One crew. Three secret identities."
        embed.description = "**3–25 players** · A word game of clues, bluffing and betrayal."
        embed.add_field(name="⚓ Civilian", value="You share a word with your crew. Find every infiltrator.", inline=False)
        embed.add_field(name="🕶️ Undercover", value="Your word is slightly different. Hide in plain sight.", inline=False)
        embed.add_field(name="🎭 Mr. White", value="No word. Just your wits. Bluff your way to survival.", inline=False)
        embed.add_field(name="THE ROUND", value=(
            "**01** Open **My secret dossier** — only you can see it.\n"
            "**02** Give one short clue without revealing your word.\n"
            "**03** Vote for a suspect. Someone loses their cover."), inline=False)
        embed.add_field(name="READY TO SET SAIL?", value=(
            f"`{prefix}mrwhite start` → **Join crew** → **Set sail**\n"
            "Explore the details below. They open privately for you."), inline=False)
    elif page == "roles":
        embed.title = "The mission behind the mask"
        embed.description = "Your word stays the same for the entire voyage."
        embed.add_field(name="⚓ CIVILIANS • Expose them all", value=(
            "Everyone on your side receives the same word.\n"
            "**Win:** eliminate every Undercover and Mr. White."), inline=False)
        embed.add_field(name="🕶️ UNDERCOVER • Take control", value=(
            "You receive a related word and know your own role.\n"
            "**Win:** your surviving faction equals or outnumbers all other survivors combined."), inline=False)
        embed.add_field(name="🎭 MR. WHITE • Improvise", value=(
            "You receive no word. Listen carefully and blend in.\n"
            "**Win:** survive to the final two, **or** guess the Civilian word when eliminated."), inline=False)
        embed.add_field(name="THE LAST WORD", value=(
            "An eliminated White gets **one guess before any other victory is checked**. "
            "A wrong or missed guess continues play if enemies remain.\n\n"
            "Whites share their faction's victory; each eliminated White gets a guess. "
            "Final-two survival takes priority over Undercover's numbers."), inline=False)
    elif page == "voting":
        embed.title = "A clue. A vote. A reveal."
        embed.add_field(name="01 / LEAVE A CLUE", value=(
            "Each living player gives **one clue of 1–80 characters**, in any order. "
            "Do not submit either secret word. Missed clues are skipped at the deadline."), inline=False)
        embed.add_field(name="02 / PICK A SUSPECT", value=(
            "Use the select menu for a **private ballot**. No self-votes. "
            "You may change your vote until everyone votes or time expires. "
            "Only living players can vote; missing votes abstain."), inline=False)
        embed.add_field(name="03 / BREAK THE TIE", value=(
            "The highest vote total is eliminated and their role is revealed.\n"
            "**Tie?** Everyone revotes among the tied suspects.\n"
            "**Tied again?** Nobody is eliminated. A new round begins."), inline=False)
        embed.add_field(name="WHEN TIME RUNS OUT", value=(
            "No ballots means a **draw**. A missed final guess counts as wrong. "
            "The voyage also draws after **20 rounds**. Button clicks never extend a deadline."), inline=False)
    else:
        embed.title = "The captain's pocket guide"
        embed.add_field(name="RUN YOUR CREW", value=(
            "The captain, a Manage Server moderator, or the bot owner can **begin**, **end**, "
            "**transfer** control, or **kick** a player from the lobby.\n"
            "The captain must transfer control before leaving. Mid-game departures are handled by deadlines."), inline=False)
        embed.add_field(name="CREW DISTRIBUTION", value=(
            "**Players → Undercover / Mr. White**\n"
            "3 → **0 / 1**\n4–7 → **1 / 1**\n8–11 → **2 / 1**\n"
            "12–15 → **3 / 2**\n16–19 → **4 / 2**\n20–23 → **5 / 2**\n24–25 → **6 / 2**\n"
            "All remaining players are Civilians."), inline=False)
        embed.add_field(name="DEFAULT DEADLINES", value=(
            "Lobby **5 min** · Clues **2 min** · Voting **90 sec** · Guess **45 sec**\n"
            "Admins can configure 30–900 seconds per phase for new lobbies."), inline=False)
        embed.add_field(name="GOOD TO KNOW", value=(
            "Closed DMs? **My secret dossier** still works privately. "
            "Typed commands and guesses are visible in chat.\n"
            "Restarting or reloading the cog closes active games.\n"
            f"`{prefix}mrwhite status` finds your current game card."), inline=False)
    return embed


class RulesView(discord.ui.View):
    def __init__(self, prefix: str):
        super().__init__(timeout=300)
        self.message = None
        for label, emoji, page in (
            ("Roles & wins", "🎭", "roles"),
            ("Voting & ties", "🗳️", "voting"),
            ("Captain's guide", "⚓", "captain"),
        ):
            button = discord.ui.Button(label=label, emoji=emoji, style=discord.ButtonStyle.secondary)

            async def callback(interaction, selected=page):
                await interaction.response.send_message(
                    embed=rules_page(selected, prefix), ephemeral=True,
                    allowed_mentions=discord.AllowedMentions.none())

            button.callback = callback
            self.add_item(button)

    async def on_timeout(self):
        if self.message:
            try:
                await self.message.edit(view=None)
            except discord.HTTPException:
                pass
