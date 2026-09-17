"""Short-lived controls tied to a session and phase generation."""
import discord


class EntryModal(discord.ui.Modal):
    def __init__(self, session, action, epoch):
        super().__init__(title="Give a clue" if action == "say" else "Final guess", timeout=180)
        self.session, self.action, self.epoch = session, action, epoch
        self.entry = discord.ui.TextInput(label="Your clue" if action == "say" else "Civilian word",
                                          max_length=80 if action == "say" else 100)
        self.add_item(self.entry)

    async def on_submit(self, interaction):
        await self.session.interact(interaction, self.action, str(self.entry), self.epoch)


class Ballot(discord.ui.Select):
    def __init__(self, session):
        options = [discord.SelectOption(label=session.game.players[p][:80], value=str(p))
                   for p in session.game.alive if p in session.game.candidates]
        super().__init__(placeholder="Choose a suspect • your ballot is private", options=options)

    async def callback(self, interaction):
        await self.view.session.interact(interaction, "vote", int(self.values[0]), self.view.epoch)


class GameView(discord.ui.View):
    def __init__(self, session):
        # Session deadlines are absolute; clicks cannot extend them.
        super().__init__(timeout=None)
        self.session = session
        self.epoch = session.game.epoch
        phase = session.game.phase
        if phase == "joining":
            self.button("Join crew", "join", discord.ButtonStyle.success)
            self.button("Leave", "leave")
            self.button("Set sail", "begin", discord.ButtonStyle.primary)
        else:
            self.button("My secret dossier", "role", discord.ButtonStyle.primary)
            if phase == "playing":
                self.button("Give a clue", "say", discord.ButtonStyle.success, modal=True)
            elif phase == "voting":
                self.add_item(Ballot(session))
            elif phase == "guessing":
                self.button("Final guess", "guess", discord.ButtonStyle.danger, modal=True)
        self.button("End voyage", "end", discord.ButtonStyle.danger)

    def button(self, label, action, style=discord.ButtonStyle.secondary, modal=False):
        item = discord.ui.Button(label=label, style=style)

        async def callback(interaction):
            if modal:
                # Submission repeats all checks inside the session lock.
                if not self.session.active or self.epoch != self.session.game.epoch:
                    await interaction.response.send_message("This control has expired.", ephemeral=True)
                    return
                await interaction.response.send_modal(EntryModal(self.session, action, self.epoch))
            else:
                await self.session.interact(interaction, action, epoch=self.epoch)
        item.callback = callback
        self.add_item(item)
