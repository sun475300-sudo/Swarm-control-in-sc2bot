# Phase 420: Marimo - SC2 Reactive Analysis Notebook
# Marimo reactive notebook for SC2 match analysis with interactive widgets

import marimo as mo
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime, timedelta

# ============================================================
# App Definition
# ============================================================

app = mo.App(width="full")

# ============================================================
# Cell 1: Title and Introduction
# ============================================================


@app.cell
def title_cell():
    return mo.md("""
    # SC2 Bot Performance Analysis
    **Zerg Bot** | Reactive analytics powered by Marimo

    Use the controls below to filter and explore match data.
    """)


# ============================================================
# Cell 2: Generate Sample Match Data
# ============================================================


@app.cell
def generate_data():
    rng = np.random.default_rng(42)
    n = 200

    dates = [datetime(2026, 1, 1) + timedelta(hours=i * 3) for i in range(n)]
    df = pd.DataFrame(
        {
            "date": dates,
            "map": rng.choice(
                ["Equilibrium LE", "Site Delta LE", "Gresvan LE", "Goldenaura LE"], n
            ),
            "race": rng.choice(["ZvT", "ZvP", "ZvZ"], n),
            "result": rng.choice(["Win", "Loss"], n, p=[0.58, 0.42]),
            "duration": rng.integers(120, 900, n),
            "apm": rng.integers(100, 300, n),
            "mmr": np.cumsum(rng.integers(-20, 25, n)) + 4700,
        }
    )
    return (df,)


# ============================================================
# Cell 3: Time Range Slider
# ============================================================


@app.cell
def time_range_slider():
    slider = mo.ui.slider(
        start=0,
        stop=200,
        step=10,
        value=200,
        label="Number of Recent Games",
        full_width=True,
    )
    return (slider,)


# ============================================================
# Cell 4: Race Filter
# ============================================================


@app.cell
def race_filter():
    race_dropdown = mo.ui.dropdown(
        options=["All", "ZvT", "ZvP", "ZvZ"],
        value="All",
        label="Matchup Filter",
    )
    return (race_dropdown,)


# ============================================================
# Cell 5: Map Filter Multiselect
# ============================================================


@app.cell
def map_filter():
    map_select = mo.ui.multiselect(
        options=["Equilibrium LE", "Site Delta LE", "Gresvan LE", "Goldenaura LE"],
        value=["Equilibrium LE", "Site Delta LE", "Gresvan LE", "Goldenaura LE"],
        label="Map Filter",
    )
    return (map_select,)


# ============================================================
# Cell 6: Filtered DataFrame
# ============================================================


@app.cell
def filtered_data(df, slider, race_dropdown, map_select):
    filtered = df.tail(slider.value)

    if race_dropdown.value != "All":
        filtered = filtered[filtered["race"] == race_dropdown.value]

    if map_select.value:
        filtered = filtered[filtered["map"].isin(map_select.value)]

    return (filtered,)


# ============================================================
# Cell 7: Summary Stats
# ============================================================


@app.cell
def summary_stats(filtered):
    if len(filtered) == 0:
        return (mo.md("No data matching current filters."),)

    wins = (filtered["result"] == "Win").sum()
    total = len(filtered)
    wr = wins / total * 100
    avg_apm = filtered["apm"].mean()
    avg_dur = filtered["duration"].mean() / 60

    stats_md = mo.md(f"""
    ## Summary Statistics
    | Metric | Value |
    |--------|-------|
    | Games  | {total} |
    | Wins   | {wins} |
    | Win Rate | **{wr:.1f}%** |
    | Avg APM  | {avg_apm:.0f} |
    | Avg Duration | {avg_dur:.1f} min |
    | Current MMR  | {filtered['mmr'].iloc[-1] if len(filtered) > 0 else '—'} |
    """)
    return (stats_md,)


# ============================================================
# Cell 8: Match History Table
# ============================================================


@app.cell
def match_table(filtered):
    display_df = filtered.tail(20).copy()
    display_df["date"] = display_df["date"].dt.strftime("%m/%d %H:%M")
    display_df["duration"] = display_df["duration"].apply(
        lambda s: f"{s//60}:{s%60:02d}"
    )

    table = mo.ui.table(
        data=display_df[
            ["date", "map", "race", "result", "duration", "apm", "mmr"]
        ].to_dict("records"),
        label="Recent Match History",
        selection=None,
    )
    return (table,)


# ============================================================
# Cell 9: MMR Trend Chart (Altair)
# ============================================================


@app.cell
def mmr_chart(filtered):
    if len(filtered) < 2:
        return (mo.md("Not enough data for MMR chart."),)

    chart_df = filtered.reset_index(drop=True).reset_index()
    chart_df.columns = (
        list(chart_df.columns[:-1]) + ["mmr"]
        if "mmr" in chart_df.columns
        else chart_df.columns
    )
    chart_df["game_num"] = range(len(chart_df))

    chart = alt.Chart(chart_df).mark_line(color="#4c72b0", strokeWidth=2).encode(
        x=alt.X("game_num:Q", title="Game Number"),
        y=alt.Y("mmr:Q", title="MMR", scale=alt.Scale(zero=False)),
        tooltip=["game_num", "mmr", "result", "race"],
    ).properties(
        title="MMR Progression",
        width=700,
        height=250,
    ) + alt.Chart(
        chart_df
    ).mark_point(
        size=40,
    ).encode(
        x="game_num:Q",
        y="mmr:Q",
        color=alt.Color(
            "result:N",
            scale=alt.Scale(domain=["Win", "Loss"], range=["#2ca02c", "#d62728"]),
        ),
    )

    return (mo.ui.altair_chart(chart, label="MMR Trend"),)


# ============================================================
# Cell 10: Win Rate by Matchup (Altair Bar Chart)
# ============================================================


@app.cell
def win_rate_chart(filtered):
    if len(filtered) < 5:
        return (mo.md("Not enough data for win rate chart."),)

    wr_df = (
        filtered.groupby("race")
        .apply(
            lambda x: pd.Series(
                {
                    "win_rate": (x["result"] == "Win").mean() * 100,
                    "games": len(x),
                }
            )
        )
        .reset_index()
    )

    chart = (
        alt.Chart(wr_df)
        .mark_bar()
        .encode(
            x=alt.X("race:N", title="Matchup"),
            y=alt.Y(
                "win_rate:Q", title="Win Rate (%)", scale=alt.Scale(domain=[0, 100])
            ),
            color=alt.Color("race:N", scale=alt.Scale(scheme="category10")),
            tooltip=["race", alt.Tooltip("win_rate:Q", format=".1f"), "games"],
        )
        .properties(title="Win Rate by Matchup", width=400, height=250)
    )

    return (mo.ui.altair_chart(chart, label="Win Rate by Matchup"),)


# ============================================================
# Cell 11: APM Distribution (Altair Histogram)
# ============================================================


@app.cell
def apm_chart(filtered):
    if len(filtered) < 5:
        return (mo.md("Not enough data."),)

    chart = (
        alt.Chart(filtered)
        .mark_bar(opacity=0.7)
        .encode(
            x=alt.X("apm:Q", bin=alt.Bin(maxbins=20), title="APM"),
            y=alt.Y("count():Q", title="Games"),
            color=alt.Color(
                "result:N",
                scale=alt.Scale(domain=["Win", "Loss"], range=["#2ca02c", "#d62728"]),
            ),
            tooltip=["result", "count()"],
        )
        .properties(title="APM Distribution by Outcome", width=500, height=250)
    )

    return (mo.ui.altair_chart(chart, label="APM Distribution"),)


# ============================================================
# Cell 12: Layout Assembly
# ============================================================


@app.cell
def layout(
    title_cell,
    slider,
    race_dropdown,
    map_select,
    summary_stats,
    match_table,
    mmr_chart,
    win_rate_chart,
    apm_chart,
):
    return mo.vstack(
        [
            title_cell,
            mo.hstack([slider, race_dropdown, map_select], gap=2),
            summary_stats,
            mmr_chart,
            mo.hstack([win_rate_chart, apm_chart]),
            match_table,
        ]
    )


# ============================================================
# Entry Point
# ============================================================

if __name__ == "__main__":
    app.run()
