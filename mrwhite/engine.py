"""Deterministic game rules; no Discord, persistence, or network side effects."""
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
import random
import unicodedata


class RuleError(ValueError):
    """An action is unavailable in the current game."""


class Role(str, Enum):
    CIVILIAN = "Civilian"
    UNDERCOVER = "Undercover"
    WHITE = "Mr. White"


def normalize(text: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def validate_word(text: str) -> str:
    text = normalize(text)
    if not 1 <= len(text) <= 40 or not all(c.isalpha() or c in " -'" for c in text):
        raise RuleError("Words must contain 1–40 letters, spaces, hyphens or apostrophes.")
    if not any(c.isalpha() for c in text):
        raise RuleError("A word must contain letters.")
    return text


def role_counts(count: int) -> tuple[int, int, int]:
    if not 3 <= count <= 25:
        raise RuleError("Gather 3–25 players before setting sail.")
    white = 2 if count >= 12 else 1
    undercover = 0 if count == 3 else max(1, count // 4)
    return count - undercover - white, undercover, white


@dataclass
class Game:
    host: int
    players: dict[int, str] = field(default_factory=dict)
    phase: str = "joining"
    epoch: int = 0
    round: int = 0
    roles: dict[int, Role] = field(default_factory=dict)
    eliminated: set[int] = field(default_factory=set)
    clues: dict[int, str] = field(default_factory=dict)
    votes: dict[int, int] = field(default_factory=dict)
    candidates: set[int] = field(default_factory=set)
    revote: bool = False
    guesser: int | None = None
    pair: tuple[str, str] = ("", "")
    result: str = ""
    events: list[str] = field(default_factory=list)

    @property
    def alive(self) -> list[int]:
        return [p for p in self.players if p not in self.eliminated]

    def require(self, condition: bool, message: str):
        if not condition:
            raise RuleError(message)

    def transition(self, phase: str):
        self.phase = phase
        self.epoch += 1

    def join(self, user: int, name: str):
        self.require(self.phase == "joining", "The voyage has already begun.")
        self.require(user not in self.players, "You are already aboard.")
        self.require(len(self.players) < 25, "This crew is full (25 players).")
        self.players[user] = name[:40]

    def leave(self, user: int):
        self.require(self.phase == "joining", "You can only leave in the lobby.")
        self.require(user in self.players, "You are not aboard.")
        self.require(user != self.host, "Transfer the captaincy or end the lobby first.")
        del self.players[user]

    def begin(self, pair: tuple[str, str], rng=None):
        self.require(self.phase == "joining", "The voyage has already begun.")
        c, u, w = role_counts(len(self.players))
        pair = tuple(validate_word(word) for word in pair)
        self.require(len(pair) == 2 and pair[0] != pair[1], "Choose two distinct related words.")
        rng = rng or random.SystemRandom()
        roles = [Role.CIVILIAN] * c + [Role.UNDERCOVER] * u + [Role.WHITE] * w
        rng.shuffle(roles)
        self.roles = dict(zip(self.players, roles))
        self.pair = pair
        self.next_round()

    def secret(self, user: int) -> str:
        self.require(user in self.roles and self.phase != "ended", "No active dossier for you.")
        role = self.roles[user]
        if role == Role.WHITE:
            return "Mr. White • No word. Blend in and deduce the Civilian word."
        word = self.pair[0 if role == Role.CIVILIAN else 1]
        return f"{role.value} • Your word: {word}"

    def next_round(self):
        self.round += 1
        if self.round > 20:
            self.finish("Draw — the voyage reached its 20-round limit.")
            return
        self.clues.clear()
        self.votes.clear()
        self.candidates.clear()
        self.revote = False
        self.guesser = None
        self.transition("playing")

    def say(self, user: int, text: str):
        self.require(self.phase == "playing", "Clues are not open right now.")
        self.require(user in self.alive, "Only surviving crew can give clues.")
        self.require(user not in self.clues, "You have already given a clue this round.")
        text = " ".join(text.split())
        self.require(1 <= len(text) <= 80, "Use a clue of 1–80 characters.")
        self.require(normalize(text) not in self.pair, "Do not submit either secret word as your clue.")
        self.clues[user] = text
        if len(self.clues) == len(self.alive):
            self.open_vote()

    def open_vote(self):
        self.candidates = set(self.alive)
        self.votes.clear()
        self.transition("voting")

    def vote(self, user: int, target: int):
        self.require(self.phase == "voting", "Voting is not open right now.")
        self.require(user in self.alive, "Only surviving crew can vote.")
        self.require(target in self.candidates, "Choose a current ballot candidate.")
        self.require(user != target, "You cannot vote for yourself.")
        self.votes[user] = target
        if len(self.votes) == len(self.alive):
            self.resolve_vote()

    def resolve_vote(self):
        if not self.votes:
            self.finish("Draw — nobody voted before the deadline.")
            return
        counts = Counter(self.votes.values())
        top = max(counts.values())
        tied = {user for user, count in counts.items() if count == top}
        self.events.append("Ballot: " + ", ".join(f"<@{p}> {n}" for p, n in sorted(counts.items())))
        if len(tied) > 1:
            if self.revote:
                self.events.append("The revote tied. Nobody is eliminated; a new round begins.")
                self.next_round()
            else:
                self.events.append("Tie! Revote only among the tied candidates.")
                self.revote = True
                self.candidates = tied
                self.votes.clear()
                self.transition("voting")
            return
        target = tied.pop()
        self.eliminated.add(target)
        self.events.append(f"<@{target}> was eliminated: **{self.roles[target].value}**.")
        if self.roles[target] == Role.WHITE:
            self.guesser = target
            self.transition("guessing")
        elif not self.check_winner():
            self.next_round()

    def guess(self, user: int, word: str):
        self.require(self.phase == "guessing" and user == self.guesser,
                     "Only the eliminated Mr. White can make this final guess.")
        self.require(1 <= len(word.strip()) <= 100, "Enter a guess of 1–100 characters.")
        if normalize(word) == self.pair[0]:
            self.finish("Mr. White wins — the Civilian word was cracked!")
        else:
            self.events.append("The final guess was wrong. The voyage continues if enemies remain.")
            if not self.check_winner():
                self.next_round()

    def check_winner(self) -> bool:
        counts = Counter(self.roles[p] for p in self.alive)
        c, u, w = (counts[r] for r in Role)
        if u + w == 0:
            self.finish("Civilians win — every infiltrator was eliminated!")
        elif w and len(self.alive) <= 2:
            self.finish("Mr. White wins — survived to the final two!")
        elif u and u >= c + w:
            self.finish("Undercover wins — controls at least half the surviving crew!")
        return self.phase == "ended"

    def expire(self):
        if self.phase == "joining":
            self.finish("Lobby expired before departure.")
        elif self.phase == "playing":
            self.events.append("Clue deadline reached; missing clues are skipped.")
            self.open_vote()
        elif self.phase == "voting":
            self.resolve_vote()
        elif self.phase == "guessing":
            self.events.append("Mr. White's final-guess deadline expired.")
            if not self.check_winner():
                self.next_round()

    def finish(self, reason: str):
        self.result = reason
        self.transition("ended")
