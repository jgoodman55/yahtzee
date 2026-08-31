/* @bruin
name: int_win_loss
type: duckdb.sql
materialization:
  type: table
depends:
  - fact_games
@bruin */

with wide as (
    select
        game_seq,
        max(case when player_key = 'jordan'  then computed_total end) as jordan_score,
        max(case when player_key = 'erin' then computed_total end) as erin_score
    from fact_games
    group by game_seq
),
scored as (
    select
        *,
        case
            when jordan_score > erin_score then 'jordan'
            when erin_score > jordan_score then 'erin'
            else 'tie'
        end as winner,
        abs(jordan_score - erin_score) as margin
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
    sum(case when winner = prev_winner then 1 else 0 end)
        over (order by game_seq rows between unbounded preceding and current row) as running_same_winner_count,
    sum(case when winner = 'jordan'  then 1 else 0 end)
        over (order by game_seq rows between unbounded preceding and current row) as jordan_cum_wins,
    sum(case when winner = 'erin' then 1 else 0 end)
        over (order by game_seq rows between unbounded preceding and current row) as erin_cum_wins
from with_lag
order by game_seq
