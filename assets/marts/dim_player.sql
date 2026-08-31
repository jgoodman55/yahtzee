/* @bruin
name: dim_player
type: duckdb.sql
materialization:
  type: table
depends:
  - stg_players
@bruin */

select
    player_key,
    display_name
from stg_players
