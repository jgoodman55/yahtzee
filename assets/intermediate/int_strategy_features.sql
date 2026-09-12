/* @bruin
name: int_strategy_features
type: duckdb.sql
materialization:
  type: table
depends:
  - stg_games
  - int_win_loss
@bruin */

-- Game-grain strategy flags shared by mart_strategy_swing,
-- mart_strategy_rescue, and mart_yz_matchup.
--
-- Why this intermediate exists (vs encoding the pivot only in DAC YAML):
-- the three Strategy visuals all need the same Erin/Jordan category flags
-- and winner. One wide game-grain table is the source of truth; the marts
-- only apply exclusive-feature / consolation / matchup grain. DAC YAML
-- stays a thin select.
--
-- Yahtzee here is the natural box (0/50), not bonus chips. Upper bonus is
-- the 0/35 box. Winner is int_win_loss (computed_total). Ties stay in the
-- grain (n=0 on the current seed).

with boxes as (
    select
        game_seq,
        player,
        max(case when category = 'yahtzee' then score end)        as yahtzee,
        max(case when category = 'yahtzee_bonus' then score end)  as yahtzee_bonus,
        max(case when category = 'upper_bonus' then score end)    as upper_bonus,
        max(case when category = 'large_straight' then score end) as large_straight,
        max(case when category = 'small_straight' then score end) as small_straight,
        max(case when category = 'full_house' then score end)     as full_house
    from stg_games
    group by game_seq, player
),
wide as (
    select
        e.game_seq,
        e.yahtzee        as erin_yahtzee,
        j.yahtzee        as jordan_yahtzee,
        e.yahtzee_bonus  as erin_yahtzee_bonus,
        j.yahtzee_bonus  as jordan_yahtzee_bonus,
        e.upper_bonus    as erin_upper_bonus,
        j.upper_bonus    as jordan_upper_bonus,
        e.large_straight as erin_large_straight,
        j.large_straight as jordan_large_straight,
        e.small_straight as erin_small_straight,
        j.small_straight as jordan_small_straight,
        e.full_house     as erin_full_house,
        j.full_house     as jordan_full_house
    from boxes e
    inner join boxes j
        on e.game_seq = j.game_seq
    where e.player = 'erin'
      and j.player = 'jordan'
)
select
    w.game_seq,
    wl.winner,
    wl.margin,
    w.erin_yahtzee,
    w.jordan_yahtzee,
    w.erin_yahtzee_bonus,
    w.jordan_yahtzee_bonus,
    w.erin_upper_bonus,
    w.jordan_upper_bonus,
    w.erin_large_straight,
    w.jordan_large_straight,
    w.erin_small_straight,
    w.jordan_small_straight,
    w.erin_full_house,
    w.jordan_full_house,
    (w.erin_yahtzee = 50)     as erin_has_yahtzee,
    (w.jordan_yahtzee = 50)   as jordan_has_yahtzee,
    (w.erin_upper_bonus = 35) as erin_has_upper_bonus,
    (w.jordan_upper_bonus = 35) as jordan_has_upper_bonus,
    (w.erin_yahtzee = 50)::integer
        + (w.jordan_yahtzee = 50)::integer as yz_holders,
    case
        when (w.erin_yahtzee = 50)::integer
           + (w.jordan_yahtzee = 50)::integer = 0 then 'none'
        when (w.erin_yahtzee = 50)::integer
           + (w.jordan_yahtzee = 50)::integer = 1 then 'one'
        else 'both'
    end as yz_matchup
from wide w
inner join int_win_loss wl using (game_seq)
order by w.game_seq
