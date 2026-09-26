/* @bruin
name: mart_location_stats
type: duckdb.sql
description: |
  Games and win rates by sheet location. One row per pub name, plus
  Unknown for games with no seed_game_locations row. pub_name matches
  seed_pubs.pub_name. Win rate is wins / games (ties stay in the
  denominator and are not wins).
materialization:
  type: table
depends:
  - int_win_loss
  - seed_game_locations
  - seed_pubs
custom_checks:
  - name: locations_match_seed_pubs
    description: Every logged pub_name exists on seed_pubs.
    query: |
      select count(*)
      from seed_game_locations l
      where not exists (
          select 1 from seed_pubs p
          where p.pub_name = l.pub_name
      )
    value: 0
  - name: location_games_cover_every_game
    description: Unknown plus logged locations equal the game count.
    query: |
      select count(*)
      from (
          select sum(games) as n from mart_location_stats
      ) s
      where s.n <> (select count(*) from int_win_loss)
    value: 0
@bruin */

with games as (
    select
        w.game_seq,
        w.winner,
        coalesce(l.pub_name, 'Unknown') as location
    from int_win_loss w
    left join seed_game_locations l
        on l.game_seq = w.game_seq
)
select
    location,
    count(*)::integer as games,
    sum(case when winner = 'erin' then 1 else 0 end)::integer as erin_wins,
    sum(case when winner = 'jordan' then 1 else 0 end)::integer as jordan_wins,
    sum(case when winner = 'tie' then 1 else 0 end)::integer as ties,
    round(
        sum(case when winner = 'erin' then 1 else 0 end) * 1.0 / count(*),
        3
    ) as erin_win_rate,
    round(
        sum(case when winner = 'jordan' then 1 else 0 end) * 1.0 / count(*),
        3
    ) as jordan_win_rate
from games
group by location
order by location = 'Unknown', games desc, location
