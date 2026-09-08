/* @bruin
name: raw_games_score_rules
type: duckdb.sql
description: |
  Impossible Yahtzee scores in raw_games (spreadsheet typos / OCR).
  One row per violating (game_seq, player, category). Jordan is still
  reviewing leftovers (IMG_2917+); this table is the living list.

  Hard-fail: `no_new_score_rule_violations` (count of rows not in
  `known_score_rule_violations`) so a new bad value fails `bruin run`.
  When leftovers are cleared, drop those seed rows and the leftover
  count check becomes `violation_count = 0`.
materialization:
  type: table
depends:
  - raw_games
  - known_score_rule_violations
columns:
  - name: game_seq
    type: integer
    checks:
      - name: not_null
  - name: player
    type: string
    checks:
      - name: not_null
  - name: category
    type: string
    checks:
      - name: not_null
  - name: score
    type: integer
    checks:
      - name: not_null
  - name: rule
    type: string
    checks:
      - name: not_null
custom_checks:
  - name: no_new_score_rule_violations
    description: |
      Fail when a score-rule violation appears that is not already listed
      in known_score_rule_violations. After Jordan clears a leftover,
      delete that row from the known-violations seed (do not silently
      "fix" other cells).
    query: |
      select count(*)
      from raw_games_score_rules v
      where not exists (
          select 1
          from known_score_rule_violations k
          where k.game_seq = v.game_seq
            and k.player = v.player
            and k.category = v.category
            and k.score = v.score
            and k.rule = v.rule
      )
    value: 0
  - name: known_score_rule_violations_still_present
    description: |
      Fail when a documented leftover disappears without updating
      known_score_rule_violations.csv (keeps the allowlist honest).
    query: |
      select count(*)
      from known_score_rule_violations k
      where not exists (
          select 1
          from raw_games_score_rules v
          where v.game_seq = k.game_seq
            and v.player = k.player
            and v.category = k.category
            and v.score = k.score
            and v.rule = k.rule
      )
    value: 0
@bruin */

-- Legal Hasbro box values. Upper faces must be n * face for n in 0..5.
-- Chance is the sum of five dice, so 0 is never a real score.
-- upper_bonus is 35 or 0.

with src as (
    select
        cast(game_seq as integer) as game_seq,
        lower(trim(player))       as player,
        lower(trim(category))     as category,
        cast(score as integer)    as score
    from raw_games
),
violations as (
    select game_seq, player, category, score,
           'full_house must be 0 or 25' as rule
    from src
    where category = 'full_house' and score not in (0, 25)

    union all
    select game_seq, player, category, score,
           'small_straight must be 0 or 30'
    from src
    where category = 'small_straight' and score not in (0, 30)

    union all
    select game_seq, player, category, score,
           'large_straight must be 0 or 40'
    from src
    where category = 'large_straight' and score not in (0, 40)

    union all
    select game_seq, player, category, score,
           'yahtzee must be 0 or 50'
    from src
    where category = 'yahtzee' and score not in (0, 50)

    union all
    select game_seq, player, category, score,
           'chance must never be 0'
    from src
    where category = 'chance' and score = 0

    union all
    select game_seq, player, category, score,
           'upper_bonus must be 0 or 35'
    from src
    where category = 'upper_bonus' and score not in (0, 35)

    union all
    select game_seq, player, category, score,
           'ones must be a multiple of 1 in 0..5'
    from src
    where category = 'ones' and (score % 1 <> 0 or score < 0 or score > 5)

    union all
    select game_seq, player, category, score,
           'twos must be a multiple of 2 in 0..10'
    from src
    where category = 'twos' and (score % 2 <> 0 or score < 0 or score > 10)

    union all
    select game_seq, player, category, score,
           'threes must be a multiple of 3 in 0..15'
    from src
    where category = 'threes' and (score % 3 <> 0 or score < 0 or score > 15)

    union all
    select game_seq, player, category, score,
           'fours must be a multiple of 4 in 0..20'
    from src
    where category = 'fours' and (score % 4 <> 0 or score < 0 or score > 20)

    union all
    select game_seq, player, category, score,
           'fives must be a multiple of 5 in 0..25'
    from src
    where category = 'fives' and (score % 5 <> 0 or score < 0 or score > 25)

    union all
    select game_seq, player, category, score,
           'sixes must be a multiple of 6 in 0..30'
    from src
    where category = 'sixes' and (score % 6 <> 0 or score < 0 or score > 30)
)
select game_seq, player, category, score, rule
from violations
order by game_seq, player, category
