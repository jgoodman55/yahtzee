/* @bruin
name: int_commentary
type: duckdb.sql
materialization:
  type: table
depends:
  - int_game_results
@bruin */

select
    game_seq,
    winner,
    margin,
    case
        when margin >= 60 then winner || ' delivered an absolute blowout (+' || margin || ')'
        when margin <= 5 and winner != 'tie' then 'nail-biter — ' || winner || ' scraped it by ' || margin
        when winner = 'tie' then 'a tie. how very diplomatic of you both.'
        else winner || ' took it by ' || margin
    end as margin_comment,
    case
        when jordan_yahtzees >= 2 then 'jordan hoarding Yahtzees like it''s a competitive sport (it is)'
        when partner_yahtzees >= 2 then 'multiple Yahtzees for partner — showoff'
        when jordan_yahtzees = 0 and partner_yahtzees = 0 then 'zero Yahtzees between you both, embarrassing'
        else null
    end as yahtzee_comment,
    case
        when not jordan_bonus and not partner_bonus then 'nobody hit the upper bonus, the 1s and 2s strategy is not working'
        when jordan_bonus and not partner_bonus then 'jordan banked the 35pt bonus, partner did not'
        when partner_bonus and not jordan_bonus then 'partner banked the 35pt bonus, jordan did not'
        else null
    end as bonus_comment,
    case
        when running_same_winner_count >= 3 then winner || ' is on a streak — someone needs to step up'
        else null
    end as streak_comment
from int_game_results
