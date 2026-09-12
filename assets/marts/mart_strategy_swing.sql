/* @bruin
name: mart_strategy_swing
type: duckdb.sql
materialization:
  type: table
depends:
  - int_strategy_features
@bruin */

-- Player-blind exclusive-feature swing rates for the Strategy tab.
--
-- Cohort: games where exactly one of Erin/Jordan has the binary feature.
-- Rate: that holder's win rate (winner from int_win_loss / computed_total).
-- Ties count in n and do not count as a holder win (seed has 0 ties).
--
-- Seed grounding (n=108, 0 ties) — verify after rebuild:
--   exclusive Yahtzee = 50      ≈ 84%  (47/56)
--   exclusive upper bonus (35)  ≈ 86%  (48/56)
--   exclusive large straight 40 ≈ 75%  (27/36)
--   exclusive large straight 0  ≈ 25%  (9/36)
-- Small straight = 0 is expected n < 10; the dashboard greys that bar.

with features as (
    select
        1 as feature_ord,
        'Yahtzee bonus > 0' as feature,
        (erin_yahtzee_bonus > 0) as erin_has,
        (jordan_yahtzee_bonus > 0) as jordan_has,
        winner
    from int_strategy_features
    union all
    select
        2,
        'Upper bonus (35)',
        erin_has_upper_bonus,
        jordan_has_upper_bonus,
        winner
    from int_strategy_features
    union all
    select
        3,
        'Yahtzee = 50',
        erin_has_yahtzee,
        jordan_has_yahtzee,
        winner
    from int_strategy_features
    union all
    select
        4,
        'Large straight = 40',
        (erin_large_straight = 40),
        (jordan_large_straight = 40),
        winner
    from int_strategy_features
    union all
    select
        5,
        'Large straight = 0',
        (erin_large_straight = 0),
        (jordan_large_straight = 0),
        winner
    from int_strategy_features
    union all
    select
        6,
        'Full house = 0',
        (erin_full_house = 0),
        (jordan_full_house = 0),
        winner
    from int_strategy_features
    union all
    select
        7,
        'Small straight = 0',
        (erin_small_straight = 0),
        (jordan_small_straight = 0),
        winner
    from int_strategy_features
),
exclusive as (
    select *
    from features
    where erin_has <> jordan_has
)
select
    feature,
    feature_ord,
    count(*)::integer as n,
    sum(
        case
            when erin_has and winner = 'erin' then 1
            when jordan_has and winner = 'jordan' then 1
            else 0
        end
    )::integer as holder_wins,
    round(
        avg(
            case
                when erin_has and winner = 'erin' then 1.0
                when jordan_has and winner = 'jordan' then 1.0
                else 0.0
            end
        ),
        3
    ) as holder_win_rate,
    (count(*) < 10) as is_low_n,
    round(
        100.0 * avg(
            case
                when erin_has and winner = 'erin' then 1.0
                when jordan_has and winner = 'jordan' then 1.0
                else 0.0
            end
        )
    )::integer || '% (n=' || count(*)::integer || ')' as label
from exclusive
group by feature, feature_ord
order by feature_ord
