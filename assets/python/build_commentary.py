"""@bruin
name: int_commentary
connection: duckdb-default
type: python
depends:
  - int_win_loss
  - fact_games
  - seed_commentary
materialization:
  type: table
@bruin"""

# Commentary is picked deterministically per game_seq (seeded, not
# `random.choice` on an unseeded generator) so re-running `bruin run`
# produces the same caption every time. Each game keeps one comment: the
# most savage type that applies.
#
# Savagery rank, most savage first. This list is the tiebreak. A blowout,
# a game with no Yahtzee, or a game where nobody hit the upper bonus
# ("someone should've packed it in after the upper section",
# "zero Yahtzees between you both, embarrassing",
# "nobody hit the upper bonus") beats a showoff, a close call, or a
# compliment such as "on a genuine heater" / "the streak continues,
# unbothered". `ordinary` is the quiet fallback when nothing sharper fits.
SAVAGERY_RANK = (
    "big_margin",
    "zero_yahtzee",
    "no_bonus_either",
    "tie",
    "multi_yahtzee",
    "bonus_split",
    "narrow_margin",
    "streak",
    "ordinary",
)

import random

import pandas as pd
from bruin import query


def pick(rng: random.Random, phrases_by_category: dict, category: str) -> str | None:
    options = phrases_by_category.get(category)
    if not options:
        return None
    return rng.choice(options)


def savage_comment(candidates: list[tuple[str, str]]) -> str:
    """Keep the candidate whose type appears first in SAVAGERY_RANK."""
    by_type = {kind: text for kind, text in candidates if text}
    for kind in SAVAGERY_RANK:
        if kind in by_type:
            return by_type[kind]
    raise RuntimeError("no commentary candidate")


def build_row(game_seq, win_loss_row, fact_by_player, phrases_by_category):
    # Separate, stably-seeded RNG per game. Phrase picks happen in a fixed
    # order so the line chosen inside a type does not depend on which other
    # types also apply. The rank list then throws the milder ones away.
    rng = random.Random(f"{game_seq}")
    candidates: list[tuple[str, str]] = []

    margin = win_loss_row["margin"]
    winner = win_loss_row["winner"]

    if winner == "tie":
        candidates.append(("tie", pick(rng, phrases_by_category, "tie")))
    elif margin >= 60:
        candidates.append(
            ("big_margin", f"{winner}: " + pick(rng, phrases_by_category, "big_margin"))
        )
    elif margin <= 5:
        candidates.append(
            (
                "narrow_margin",
                f"{winner}: " + pick(rng, phrases_by_category, "narrow_margin"),
            )
        )

    if win_loss_row["running_same_winner_count"] >= 3:
        candidates.append(
            ("streak", f"{winner}: " + pick(rng, phrases_by_category, "streak"))
        )

    jordan = fact_by_player.get((game_seq, "jordan"), {})
    erin = fact_by_player.get((game_seq, "erin"), {})

    total_yahtzees_j = jordan.get("total_yahtzees", 0)
    total_yahtzees_p = erin.get("total_yahtzees", 0)
    if total_yahtzees_j >= 2:
        candidates.append(
            ("multi_yahtzee", "jordan: " + pick(rng, phrases_by_category, "multi_yahtzee"))
        )
    elif total_yahtzees_p >= 2:
        candidates.append(
            ("multi_yahtzee", "erin: " + pick(rng, phrases_by_category, "multi_yahtzee"))
        )
    elif total_yahtzees_j == 0 and total_yahtzees_p == 0:
        candidates.append(("zero_yahtzee", pick(rng, phrases_by_category, "zero_yahtzee")))

    bonus_j = jordan.get("upper_bonus_hit", False)
    bonus_p = erin.get("upper_bonus_hit", False)
    if not bonus_j and not bonus_p:
        candidates.append(("no_bonus_either", pick(rng, phrases_by_category, "no_bonus_either")))
    elif bonus_j and not bonus_p:
        candidates.append(
            ("bonus_split", "jordan: " + pick(rng, phrases_by_category, "bonus_split"))
        )
    elif bonus_p and not bonus_j:
        candidates.append(
            ("bonus_split", "erin: " + pick(rng, phrases_by_category, "bonus_split"))
        )

    candidates.append(("ordinary", pick(rng, phrases_by_category, "ordinary")))

    return {
        "game_seq": game_seq,
        "comment": savage_comment(candidates),
    }


def materialize():
    win_loss = query("select * from int_win_loss").set_index("game_seq", drop=False)
    facts = query("select * from fact_games")
    commentary_seed = query("select * from seed_commentary")

    phrases_by_category = (
        commentary_seed.groupby("category")["phrase"].apply(list).to_dict()
    )
    fact_by_player = {
        (row["game_seq"], row["player_key"]): row for _, row in facts.iterrows()
    }

    rows = [
        build_row(game_seq, win_loss_row, fact_by_player, phrases_by_category)
        for game_seq, win_loss_row in win_loss.iterrows()
    ]
    return pd.DataFrame(rows)