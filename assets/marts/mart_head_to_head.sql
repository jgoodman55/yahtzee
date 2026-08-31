/* @bruin
name: mart_head_to_head
type: duckdb.sql
materialization:
  type: table
depends:
  - int_win_loss
  - int_commentary
@bruin */

select
    w.game_seq,
    w.jordan_score,
    w.erin_score,
    w.winner,
    w.margin,
    w.jordan_cum_wins,
    w.erin_cum_wins,
    c.margin_comment,
    c.yahtzee_comment,
    c.bonus_comment,
    c.streak_comment
from int_win_loss w
left join int_commentary c using (game_seq)
order by w.game_seq
