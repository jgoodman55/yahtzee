/* @bruin
name: mart_yz_matchup
type: duckdb.sql
materialization:
  type: table
depends:
  - int_strategy_features
@bruin */

-- Exclusive Yahtzee holder outcomes for the Strategy stacked bar.
--
-- Cohort: games where exactly one of Erin/Jordan scored Yahtzee = 50
-- (yz_matchup = 'one'). None / both are excluded from this mart.
-- Grain: holder × outcome (Holder won / Upset).
-- Rate: that holder's win rate. Combined exclusive holder is 47/56 ≈ 84%.
--
-- Seed grounding (n=108, 0 ties) — verify after rebuild:
--   Erin alone   23W / 8L  of 31  ≈ 74%
--   Jordan alone 24W / 1L  of 25  ≈ 96%
--   combined     47 / 56         ≈ 84%

with exclusive as (
    select
        case
            when erin_has_yahtzee then 'Erin'
            else 'Jordan'
        end as holder,
        case
            when (erin_has_yahtzee and winner = 'erin')
              or (jordan_has_yahtzee and winner = 'jordan')
                then 'Holder won'
            else 'Upset'
        end as outcome
    from int_strategy_features
    where yz_matchup = 'one'
),
holder_defs as (
    select 1 as holder_ord, 'Erin' as holder, 'Erin alone has Yahtzee' as holder_label
    union all
    select 2, 'Jordan', 'Jordan alone has Yahtzee'
),
outcome_defs as (
    select 1 as outcome_ord, 'Holder won' as outcome
    union all
    select 2, 'Upset'
),
agg as (
    select
        holder,
        outcome,
        count(*)::integer as n
    from exclusive
    group by holder, outcome
),
holder_tot as (
    select
        holder,
        sum(n)::integer as n_holder,
        sum(case when outcome = 'Holder won' then n else 0 end)::integer as holder_wins
    from agg
    group by holder
)
select
    h.holder_ord,
    h.holder,
    h.holder_label,
    o.outcome_ord,
    o.outcome,
    coalesce(a.n, 0)::integer as n,
    t.n_holder,
    t.holder_wins,
    (t.n_holder - t.holder_wins)::integer as holder_losses,
    round(t.holder_wins::double / nullif(t.n_holder, 0), 3) as holder_win_rate,
    round(100.0 * t.holder_wins / nullif(t.n_holder, 0))::integer
        || '% (' || t.holder_wins || '/' || t.n_holder || ')' as label,
    case
        when o.outcome = 'Upset' then 'Upset'
        when h.holder = 'Erin' then 'Erin won'
        else 'Jordan won'
    end as stack_key
from holder_defs h
cross join outcome_defs o
left join agg a
    on a.holder = h.holder
   and a.outcome = o.outcome
inner join holder_tot t
    on t.holder = h.holder
order by h.holder_ord, o.outcome_ord
