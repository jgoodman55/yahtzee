/* @bruin
name: mart_strategy_rescue
type: duckdb.sql
materialization:
  type: table
depends:
  - int_strategy_features
@bruin */

-- Rescue matrix: missed box × consolation still on the card.
--
-- Cohort (exclusive combo — read this before quoting a rate):
--   A game enters cell (miss M, consolation C) when exactly one of
--   Erin/Jordan has BOTH M and C. The cell is that focal player's win
--   rate. Consolation buckets are mutually exclusive:
--     has Yahtzee      = natural 50, no upper bonus
--     has upper bonus  = upper 35, no Yahtzee
--     has both         = natural 50 and upper 35
--     has neither      = no natural 50 and no upper 35
--
-- This is not "exactly one player has miss M, then split by what they
-- still have". That exclusive-miss cut of LS=0 + any Yahtzee is 8/18.
-- Exclusive (LS=0 AND has Yahtzee) — yz-only + both, any opponent LS —
-- is the grounded 12/22 ≈ 55% (includes 4 games where both missed LS
-- but only one also had Yahtzee).
--
-- Rows are miss types, not unique games: one game can appear in several
-- cells if the same player uniquely holds more than one miss+consolation.
-- n < 10 cells are noisy (small straight in particular).
--
-- Seed grounding: exclusive LS=0 + any Yahtzee = 12/22 ≈ 55%.

with miss_defs as (
    select 1 as miss_ord, 'Large straight = 0' as miss
    union all select 2, 'Small straight = 0'
    union all select 3, 'Full house = 0'
    union all select 4, 'No Yahtzee'
),
cons_defs as (
    select 1 as cons_ord, 'Has Yahtzee' as consolation
    union all select 2, 'Has upper bonus'
    union all select 3, 'Has both'
    union all select 4, 'Has neither'
),
crossed as (
    select
        g.game_seq,
        g.winner,
        m.miss_ord,
        m.miss,
        c.cons_ord,
        c.consolation,
        case m.miss
            when 'Large straight = 0' then g.erin_large_straight = 0
            when 'Small straight = 0' then g.erin_small_straight = 0
            when 'Full house = 0' then g.erin_full_house = 0
            when 'No Yahtzee' then not g.erin_has_yahtzee
        end as erin_miss,
        case m.miss
            when 'Large straight = 0' then g.jordan_large_straight = 0
            when 'Small straight = 0' then g.jordan_small_straight = 0
            when 'Full house = 0' then g.jordan_full_house = 0
            when 'No Yahtzee' then not g.jordan_has_yahtzee
        end as jordan_miss,
        case c.consolation
            when 'Has Yahtzee' then g.erin_has_yahtzee and not g.erin_has_upper_bonus
            when 'Has upper bonus' then g.erin_has_upper_bonus and not g.erin_has_yahtzee
            when 'Has both' then g.erin_has_yahtzee and g.erin_has_upper_bonus
            when 'Has neither' then not g.erin_has_yahtzee and not g.erin_has_upper_bonus
        end as erin_cons,
        case c.consolation
            when 'Has Yahtzee' then g.jordan_has_yahtzee and not g.jordan_has_upper_bonus
            when 'Has upper bonus' then g.jordan_has_upper_bonus and not g.jordan_has_yahtzee
            when 'Has both' then g.jordan_has_yahtzee and g.jordan_has_upper_bonus
            when 'Has neither' then not g.jordan_has_yahtzee and not g.jordan_has_upper_bonus
        end as jordan_cons
    from int_strategy_features g
    cross join miss_defs m
    cross join cons_defs c
),
flagged as (
    select
        *,
        (erin_miss and erin_cons) as erin_in_cell,
        (jordan_miss and jordan_cons) as jordan_in_cell
    from crossed
),
exclusive as (
    select *
    from flagged
    where erin_in_cell <> jordan_in_cell
),
agg as (
    select
        miss,
        miss_ord,
        consolation,
        cons_ord,
        count(*)::integer as n,
        sum(
            case
                when erin_in_cell and winner = 'erin' then 1
                when jordan_in_cell and winner = 'jordan' then 1
                else 0
            end
        )::integer as focal_wins,
        round(
            avg(
                case
                    when erin_in_cell and winner = 'erin' then 1.0
                    when jordan_in_cell and winner = 'jordan' then 1.0
                    else 0.0
                end
            ),
            3
        ) as focal_win_rate
    from exclusive
    group by miss, miss_ord, consolation, cons_ord
)
select
    m.miss,
    m.miss_ord,
    c.consolation,
    c.cons_ord,
    coalesce(a.n, 0)::integer as n,
    coalesce(a.focal_wins, 0)::integer as focal_wins,
    a.focal_win_rate,
    (coalesce(a.n, 0) < 10) as is_low_n,
    case
        when coalesce(a.n, 0) = 0 then '—'
        else
            round(100.0 * a.focal_win_rate)::integer
            || '% (n=' || a.n || ')'
    end as label
from miss_defs m
cross join cons_defs c
left join agg a
    on a.miss = m.miss
   and a.consolation = c.consolation
order by m.miss_ord, c.cons_ord
