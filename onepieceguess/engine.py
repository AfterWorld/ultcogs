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


def safe_wiki_hint(extract: str, title: str, aliases: list[str] | tuple[str, ...] = ()) -> str:
    """Build a short intro hint while removing the answer and known aliases."""
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", extract or "")).strip()
    for secret in sorted([title, *(aliases or [])], key=len, reverse=True):
        if secret:
            text = re.sub(re.escape(secret), "[redacted]", text, flags=re.IGNORECASE)
    text = text.split(". ", 1)[0].strip()
    if not text or "[redacted]" in text.lower():
        return "Look closely at the blurred image and answer with `[p]guess <name>`."
    return text[:400]
