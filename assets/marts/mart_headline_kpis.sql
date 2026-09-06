/* @bruin
name: mart_headline_kpis
type: duckdb.sql
materialization:
  type: table
depends:
  - mart_player_kpis
  - fact_games
  - int_win_loss
@bruin */

-- Single-row headline for Overview metric widgets.
--
-- Score choice: high_score, lifetime_points, avg/median use recorded_total
-- (max/sum/avg of the grand total written on the card). Wins, margin, and
-- winner still come from int_win_loss (computed_total). Seed game 2 Erin is
-- the known mismatch: recorded 180 vs computed 175.
--
-- Yahtzees: 1 when the yahtzee box is 50, plus yahtzee_bonus / 100.
-- Multi-yahtzee player-games: total_yahtzees >= 2 (yahtzee_bonus >= 100).

select
    (select count(*)::integer from int_win_loss)                   as total_games,
    (select count(*)::integer from int_win_loss where winner = 'tie') as ties,
    e.wins                                                         as erin_wins,
    j.wins                                                         as jordan_wins,
    e.high_score                                                   as erin_high_score,
    j.high_score                                                   as jordan_high_score,
    (e.total_yahtzees + j.total_yahtzees)::integer                 as total_yahtzees,
    e.upper_bonus_hits                                             as erin_upper_bonuses,
    j.upper_bonus_hits                                             as jordan_upper_bonuses,
    (e.multi_yahtzee_games + j.multi_yahtzee_games)::integer       as multi_yahtzee_player_games,
    e.lifetime_points                                              as erin_lifetime_points,
    j.lifetime_points                                              as jordan_lifetime_points,
    e.avg_score                                                    as erin_avg_score,
    j.avg_score                                                    as jordan_avg_score,
    e.median_score                                                 as erin_median_score,
    j.median_score                                                 as jordan_median_score,
    e.upper_bonus_rate                                             as erin_bonus_rate,
    j.upper_bonus_rate                                             as jordan_bonus_rate,
    e.yahtzees_per_game                                            as erin_yahtzees_per_game,
    j.yahtzees_per_game                                            as jordan_yahtzees_per_game,
    e.avg_upper_pre_bonus                                          as erin_avg_upper_pre_bonus,
    j.avg_upper_pre_bonus                                          as jordan_avg_upper_pre_bonus,
    e.avg_chance                                                   as erin_avg_chance,
    j.avg_chance                                                   as jordan_avg_chance,
    (e.totals_mismatch_count + j.totals_mismatch_count)::integer   as totals_mismatch_count,
    e.current_win_streak                                           as erin_current_streak,
    j.current_win_streak                                           as jordan_current_streak,
    e.longest_win_streak                                           as erin_longest_streak,
    j.longest_win_streak                                           as jordan_longest_streak
from mart_player_kpis e
inner join mart_player_kpis j
    on e.player_key = 'erin'
   and j.player_key = 'jordan'
