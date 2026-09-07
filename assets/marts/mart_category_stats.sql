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
--
-- Upper faces (ones–sixes): avg_dice_count = avg(score / face_value) on a 0–5
-- dice scale (e.g. 18 on sixes → 3). Conversion boxes stay on miss_rate;
-- lower sum boxes (3oak / 4oak / chance) keep avg_score in points.

with scored as (
    select
        d.player_key,
        d.display_name,
        g.category,
        g.score,
        case
            when g.category in ('ones', 'twos', 'threes', 'fours', 'fives', 'sixes')
                then 'upper'
            else 'lower'
        end as section,
        g.category in ('full_house', 'small_straight', 'large_straight', 'yahtzee')
            as is_conversion_box,
        g.category in ('three_of_a_kind', 'four_of_a_kind', 'chance')
            as is_sum_box,
        case g.category
            when 'ones' then 1
            when 'twos' then 2
            when 'threes' then 3
            when 'fours' then 4
            when 'fives' then 5
            when 'sixes' then 6
        end as face_value,
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
        end as category_ord
    from stg_games g
    inner join dim_player d
        on g.player = d.player_key
    where g.category not in ('upper_bonus', 'yahtzee_bonus')
)

select
    player_key,
    display_name,
    category,
    section,
    is_conversion_box,
    is_sum_box,
    face_value,
    category_ord,
    count(*)::integer                                              as games,
    round(avg(score), 1)                                           as avg_score,
    round(
        avg(case
            when face_value is not null then score::double / face_value
        end),
        1
    )                                                              as avg_dice_count,
    sum(case when score = 0 then 1 else 0 end)::integer            as zero_count,
    round(avg(case when score = 0 then 1.0 else 0.0 end), 3)       as miss_rate
from scored
group by
    player_key,
    display_name,
    category,
    section,
    is_conversion_box,
    is_sum_box,
    face_value,
    category_ord
order by category_ord, player_key
