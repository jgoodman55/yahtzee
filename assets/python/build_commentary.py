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
# produces the same captions every time — reproducibility matters for a
# pipeline, even a joke-generating one.

import random

import pandas as pd
from bruin import query


def pick(rng: random.Random, phrases_by_category: dict, category: str) -> str | None:
    options = phrases_by_category.get(category)
    if not options:
        return None
    return rng.choice(options)


def build_row(game_seq, win_loss_row, fact_by_player, phrases_by_category):
    # Separate, stably-seeded RNG per game so each comment type doesn't
    # always land on the same phrase index within a game.
    rng = random.Random(f"{game_seq}")

    margin = win_loss_row["margin"]
    winner = win_loss_row["winner"]

    if winner == "tie":
        margin_comment = pick(rng, phrases_by_category, "tie")
    elif margin >= 60:
        margin_comment = f"{winner}: " + pick(rng, phrases_by_category, "big_margin")
    elif margin <= 5:
        margin_comment = f"{winner}: " + pick(rng, phrases_by_category, "narrow_margin")
    else:
        margin_comment = None

    streak_comment = None
    if win_loss_row["running_same_winner_count"] >= 3:
        streak_comment = f"{winner}: " + pick(rng, phrases_by_category, "streak")

    jordan = fact_by_player.get((game_seq, "jordan"), {})
    erin = fact_by_player.get((game_seq, "erin"), {})

    total_yahtzees_j = jordan.get("total_yahtzees", 0)
    total_yahtzees_p = erin.get("total_yahtzees", 0)
    if total_yahtzees_j >= 2:
        yahtzee_comment = "jordan: " + pick(rng, phrases_by_category, "multi_yahtzee")
    elif total_yahtzees_p >= 2:
        yahtzee_comment = "erin: " + pick(rng, phrases_by_category, "multi_yahtzee")
    elif total_yahtzees_j == 0 and total_yahtzees_p == 0:
        yahtzee_comment = pick(rng, phrases_by_category, "zero_yahtzee")
    else:
        yahtzee_comment = None

    bonus_j = jordan.get("upper_bonus_hit", False)
    bonus_p = erin.get("upper_bonus_hit", False)
    if not bonus_j and not bonus_p:
        bonus_comment = pick(rng, phrases_by_category, "no_bonus_either")
    elif bonus_j and not bonus_p:
        bonus_comment = "jordan: " + pick(rng, phrases_by_category, "bonus_split")
    elif bonus_p and not bonus_j:
        bonus_comment = "erin: " + pick(rng, phrases_by_category, "bonus_split")
    else:
        bonus_comment = None

    return {
        "game_seq": game_seq,
        "margin_comment": margin_comment,
        "yahtzee_comment": yahtzee_comment,
        "bonus_comment": bonus_comment,
        "streak_comment": streak_comment,
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