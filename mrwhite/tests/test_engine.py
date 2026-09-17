import random
from collections import Counter

import pytest

from mrwhite.engine import Game, Role, RuleError, normalize, role_counts, validate_word
from mrwhite.words import DEFAULT_PAIRS


def game(n=6):
    g = Game(1)
    for p in range(1, n+1):
        g.join(p, f"Crew {p}")
    g.begin(("anchor", "compass"), random.Random(4))
    return g


def eliminate(g, target):
    g.open_vote()
    # A deadline with partial turnout resolves votes actually cast.
    voter = next(p for p in g.alive if p != target)
    g.vote(voter, target)
    g.expire()


@pytest.mark.parametrize("n", range(3,26))
def test_scaling_secrets_and_no_instant_win(n):
    g = game(n)
    counts = Counter(g.roles.values())
    assert tuple(counts[r] for r in Role) == role_counts(n)
    assert not g.check_winner()
    for p,r in g.roles.items():
        secret = g.secret(p)
        if r == Role.WHITE:
            assert "anchor" not in secret and "compass" not in secret
        else:
            assert ("anchor" if r == Role.CIVILIAN else "compass") in secret


@pytest.mark.parametrize("n", [0,1,2,26])
def test_player_limits(n):
    with pytest.raises(RuleError):
        role_counts(n)


def test_lobby_and_clue_guards():
    g = game()
    with pytest.raises(RuleError):
        g.join(99, "Late")
    with pytest.raises(RuleError):
        g.say(99, "outsider")
    with pytest.raises(RuleError):
        g.say(1, "ANCHOR")
    with pytest.raises(RuleError):
        g.say(1, "x" * 81)
    g.say(1, "rope")
    with pytest.raises(RuleError):
        g.say(1, "again")
    for p in g.alive[1:]:
        g.say(p, "nautical")
    assert g.phase == "voting"


def test_tie_revote_restriction_and_second_tie():
    g = game(6)
    g.open_vote()
    g.vote(3,1)
    g.vote(4,2)
    epoch = g.epoch
    g.expire()
    assert g.revote and g.candidates == {1,2} and g.epoch > epoch
    with pytest.raises(RuleError):
        g.vote(1,3)
    with pytest.raises(RuleError):
        g.vote(1,1)
    g.vote(1,2)
    g.vote(2,1)
    g.expire()
    assert g.phase == "playing" and g.round == 2 and not g.eliminated


def test_ballot_changes_and_abstentions():
    g = game()
    g.open_vote()
    g.vote(1,2)
    g.vote(1,3)
    assert len(g.votes) == 1 and g.votes[1] == 3
    g.expire()
    assert g.eliminated == {3}
    with pytest.raises(RuleError):
        g.vote(3,1)


@pytest.mark.parametrize("correct", [True,False])
def test_white_final_guess_three_players(correct):
    g = game(3)
    white = next(p for p,r in g.roles.items() if r == Role.WHITE)
    eliminate(g,white)
    assert g.phase == "guessing"
    with pytest.raises(RuleError):
        g.guess(next(p for p in g.alive), "anchor")
    g.guess(white, "  ＡＮＣＨＯＲ  " if correct else "compass")
    assert g.phase == "ended"
    assert ("Mr. White wins" if correct else "Civilians win") in g.result
    with pytest.raises(RuleError):
        g.guess(white,"anchor")


def test_wrong_white_guess_continues_with_undercover():
    g = game(6)
    white = next(p for p,r in g.roles.items() if r == Role.WHITE)
    eliminate(g,white)
    g.guess(white,"wrong")
    assert g.phase == "playing"
    undercover = next(p for p,r in g.roles.items() if r == Role.UNDERCOVER)
    eliminate(g,undercover)
    assert "Civilians win" in g.result


def test_multiple_whites_each_get_a_guess():
    g = game(12)
    whites = [p for p,r in g.roles.items() if r == Role.WHITE]
    eliminate(g,whites[0])
    g.expire()
    assert g.phase == "playing"
    eliminate(g,whites[1])
    assert g.guesser == whites[1]
    g.guess(whites[1],"anchor")
    assert "Mr. White wins" in g.result


def test_undercover_parity_and_white_survival_priority():
    g = game(6)
    u = next(p for p,r in g.roles.items() if r == Role.UNDERCOVER)
    c = next(p for p,r in g.roles.items() if r == Role.CIVILIAN)
    g.eliminated = set(g.players)-{u,c}
    assert g.check_winner() and "Undercover wins" in g.result
    g = game(4)
    u = next(p for p,r in g.roles.items() if r == Role.UNDERCOVER)
    w = next(p for p,r in g.roles.items() if r == Role.WHITE)
    g.eliminated = set(g.players)-{u,w}
    assert g.check_winner() and "Mr. White wins" in g.result


def test_all_timeouts_and_round_limit():
    g = Game(1)
    g.expire()
    assert g.phase == "ended"
    g = game()
    g.expire()
    assert g.phase == "voting"
    g.expire()
    assert "nobody voted" in g.result
    g = game(3)
    w = next(p for p,r in g.roles.items() if r == Role.WHITE)
    eliminate(g,w)
    g.expire()
    assert "Civilians win" in g.result
    g = game()
    g.round = 20
    g.next_round()
    assert "20-round" in g.result


def test_word_validation_and_defaults():
    assert normalize("  ICE   Cream ") == "ice cream"
    for bad in ("", "@everyone", "-", "a"*41, "a\nb", "x|y"):
        if bad == "a\nb":
            assert validate_word(bad) == "a b"
        else:
            with pytest.raises(RuleError):
                validate_word(bad)
    pairs = set()
    for a,b in DEFAULT_PAIRS:
        assert validate_word(a) != validate_word(b)
        assert frozenset((a,b)) not in pairs
        pairs.add(frozenset((a,b)))


@pytest.mark.parametrize("seed", range(50))
def test_random_complete_games_terminate(seed):
    rng = random.Random(seed)
    g = game(rng.randint(3,25))
    for _ in range(2000):
        if g.phase == "ended":
            break
        if g.phase == "playing":
            for p in list(g.alive):
                g.say(p,"clue")
        elif g.phase == "voting":
            for p in list(g.alive):
                candidates = list(g.candidates-{p})
                if candidates:
                    g.vote(p,rng.choice(candidates))
                if g.phase != "voting":
                    break
            if g.phase == "voting":
                g.expire()
        elif g.phase == "guessing":
            g.guess(g.guesser,"anchor" if rng.random()<.2 else "wrong")
        assert set(g.alive).isdisjoint(g.eliminated)
    assert g.phase == "ended" and g.result
