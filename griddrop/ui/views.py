"""
ui/views.py — discord.ui.View implementations for GridDrop.

Three views:
  MacroTargetingView  — full-map dropdown (Row A-J, Col 1-10) + Lock In
  MicroTargetingView  — sector-zoom dropdown (row a-j, col 1-10) + Lock In
  ViewportView        — ⬅️ Center ➡️ panning buttons for the panorama mechanic

Design principles:
  - Views are stateless regarding the map image. They call back into the
    GameSession (passed by reference) and delegate image generation to the
    ImageEngine. This keeps rendering off the main thread.
  - All interaction responses use ephemeral=True to avoid flooding the channel.
  - The session's phase is checked on every interaction; late guesses after
    LOCKED are silently rejected with an ephemeral warning.
  - MicroTargetingView is spawned per-player from within MacroTargetingView,
    not re-used across players, so there are no shared-state race conditions.
"""

from __future__ import annotations

import io
from typing import Optional, TYPE_CHECKING

import discord

from ..models.coordinates import MacroSector, MicroCell, GridPoint
from ..models.session import GameSession, RoundPhase
from ..engine.math import score_guess, rank_guesses
from . import embeds

if TYPE_CHECKING:
    from ..engine.renderer import ImageEngine


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _macro_row_options() -> list[discord.SelectOption]:
    return [
        discord.SelectOption(label=f"Row {chr(65 + i)}  ({chr(65 + i)}1 – {chr(65 + i)}10)", value=str(i))
        for i in range(10)
    ]


def _macro_col_options() -> list[discord.SelectOption]:
    return [
        discord.SelectOption(label=f"Column {i + 1}", value=str(i))
        for i in range(10)
    ]


def _micro_row_options() -> list[discord.SelectOption]:
    return [
        discord.SelectOption(label=f"Row {chr(97 + i)}", value=str(i))
        for i in range(10)
    ]


def _micro_col_options() -> list[discord.SelectOption]:
    return [
        discord.SelectOption(label=f"Column {i + 1}", value=str(i))
        for i in range(10)
    ]


# ---------------------------------------------------------------------------
# Macro targeting (shown to all players in the channel)
# ---------------------------------------------------------------------------

class MacroTargetingView(discord.ui.View):
    """
    The primary guessing interface. Sent once per round in the channel.

    Players select their macro row + column and hit Lock In.
    If micro_mode is enabled, locking a macro selection spawns an ephemeral
    MicroTargetingView rather than finalising the guess immediately.
    """

    def __init__(
        self,
        session: GameSession,
        image_engine: "ImageEngine",
        base_image_bytes: bytes,
    ) -> None:
        super().__init__(timeout=float(session.round_seconds + 5))
        self.session          = session
        self.image_engine     = image_engine
        self.base_image_bytes = base_image_bytes

    # --- Row select ---

    @discord.ui.select(
        placeholder="① Select Latitude Row  (A – J)",
        options=_macro_row_options(),
        custom_id="macro_row",
        row=0,
    )
    async def select_row(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        if not self._check_phase(interaction):
            return
        macro = MacroSector(row=int(select.values[0]), col=self.session.get_or_create_guess(interaction.user.id).macro.col if (g := self.session.guesses.get(interaction.user.id)) and g.macro else 0)
        self.session.set_macro(interaction.user.id, MacroSector(row=int(select.values[0]), col=macro.col if self.session.guesses.get(interaction.user.id) and self.session.guesses[interaction.user.id].macro else 0))
        await interaction.response.defer(ephemeral=True, thinking=False)

    # --- Column select ---

    @discord.ui.select(
        placeholder="② Select Longitude Column  (1 – 10)",
        options=_macro_col_options(),
        custom_id="macro_col",
        row=1,
    )
    async def select_col(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        if not self._check_phase(interaction):
            return
        guess = self.session.guesses.get(interaction.user.id)
        current_row = guess.macro.row if (guess and guess.macro) else 0
        self.session.set_macro(interaction.user.id, MacroSector(row=current_row, col=int(select.values[0])))
        await interaction.response.defer(ephemeral=True, thinking=False)

    # --- Lock In ---

    @discord.ui.button(
        label="🔒 Lock In Sector",
        style=discord.ButtonStyle.primary,
        custom_id="macro_lock",
        row=2,
    )
    async def lock_in(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not self._check_phase(interaction):
            return

        user_id = interaction.user.id
        guess   = self.session.guesses.get(user_id)

        if not guess or guess.macro is None:
            await interaction.response.send_message(
                "⚠️ Please select both a **Row** and a **Column** before locking in.",
                ephemeral=True,
            )
            return

        # Macro-only mode: finalise immediately
        if not self.session.micro_mode:
            result = self.session.lock_guess(user_id)
            if result and result.resolved_point:
                score, dist = score_guess(
                    self.session.target,
                    result.resolved_point,
                    max_score=self.session.max_score,
                    k=self.session.decay_rate,
                )
                result.score    = score
                result.distance = dist
                ranked = rank_guesses(
                    [(uid, g.resolved_point) for uid, g in self.session.guesses.items() if g.resolved_point],
                    self.session.target,
                    max_score=self.session.max_score,
                    k=self.session.decay_rate,
                )
                my_rank = next((r["rank"] for r in ranked if r["user_id"] == user_id), 1)
                embed = embeds.guess_confirmed(
                    result,
                    distance_display=f"~{dist:.1f} units",
                    score=score,
                    rank=my_rank,
                    total_players=len(self.session.locked_guesses),
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Micro mode: spawn ephemeral MicroTargetingView
        macro    = guess.macro
        micro_bytes = await self.image_engine.generate_micro_grid(self.base_image_bytes, macro)
        micro_view  = MicroTargetingView(
            session=self.session,
            macro=macro,
            image_engine=self.image_engine,
            base_image_bytes=self.base_image_bytes,
        )
        micro_embed = embeds.micro_prompt(macro)
        file = discord.File(io.BytesIO(micro_bytes), filename="micro.png")
        await interaction.response.send_message(embed=micro_embed, view=micro_view, file=file, ephemeral=True)

    # --- Utility ---

    def _check_phase(self, interaction: discord.Interaction) -> bool:
        """Returns False and responds if the round is no longer accepting guesses."""
        if self.session.phase in (RoundPhase.LOCKED, RoundPhase.RESOLVING, RoundPhase.COMPLETE):
            # Fire-and-forget; we don't await here because this is called before defer
            interaction.response.send_message(
                "⏱️ The round has ended — no more guesses accepted.", ephemeral=True
            )
            return False
        return True

    def disable_all(self) -> None:
        """Disable all children. Called by core.py when the timer fires."""
        for child in self.children:
            child.disabled = True


# ---------------------------------------------------------------------------
# Micro targeting (ephemeral per-player zoom)
# ---------------------------------------------------------------------------

class MicroTargetingView(discord.ui.View):
    """
    Spawned ephemerally after a player locks their macro sector.
    Presents the cropped sector with a 10×10 sub-grid for precision.
    """

    def __init__(
        self,
        session: GameSession,
        macro: MacroSector,
        image_engine: "ImageEngine",
        base_image_bytes: bytes,
    ) -> None:
        super().__init__(timeout=float(session.round_seconds))
        self.session          = session
        self.macro            = macro
        self.image_engine     = image_engine
        self.base_image_bytes = base_image_bytes

    @discord.ui.select(
        placeholder="③ Select Micro Row  (a – j)",
        options=_micro_row_options(),
        custom_id="micro_row",
        row=0,
    )
    async def micro_row(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        self.session.set_micro(interaction.user.id, MicroCell(
            row=int(select.values[0]),
            col=self.session.guesses[interaction.user.id].micro.col
                if self.session.guesses.get(interaction.user.id) and self.session.guesses[interaction.user.id].micro
                else 0,
        ))
        await interaction.response.defer(ephemeral=True, thinking=False)

    @discord.ui.select(
        placeholder="④ Select Micro Column  (1 – 10)",
        options=_micro_col_options(),
        custom_id="micro_col",
        row=1,
    )
    async def micro_col(self, interaction: discord.Interaction, select: discord.ui.Select) -> None:
        guess = self.session.guesses.get(interaction.user.id)
        current_row = guess.micro.row if (guess and guess.micro) else 0
        self.session.set_micro(interaction.user.id, MicroCell(row=current_row, col=int(select.values[0])))
        await interaction.response.defer(ephemeral=True, thinking=False)

    @discord.ui.button(
        label="🎯 Lock In Final Guess",
        style=discord.ButtonStyle.green,
        custom_id="micro_lock",
        row=2,
    )
    async def lock_in(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.session.phase in (RoundPhase.LOCKED, RoundPhase.RESOLVING, RoundPhase.COMPLETE):
            await interaction.response.send_message(
                "⏱️ Time's up — your guess was not counted.", ephemeral=True
            )
            return

        user_id = interaction.user.id
        result  = self.session.lock_guess(user_id)

        if result is None:
            await interaction.response.send_message(
                "⚠️ Please select both **Micro Row** and **Micro Column** first.",
                ephemeral=True,
            )
            return

        score, dist = score_guess(
            self.session.target,
            result.resolved_point,
            max_score=self.session.max_score,
            k=self.session.decay_rate,
        )
        result.score    = score
        result.distance = dist

        ranked = rank_guesses(
            [(uid, g.resolved_point) for uid, g in self.session.guesses.items() if g.resolved_point],
            self.session.target,
            max_score=self.session.max_score,
            k=self.session.decay_rate,
        )
        my_rank = next((r["rank"] for r in ranked if r["user_id"] == user_id), 1)

        embed = embeds.guess_confirmed(
            result,
            distance_display=f"~{dist:.1f} units",
            score=score,
            rank=my_rank,
            total_players=len(self.session.locked_guesses),
        )

        # Disable this view so the player can't re-lock
        for child in self.children:
            child.disabled = True

        await interaction.response.edit_message(embed=embed, view=self)


# ---------------------------------------------------------------------------
# Viewport panning (panorama look-around)
# ---------------------------------------------------------------------------

class ViewportView(discord.ui.View):
    """
    Three-panel panorama navigator.
    Edits the embed image in-place to simulate panning left/right.
    Requires the caller to hold the full panorama bytes in memory.
    """

    PANELS = ("left", "center", "right")

    def __init__(
        self,
        panorama_bytes: bytes,
        image_engine: "ImageEngine",
        initial_panel: str = "center",
    ) -> None:
        super().__init__(timeout=120.0)
        self.panorama_bytes = panorama_bytes
        self.image_engine   = image_engine
        self.current_panel  = initial_panel
        self._update_button_states()

    def _update_button_states(self) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                if child.custom_id == "pan_left":
                    child.disabled = (self.current_panel == "left")
                elif child.custom_id == "pan_right":
                    child.disabled = (self.current_panel == "right")

    @discord.ui.button(label="⬅️", style=discord.ButtonStyle.secondary, custom_id="pan_left", row=0)
    async def pan_left(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        idx = self.PANELS.index(self.current_panel)
        self.current_panel = self.PANELS[max(0, idx - 1)]
        await self._update_view(interaction)

    @discord.ui.button(label="Center", style=discord.ButtonStyle.secondary, custom_id="pan_center", row=0)
    async def pan_center(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.current_panel = "center"
        await self._update_view(interaction)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.secondary, custom_id="pan_right", row=0)
    async def pan_right(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        idx = self.PANELS.index(self.current_panel)
        self.current_panel = self.PANELS[min(len(self.PANELS) - 1, idx + 1)]
        await self._update_view(interaction)

    async def _update_view(self, interaction: discord.Interaction) -> None:
        panel_bytes = await self.image_engine.generate_viewport(self.panorama_bytes, self.current_panel)
        self._update_button_states()
        file = discord.File(io.BytesIO(panel_bytes), filename="viewport.png")
        await interaction.response.edit_message(attachments=[file], view=self)
