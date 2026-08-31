/* @bruin
name: stg_games
type: duckdb.sql
materialization:
  type: view
depends:
  - raw_games
@bruin */

select
    cast(game_seq as integer) as game_seq,
    lower(trim(player))       as player,
    lower(trim(category))     as category,
    cast(score as integer)    as score
from raw_games
