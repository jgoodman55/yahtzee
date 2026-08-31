/* @bruin
name: stg_players
type: duckdb.sql
materialization:
  type: view
depends:
  - raw_players
@bruin */

select
    lower(trim(player_key)) as player_key,
    trim(display_name)      as display_name
from raw_players
