"""Discord components; all meaningful state lives in Store, never in a view."""

import discord

NONE = discord.AllowedMentions.none()


async def reply(interaction, text, **kwargs):
    kwargs.setdefault("allowed_mentions", NONE)
    kwargs.setdefault("ephemeral", True)
    if interaction.response.is_done():
        return await interaction.followup.send(text, **kwargs)
    return await interaction.response.send_message(text, **kwargs)


class SafeView(discord.ui.View):
    def __init__(self, cog, guild_id, *, timeout=None):
        super().__init__(timeout=timeout)
        self.cog, self.guild_id = cog, guild_id

    async def on_error(self, interaction, error, item):
        await self.cog.interaction_error(interaction, self.guild_id, error)


class ActionButton(discord.ui.Button):
    def __init__(
        self, cog, guild_id, action, label, app_id=None, style=discord.ButtonStyle.secondary
    ):
        super().__init__(
            label=label, style=style, custom_id=f"staffapp:{guild_id}:{app_id or 'panel'}:{action}"
        )
        self.cog, self.guild_id, self.action, self.app_id = cog, guild_id, action, app_id

    async def callback(self, interaction):
        try:
            await self.cog.handle(interaction, self.guild_id, self.action, self.app_id)
        except Exception as error:
            await self.cog.interaction_error(interaction, self.guild_id, error, self.app_id)


def panel(cog, guild_id):
    cfg = cog.store.settings(guild_id)
    buttons = [
        ActionButton(cog, guild_id, action, label, style=style)
        for action, label, style in [
            ("apply", "Apply Now", discord.ButtonStyle.primary),
            ("requirements", "Requirements", discord.ButtonStyle.secondary),
            ("status", "My Application", discord.ButtonStyle.secondary),
        ]
    ]
    text = f"{cfg['description']}\n\n**Applications {'OPEN' if cfg['open'] else 'CLOSED'}**\nYour answers are shared only with authorized server reviewers and bot operators."
    if hasattr(discord.ui, "LayoutView"):
        view = discord.ui.LayoutView(timeout=None)
        view.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(f"## {cfg['title']}"),
                discord.ui.TextDisplay(text),
                discord.ui.Separator(),
                discord.ui.ActionRow(*buttons),
                accent_color=cfg["color"],
            )
        )
        return {"view": view}
    view = SafeView(cog, guild_id)
    for button in buttons:
        view.add_item(button)
    return {
        "embed": discord.Embed(title=cfg["title"], description=text, color=cfg["color"]),
        "view": view,
    }


class PositionSelect(discord.ui.Select):
    def __init__(self, cog, guild_id):
        super().__init__(
            placeholder="Choose a staff position",
            options=[
                discord.SelectOption(label=p, value=p)
                for p in cog.store.settings(guild_id)["positions"]
            ],
        )
        self.cog, self.guild_id = cog, guild_id

    async def callback(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await self.cog.guard(interaction, self.guild_id)
        await self.cog.begin(interaction, self.guild_id, self.values[0])


class PositionView(SafeView):
    def __init__(self, cog, guild_id):
        super().__init__(cog, guild_id, timeout=180)
        self.add_item(PositionSelect(cog, guild_id))


class DraftView(SafeView):
    def __init__(self, cog, app):
        super().__init__(cog, app["guild"])
        for action, label, style in [
            ("continue", "Continue", discord.ButtonStyle.primary),
            ("edit", "Edit an Answer", discord.ButtonStyle.secondary),
            ("preview", "Review Answers", discord.ButtonStyle.secondary),
            ("submit", "Submit", discord.ButtonStyle.success),
            ("cancel", "Cancel", discord.ButtonStyle.danger),
        ]:
            self.add_item(ActionButton(cog, app["guild"], action, label, app["id"], style))


class QuestionSelect(discord.ui.Select):
    def __init__(self, cog, app):
        super().__init__(
            placeholder="Choose a question to edit",
            options=[
                discord.SelectOption(label=f"Question {n + 1}", description=q[:100], value=str(n))
                for n, q in enumerate(app["questions"])
            ],
        )
        self.cog, self.app_id = cog, app["id"]

    async def callback(self, interaction):
        app = self.cog.store.owned(self.app_id, interaction.user.id, draft=True)
        await interaction.response.send_modal(AnswerModal(self.cog, app, int(self.values[0])))


class EditView(SafeView):
    def __init__(self, cog, app):
        super().__init__(cog, app["guild"], timeout=180)
        self.add_item(QuestionSelect(cog, app))


class AnswerModal(discord.ui.Modal):
    def __init__(self, cog, app, index):
        super().__init__(title=f"Question {index + 1} of {len(app['questions'])}", timeout=600)
        self.cog, self.app_id, self.guild_id = cog, app["id"], app["guild"]
        self.index, self.revision = index, app["revision"]
        self.answer = discord.ui.TextInput(
            label=None if hasattr(discord.ui, "Label") else app["questions"][index][:45],
            style=discord.TextStyle.paragraph,
            default=app["answers"][index],
            min_length=1,
            max_length=2000,
        )
        if hasattr(discord.ui, "Label"):
            self.add_item(
                discord.ui.Label(
                    text=f"Question {index + 1}",
                    description=app["questions"][index],
                    component=self.answer,
                )
            )
        else:
            self.add_item(self.answer)

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await self.cog.guard(interaction, self.guild_id)
        self.cog.store.answer(
            self.app_id, interaction.user.id, self.index, str(self.answer), self.revision
        )
        await reply(
            interaction,
            "Answer saved. Use Continue for the next question, or Review Answers before submitting.",
        )
        await self.cog.refresh_draft(self.app_id)

    async def on_error(self, interaction, error):
        await self.cog.interaction_error(interaction, self.guild_id, error, self.app_id)


class ReviewView(SafeView):
    def __init__(self, cog, app):
        super().__init__(cog, app["guild"])
        for action, label, style in [
            ("view_answers", "View Answers", discord.ButtonStyle.secondary),
            ("claim", "Claim", discord.ButtonStyle.secondary),
            ("under_review", "Under Review", discord.ButtonStyle.primary),
            ("accepted", "Accept", discord.ButtonStyle.success),
            ("declined", "Decline", discord.ButtonStyle.danger),
        ]:
            button = ActionButton(cog, app["guild"], action, label, app["id"], style)
            button.disabled = action != "view_answers" and app["status"] not in {
                "queued",
                "pending",
                "under_review",
            }
            self.add_item(button)


class DecisionModal(discord.ui.Modal):
    def __init__(self, cog, app, action):
        super().__init__(
            title="Accept application" if action == "accepted" else "Decline application",
            timeout=300,
        )
        self.cog, self.app_id, self.guild_id, self.action = cog, app["id"], app["guild"], action
        self.reason = discord.ui.TextInput(
            label=None if hasattr(discord.ui, "Label") else "Message sent to the applicant",
            style=discord.TextStyle.paragraph,
            min_length=1,
            max_length=1000,
        )
        if hasattr(discord.ui, "Label"):
            self.add_item(
                discord.ui.Label(text="Message sent to the applicant", component=self.reason)
            )
        else:
            self.add_item(self.reason)

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        await self.cog.guard(interaction, self.guild_id, reviewer=True)
        self.cog.check_review_message(interaction, self.cog.store.get(self.app_id), modal=True)
        self.cog.store.decide(self.app_id, interaction.user.id, self.action, str(self.reason))
        await reply(
            interaction,
            "Decision saved. The review card and applicant notification will update shortly.",
        )

    async def on_error(self, interaction, error):
        await self.cog.interaction_error(interaction, self.guild_id, error, self.app_id)


class CancelView(SafeView):
    def __init__(self, cog, app):
        super().__init__(cog, app["guild"], timeout=60)
        self.add_item(
            ActionButton(
                cog,
                app["guild"],
                "confirm_cancel",
                "Yes, cancel my draft",
                app["id"],
                discord.ButtonStyle.danger,
            )
        )


class AnswerPages(SafeView):
    """Private, in-Discord answer reader; authorization is rechecked on every page."""

    def __init__(self, cog, app, user_id, reviewer=False):
        super().__init__(cog, app["guild"], timeout=300)
        self.app_id, self.user_id, self.reviewer = app["id"], user_id, reviewer
        self.index = 0

    def embed(self):
        app = self.cog.store.get(self.app_id)
        return discord.Embed(
            title=f"Answer {self.index + 1} of {len(app['questions'])}",
            description=f"**{app['questions'][self.index]}**\n\n{app['answers'][self.index] or '(not answered)'}",
            color=0x5865F2,
        ).set_footer(text=f"Application {app['id']}")

    async def turn(self, interaction, offset):
        if interaction.user.id != self.user_id:
            from .store import UserError

            raise UserError("This answer reader belongs to another member.")
        await interaction.response.defer()
        await self.cog.guard(interaction, self.guild_id, reviewer=self.reviewer)
        app = self.cog.store.get(self.app_id)
        if self.reviewer:
            self.cog.check_review_message(interaction, app, modal=True)
        else:
            self.cog.store.owned(self.app_id, interaction.user.id)
        self.index = (self.index + offset) % len(app["questions"])
        await interaction.edit_original_response(
            embed=self.embed(), view=self, allowed_mentions=NONE
        )

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction, button):
        await self.turn(interaction, -1)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction, button):
        await self.turn(interaction, 1)
