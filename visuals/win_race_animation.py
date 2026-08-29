"""
Renders an animated cumulative-wins race, ordered by game_seq (not date,
since we don't have reliable dates). Captions come straight from
mart_head_to_head's precomputed commentary columns — nothing is generated
at render time, so the output is reproducible.

Run standalone (outside Bruin) once mart_head_to_head exists in the DuckDB
file:

    pip install duckdb pandas matplotlib
    python win_race_animation.py

Outputs win_race.mp4 (falls back to .gif if ffmpeg isn't available).
"""

import duckdb
import matplotlib.pyplot as plt
import matplotlib.animation as animation

DB_PATH = "../yahtzee.duckdb"
PLAYERS = ["jordan", "partner"]
COLORS = {"jordan": "#3B82F6", "partner": "#EF4444"}


def load_data():
    con = duckdb.connect(DB_PATH, read_only=True)
    df = con.execute("select * from mart_head_to_head order by game_seq").df()
    con.close()
    return df


def build_caption(row) -> str:
    parts = [c for c in (row.get("streak_comment"), row.get("margin_comment")) if c]
    return "  •  ".join(parts) if parts else f"Game {int(row['game_seq'])}"


def animate(df):
    fig, ax = plt.subplots(figsize=(8, 5))
    max_wins = max(df["jordan_cum_wins"].max(), df["partner_cum_wins"].max()) + 1

    def draw(frame_idx):
        ax.clear()
        window = df.iloc[: frame_idx + 1]
        row = window.iloc[-1]

        bars = ax.bar(
            PLAYERS,
            [row["jordan_cum_wins"], row["partner_cum_wins"]],
            color=[COLORS[p] for p in PLAYERS],
        )
        for bar, val in zip(bars, [row["jordan_cum_wins"], row["partner_cum_wins"]]):
            ax.text(bar.get_x() + bar.get_width() / 2, val + 0.1, str(int(val)),
                     ha="center", fontweight="bold")

        ax.set_ylim(0, max_wins)
        ax.set_title(f"Game {int(row['game_seq'])} of {len(df)}", fontsize=13)
        ax.set_ylabel("Cumulative wins")
        ax.text(
            0.5, -0.15, build_caption(row),
            transform=ax.transAxes, ha="center", fontsize=10, style="italic", wrap=True,
        )

    anim = animation.FuncAnimation(fig, draw, frames=len(df), interval=900, repeat=False)

    try:
        anim.save("win_race.mp4", writer="ffmpeg", fps=1.2)
        print("Saved win_race.mp4")
    except (FileNotFoundError, RuntimeError):
        anim.save("win_race.gif", writer="pillow", fps=1.2)
        print("ffmpeg not found — saved win_race.gif instead (pip install pillow)")


if __name__ == "__main__":
    animate(load_data())
