/* @bruin
name: mart_player_kpis
type: duckdb.sql
materialization:
  type: table
depends:
  - fact_games
  - int_win_loss
@bruin */

-- Lifetime stats at player grain. High scores / points use recorded_total
-- (the grand total written on the card). Wins stay on int_win_loss, which
-- compares computed_total so a totals mismatch cannot silently flip a result.

with ordered as (
    select
        game_seq,
        winner,
        lag(winner) over (order by game_seq) as prev_winner
    from int_win_loss
),
flagged as (
    select
        game_seq,
        winner,
        case
            when prev_winner is null or winner <> prev_winner then 1
            else 0
        end as new_island
    from ordered
),
streaks as (
    select
        game_seq,
        winner,
        sum(new_island) over (order by game_seq rows unbounded preceding) as island_id
    from flagged
),
island_len as (
    select
        winner,
        island_id,
        count(*) as streak_len,
        max(game_seq) as end_seq
    from streaks
    group by winner, island_id
),
longest as (
    select
        winner as player_key,
        max(streak_len) as longest_win_streak
    from island_len
    where winner in ('erin', 'jordan')
    group by winner
),
current as (
    select
        winner as player_key,
        streak_len as current_win_streak
    from island_len
    where end_seq = (select max(game_seq) from int_win_loss)
      and winner in ('erin', 'jordan')
),
wins as (
    select
        winner as player_key,
        count(*) as wins
    from int_win_loss
    where winner in ('erin', 'jordan')
    group by winner
)
select
    f.player_key,
    f.display_name,
    count(*)::integer                                              as games_played,
    coalesce(max(w.wins), 0)::integer                              as wins,
    max(f.recorded_total)::integer                                 as high_score,
    sum(f.recorded_total)::integer                                 as lifetime_points,
    round(avg(f.recorded_total), 1)                                as avg_score,
    median(f.recorded_total)::integer                              as median_score,
    sum(f.total_yahtzees)::integer                                 as total_yahtzees,
    sum(case when f.has_multi_yahtzee then 1 else 0 end)::integer  as multi_yahtzee_games,
    sum(case when f.upper_bonus_hit then 1 else 0 end)::integer    as upper_bonus_hits,
    round(avg(case when f.upper_bonus_hit then 1.0 else 0.0 end), 3) as upper_bonus_rate,
    round(avg(f.total_yahtzees), 2)                                as yahtzees_per_game,
    round(avg(f.upper_pre_bonus), 1)                               as avg_upper_pre_bonus,
    round(avg(f.chance_score), 1)                                  as avg_chance,
    sum(case when not f.totals_match then 1 else 0 end)::integer   as totals_mismatch_count,
    coalesce(max(c.current_win_streak), 0)::integer                as current_win_streak,
    coalesce(max(l.longest_win_streak), 0)::integer                as longest_win_streak
from fact_games f
left join wins w
    on f.player_key = w.player_key
left join current c
    on f.player_key = c.player_key
left join longest l
    on f.player_key = l.player_key
group by f.player_key, f.display_name
order by f.player_key
