/* @bruin
name: stg_game_totals
type: duckdb.sql
materialization:
  type: view
depends:
  - raw_game_totals
@bruin */

select
    cast(game_seq as integer)        as game_seq,
    lower(trim(player))              as player,
    cast(recorded_total as integer)  as recorded_total
from raw_game_totals
