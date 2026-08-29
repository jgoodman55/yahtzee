/* @bruin
name: mart_head_to_head
type: duckdb.sql
materialization:
  type: table
depends:
  - int_game_results
  - int_commentary
@bruin */

select
    r.game_seq,
    r.jordan_score,
    r.partner_score,
    r.winner,
    r.margin,
    sum(case when r.winner = 'jordan'  then 1 else 0 end)
        over (order by r.game_seq rows between unbounded preceding and current row) as jordan_cum_wins,
    sum(case when r.winner = 'partner' then 1 else 0 end)
        over (order by r.game_seq rows between unbounded preceding and current row) as partner_cum_wins,
    c.margin_comment,
    c.yahtzee_comment,
    c.bonus_comment,
    c.streak_comment
from int_game_results r
left join int_commentary c using (game_seq)
order by r.game_seq
