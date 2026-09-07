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
    case g.category
        when 'ones' then 1
        when 'twos' then 2
        when 'threes' then 3
        when 'fours' then 4
        when 'fives' then 5
        when 'sixes' then 6
        when 'three_of_a_kind' then 7
        when 'four_of_a_kind' then 8
        when 'full_house' then 9
        when 'small_straight' then 10
        when 'large_straight' then 11
        when 'chance' then 12
        when 'yahtzee' then 13
        else 99
    end as category_ord,
    count(*)::integer                                              as games,
    round(avg(g.score), 1)                                         as avg_score,
    sum(case when g.score = 0 then 1 else 0 end)::integer          as zero_count,
    round(avg(case when g.score = 0 then 1.0 else 0.0 end), 3)     as miss_rate
from stg_games g
inner join dim_player d
    on g.player = d.player_key
where g.category not in ('upper_bonus', 'yahtzee_bonus')
group by d.player_key, d.display_name, g.category
order by category_ord, d.player_key
