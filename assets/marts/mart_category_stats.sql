/* @bruin
name: mart_category_stats
type: duckdb.sql
materialization:
  type: table
depends:
  - stg_games
  - dim_player
@bruin */

-- Per-player category averages and miss rates.
-- Zeros exclude upper_bonus and yahtzee_bonus (those boxes are 0/35 and 0/100n,
-- not "scratched" scoring categories).

select
    d.player_key,
    d.display_name,
    g.category,
    case
        when g.category in ('ones', 'twos', 'threes', 'fours', 'fives', 'sixes')
            then 'upper'
        else 'lower'
    end as section,
    g.category in ('full_house', 'small_straight', 'large_straight', 'yahtzee')
        as is_conversion_box,
    count(*)::integer                                              as games,
    round(avg(g.score), 1)                                         as avg_score,
    sum(case when g.score = 0 then 1 else 0 end)::integer          as zero_count,
    round(avg(case when g.score = 0 then 1.0 else 0.0 end), 3)     as miss_rate
from stg_games g
inner join dim_player d
    on g.player = d.player_key
where g.category not in ('upper_bonus', 'yahtzee_bonus')
group by d.player_key, d.display_name, g.category
order by section, g.category, d.player_key
