/* @bruin
name: mart_yz_matchup
type: duckdb.sql
materialization:
  type: table
depends:
  - int_strategy_features
@bruin */

-- Yahtzee matchup buckets for the stacked-bar Strategy chart.
--
-- Bucket = how many players scored the natural Yahtzee box (50):
--   none / one / both. Seed expectation ≈ 32 / 56 / 20.
-- Grain: matchup_bucket × winner (Erin / Jordan). Stack by winner,
-- not a pie. holder_* is only meaningful on the 'one' bucket — that
-- is the exclusive Yahtzee = 50 swing (~84%).

with bucket as (
    select
        yz_matchup,
        case yz_matchup
            when 'none' then 1
            when 'one' then 2
            else 3
        end as matchup_ord,
        case yz_matchup
            when 'none' then 'None'
            when 'one' then 'One'
            else 'Both'
        end as matchup_label,
        winner,
        case
            when yz_matchup = 'one'
                 and (
                     (erin_has_yahtzee and winner = 'erin')
                     or (jordan_has_yahtzee and winner = 'jordan')
                 )
                then 1
            else 0
        end as holder_win
    from int_strategy_features
),
totals as (
    select
        yz_matchup,
        count(*)::integer as n_bucket,
        sum(holder_win)::integer as holder_wins
    from bucket
    group by yz_matchup
)
select
    b.matchup_ord,
    b.yz_matchup,
    b.matchup_label,
    case b.winner
        when 'erin' then 'Erin'
        when 'jordan' then 'Jordan'
        else 'Tie'
    end as winner,
    count(*)::integer as n,
    t.n_bucket,
    t.holder_wins,
    case
        when b.yz_matchup = 'one'
            then round(t.holder_wins::double / nullif(t.n_bucket, 0), 3)
    end as holder_win_rate
from bucket b
inner join totals t using (yz_matchup)
group by
    b.matchup_ord,
    b.yz_matchup,
    b.matchup_label,
    b.winner,
    t.n_bucket,
    t.holder_wins
order by b.matchup_ord, b.winner
