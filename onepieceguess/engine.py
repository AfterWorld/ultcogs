"""Pure helpers for OnePieceGuess answer handling."""

import difflib
import re


def normalize(value: str) -> str:
    """Normalize punctuation, spacing, and case for answer comparisons."""
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def matches_guess(guess: str, title: str, aliases: tuple[str, ...] | list[str] = ()) -> bool:
    """Allow exact answers, safe surname/nickname matches, and close typos."""
    guess_norm = normalize(guess)
    if len(guess_norm.replace(" ", "")) < 3:
        return False
    title_norm = normalize(title)
    options = [title_norm, *(normalize(item) for item in aliases)]
    if guess_norm in options:
        return True
    tokens = title_norm.split()
    if len(guess_norm.split()) == 1 and len(guess_norm) >= 4 and len(tokens) > 1:
        if guess_norm in tokens[1:]:
            return True
    if len(guess_norm) >= 4:
        for option in options:
            if len(option) >= 4 and difflib.SequenceMatcher(None, guess_norm, option).ratio() >= 0.88:
                return True
    return False
