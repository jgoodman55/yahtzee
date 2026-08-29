/* @bruin
name: int_game_results
type: duckdb.sql
materialization:
  type: table
depends:
  - stg_games
@bruin */

with wide as (
    select
        game_seq,
        max(case when player = 'jordan'  then total_score end) as jordan_score,
        max(case when player = 'partner' then total_score end) as partner_score,
        max(case when player = 'jordan'  then upper_bonus_hit end) as jordan_bonus,
        max(case when player = 'partner' then upper_bonus_hit end) as partner_bonus,
        max(case when player = 'jordan'  then yahtzee_count end) as jordan_yahtzees,
        max(case when player = 'partner' then yahtzee_count end) as partner_yahtzees
    from stg_games
    group by 1
),
scored as (
    select
        game_seq,
        jordan_score,
        partner_score,
        jordan_bonus,
        partner_bonus,
        jordan_yahtzees,
        partner_yahtzees,
        case
            when jordan_score > partner_score then 'jordan'
            when partner_score > jordan_score then 'partner'
            else 'tie'
        end as winner,
        abs(jordan_score - partner_score) as margin
    from wide
),
with_lag as (
    select
        *,
        lag(winner) over (order by game_seq) as prev_winner
    from scored
)
select
    * exclude (prev_winner),
    -- current win streak length for the winner of this game, within their own results
    sum(case when winner = prev_winner then 1 else 0 end)
        over (order by game_seq rows between unbounded preceding and current row) as running_same_winner_count
from with_lag
order by game_seq
