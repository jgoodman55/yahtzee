/* @bruin
name: mart_game_trends
type: duckdb.sql
materialization:
  type: table
depends:
  - fact_games
  - int_win_loss
@bruin */

-- Game-sequence grain for race charts and per-game zero / yahtzee trends.
-- Cumulative windows are ordered by game_seq so they stay stable as raw_games
-- grows toward ~100 rows.

with wide as (
    select
        game_seq,
        max(case when player_key = 'erin' then recorded_total end)     as erin_recorded_total,
        max(case when player_key = 'jordan' then recorded_total end)   as jordan_recorded_total,
        max(case when player_key = 'erin' then computed_total end)     as erin_computed_total,
        max(case when player_key = 'jordan' then computed_total end)   as jordan_computed_total,
        max(case when player_key = 'erin' then total_yahtzees end)     as erin_yahtzees,
        max(case when player_key = 'jordan' then total_yahtzees end)   as jordan_yahtzees,
        max(case when player_key = 'erin' then
            case when has_multi_yahtzee then 1 else 0 end end)         as erin_multi_yahtzee,
        max(case when player_key = 'jordan' then
            case when has_multi_yahtzee then 1 else 0 end end)         as jordan_multi_yahtzee,
        max(case when player_key = 'erin' then zeros_taken end)        as erin_zeros,
        max(case when player_key = 'jordan' then zeros_taken end)      as jordan_zeros,
        max(case when player_key = 'erin' then
            case when upper_bonus_hit then 1 else 0 end end)           as erin_upper_bonus,
        max(case when player_key = 'jordan' then
            case when upper_bonus_hit then 1 else 0 end end)           as jordan_upper_bonus
    from fact_games
    group by game_seq
)
select
    w.game_seq,
    wl.winner,
    wl.margin,
    w.erin_recorded_total,
    w.jordan_recorded_total,
    w.erin_computed_total,
    w.jordan_computed_total,
    wl.erin_cum_wins,
    wl.jordan_cum_wins,
    w.erin_yahtzees,
    w.jordan_yahtzees,
    sum(w.erin_yahtzees) over (order by w.game_seq rows unbounded preceding)
        as erin_cum_yahtzees,
    sum(w.jordan_yahtzees) over (order by w.game_seq rows unbounded preceding)
        as jordan_cum_yahtzees,
    w.erin_multi_yahtzee,
    w.jordan_multi_yahtzee,
    sum(w.erin_multi_yahtzee) over (order by w.game_seq rows unbounded preceding)
        as erin_cum_multi_yahtzee_games,
    sum(w.jordan_multi_yahtzee) over (order by w.game_seq rows unbounded preceding)
        as jordan_cum_multi_yahtzee_games,
    w.erin_zeros,
    w.jordan_zeros,
    w.erin_upper_bonus,
    w.jordan_upper_bonus
from wide w
inner join int_win_loss wl using (game_seq)
order by w.game_seq
