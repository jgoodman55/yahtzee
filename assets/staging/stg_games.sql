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
    lower(trim(category))            as category,
    cast(score as integer)           as score,
    cast(recorded_total as integer)  as recorded_total
from raw_games
