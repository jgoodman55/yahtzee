/* @bruin
name: stg_games
type: duckdb.sql
materialization:
  type: view
depends:
  - raw_games
@bruin */

select
    cast(game_seq as integer)        as game_seq,
    lower(trim(player))              as player,
    cast(total_score as integer)     as total_score,
    cast(upper_bonus_hit as boolean) as upper_bonus_hit,
    cast(yahtzee_count as integer)   as yahtzee_count,
    cast(zeros_taken as integer)     as zeros_taken
from raw_games
