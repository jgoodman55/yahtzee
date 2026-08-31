/* @bruin
name: fact_games
type: duckdb.sql
materialization:
  type: table
depends:
  - dim_player
  - stg_games
@bruin */

with agg as (
    select
        game_seq,
        player,
        sum(score) as computed_total,
        sum(case when category in ('ones','twos','threes','fours','fives','sixes','upper_bonus')
                 then score else 0 end)                                as upper_section_total,
        max(case when category = 'upper_bonus' then score end) > 0    as upper_bonus_hit,
        max(case when category = 'yahtzee' then score end) > 0        as scored_natural_yahtzee,
        coalesce(max(case when category = 'yahtzee_bonus' then score end), 0) / 100 as yahtzee_bonus_count,
        sum(case
                when category not in ('upper_bonus', 'yahtzee_bonus') and score = 0
                then 1 else 0
            end) as zeros_taken
    from stg_games
    group by game_seq, player
)
select
    dim.player_key,
    dim.display_name,
    a.game_seq,
    a.computed_total,
    a.upper_section_total,
    a.upper_bonus_hit,
    a.scored_natural_yahtzee,
    a.yahtzee_bonus_count,
    (case when a.scored_natural_yahtzee then 1 else 0 end) + a.yahtzee_bonus_count as total_yahtzees,
    a.zeros_taken
from dim_player dim
left join agg a
    on dim.player_key = a.player
order by a.game_seq, dim.player_key
