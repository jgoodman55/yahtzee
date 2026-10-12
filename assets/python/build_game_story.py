"""@bruin
name: int_game_story
connection: duckdb-default
type: python
depends:
  - stg_games
materialization:
  type: table
@bruin"""

# One or two plain sentences on what decided a game, from the box scores only.
# `int_commentary` samples a joke. This does not: the same scores always
# produce the same story, with no phrase bank and no invented detail.
# `mart_head_to_head` joins both. The scorecard export calls `game_story`
# directly so the viewer matches the Game tab.

# Higher in this list wins a tie on the size of the gap.
_BOXES = (
    "yahtzee",
    "yahtzee_bonus",
    "large_straight",
    "small_straight",
    "full_house",
    "upper_bonus",
    "four_of_a_kind",
    "three_of_a_kind",
    "chance",
    "sixes",
    "fives",
    "fours",
    "threes",
    "twos",
    "ones",
)

_PLAIN = {
    "ones": "aces",
    "twos": "twos",
    "threes": "threes",
    "fours": "fours",
    "fives": "fives",
    "sixes": "sixes",
    "upper_bonus": "upper bonus",
    "three_of_a_kind": "three of a kind",
    "four_of_a_kind": "four of a kind",
    "full_house": "full house",
    "small_straight": "small straight",
    "large_straight": "large straight",
    "chance": "chance",
    "yahtzee": "Yahtzee",
    "yahtzee_bonus": "Yahtzee bonus",
}

# A zero here is a scratch worth naming. Upper faces and chance are not.
_MISSABLE = {
    "upper_bonus",
    "three_of_a_kind",
    "four_of_a_kind",
    "full_house",
    "small_straight",
    "large_straight",
    "yahtzee",
    "yahtzee_bonus",
}

_HIT = {"full_house", "small_straight", "large_straight"}
_PRIORITY = {key: index for index, key in enumerate(_BOXES)}
_NAMES = {"erin": "Erin", "jordan": "Jordan"}

# Ignore 1-point upper-section noise unless nothing bigger exists.
_STRONG = 10
_FILL = 5
_NOTABLE = 20
_BLOWOUT = 80


def _points(scores: dict, key: str) -> int:
    value = scores.get(key, 0)
    if value is None:
        return 0
    return int(value)


def _join(parts: list[str]) -> str:
    if len(parts) == 1:
        return parts[0]
    if len(parts) == 2:
        return f"{parts[0]} and {parts[1]}"
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def _miss_name(key: str, winner_score: int) -> str:
    if key == "upper_bonus":
        return "the upper bonus"
    if key == "yahtzee":
        return "Yahtzee"
    if key == "yahtzee_bonus":
        if winner_score >= 200:
            return "two Yahtzee bonuses"
        return "the Yahtzee bonus"
    return _PLAIN[key]


def _noun(key: str, gap: int, winner_score: int) -> str:
    if key == "yahtzee_bonus":
        if winner_score >= 200 and gap >= 200:
            return f"two Yahtzee bonuses (+{gap})"
        if winner_score >= 200 and gap < winner_score:
            return f"extra Yahtzee bonus (+{gap})"
        return f"Yahtzee bonus (+{gap})"
    return f"{_PLAIN[key]} (+{gap})"


def _bright_verb(key: str, gap: int, loser_score: int) -> str:
    if key == "yahtzee":
        return f"rolled a Yahtzee (+{gap})"
    if key == "yahtzee_bonus":
        if loser_score >= 200 and gap >= 200:
            return f"picked up two Yahtzee bonuses (+{gap})"
        if loser_score >= 200 and gap < loser_score:
            return f"picked up an extra Yahtzee bonus (+{gap})"
        return f"picked up a Yahtzee bonus (+{gap})"
    if key in _HIT:
        return f"hit a {_PLAIN[key]} (+{gap})"
    if key == "upper_bonus":
        return f"took the upper bonus (+{gap})"
    return f"led on {_PLAIN[key]} (+{gap})"


def _ranked(leader: dict, trailer: dict) -> list[dict]:
    rows = []
    for key in _BOXES:
        gap = _points(leader, key) - _points(trailer, key)
        if gap > 0:
            rows.append(
                {
                    "key": key,
                    "gap": gap,
                    "leader_score": _points(leader, key),
                    "trailer_score": _points(trailer, key),
                }
            )
    rows.sort(key=lambda row: (-row["gap"], _PRIORITY[row["key"]]))
    return rows


def _pick_swings(ranked: list[dict]) -> list[dict]:
    if not ranked:
        return []
    strong = [row for row in ranked if row["gap"] >= _STRONG][:3]
    if len(strong) >= 2:
        return strong
    if len(strong) == 1:
        extra = [
            row
            for row in ranked
            if row["key"] != strong[0]["key"] and row["gap"] >= _FILL
        ]
        return strong + extra[:1]
    return ranked[:1]


def _collapse(swings: list[dict]) -> list[dict]:
    by_key = {row["key"]: row for row in swings}
    if "three_of_a_kind" not in by_key or "four_of_a_kind" not in by_key:
        return swings
    three = by_key["three_of_a_kind"]
    four = by_key["four_of_a_kind"]
    gap = three["gap"] + four["gap"]
    label = "big three and four of a kind" if gap >= 25 else "three and four of a kind"
    merged = {
        "key": "kinds",
        "gap": gap,
        "noun": f"{label} (+{gap})",
        "parts": (three, four),
    }
    out = []
    placed = False
    for row in swings:
        if row["key"] in ("three_of_a_kind", "four_of_a_kind"):
            if not placed:
                out.append(merged)
                placed = True
            continue
        out.append(row)
    return out


def _with_nouns(swings: list[dict]) -> list[dict]:
    ready = []
    for row in swings:
        if row["key"] == "kinds":
            ready.append(row)
            continue
        item = dict(row)
        item["noun"] = _noun(row["key"], row["gap"], row["leader_score"])
        item["parts"] = (row,)
        ready.append(item)
    return ready


def _misses(swings: list[dict]) -> list[str]:
    names = []
    for row in swings:
        parts = row["parts"]
        zeros = [part for part in parts if part["key"] in _MISSABLE and part["trailer_score"] == 0]
        if row["key"] == "kinds" and len(zeros) == 2:
            names.append("three and four of a kind")
            continue
        for part in zeros:
            names.append(_miss_name(part["key"], part["leader_score"]))
    return names


def game_story(erin_scores: dict, jordan_scores: dict) -> str:
    """Plain sentence or two. Scores are category to points; missing boxes are 0."""
    erin = {_key: _points(erin_scores, _key) for _key in _BOXES}
    jordan = {_key: _points(jordan_scores, _key) for _key in _BOXES}
    erin_total = sum(erin.values())
    jordan_total = sum(jordan.values())

    if erin_total == jordan_total:
        if erin == jordan:
            return "They finished level, box for box."
        erin_best = _ranked(erin, jordan)[0]
        jordan_best = _ranked(jordan, erin)[0]
        first, second = (erin_best, jordan_best)
        first_name, second_name = "Erin", "Jordan"
        if jordan_best["gap"] > erin_best["gap"] or (
            jordan_best["gap"] == erin_best["gap"]
            and _PRIORITY[jordan_best["key"]] < _PRIORITY[erin_best["key"]]
        ):
            first, second = jordan_best, erin_best
            first_name, second_name = "Jordan", "Erin"
        return (
            "They finished level. The widest split was "
            f"{first_name}'s {_noun(first['key'], first['gap'], first['leader_score'])} "
            f"against {second_name}'s {_noun(second['key'], second['gap'], second['leader_score'])}."
        )

    if jordan_total > erin_total:
        winner, loser = "jordan", "erin"
        winner_scores, loser_scores = jordan, erin
    else:
        winner, loser = "erin", "jordan"
        winner_scores, loser_scores = erin, jordan
    margin = abs(jordan_total - erin_total)
    swings = _with_nouns(_collapse(_pick_swings(_ranked(winner_scores, loser_scores))))
    cited = sum(row["gap"] for row in swings)
    misses = _misses(swings)
    winner_name = _NAMES[winner]
    loser_name = _NAMES[loser]
    winner_bits = _join([row["noun"] for row in swings])

    bright_rows = _ranked(loser_scores, winner_scores)
    bright = bright_rows[0] if bright_rows and bright_rows[0]["gap"] >= _NOTABLE else None

    if bright is not None:
        verb = _bright_verb(bright["key"], bright["gap"], bright["leader_score"])
        miss_bit = f" but missed {_join(misses)}" if misses else ""
        ending = "outweighed it" if cited > bright["gap"] else "went the other way"
        text = (
            f"{loser_name} {verb}{miss_bit}, while "
            f"{winner_name}'s {winner_bits} {ending}."
        )
    else:
        text = f"{winner_name}'s {winner_bits} decided it."
        if misses:
            text += f" {loser_name} missed {_join(misses)}."

    if margin >= _BLOWOUT:
        text = "Never close: " + text
    return text


def materialize():
    import pandas as pd
    from bruin import query

    rows = query("select game_seq, player, category, score from stg_games")
    by_game: dict[int, dict[str, dict[str, int]]] = {}
    for _, row in rows.iterrows():
        seq = int(row["game_seq"])
        player = str(row["player"]).strip().lower()
        slot = by_game.setdefault(seq, {"erin": {}, "jordan": {}})
        if player not in slot:
            continue
        slot[player][str(row["category"]).strip().lower()] = int(row["score"])

    return pd.DataFrame(
        [
            {
                "game_seq": seq,
                "story": game_story(by_game[seq]["erin"], by_game[seq]["jordan"]),
            }
            for seq in sorted(by_game)
        ]
    )
