from __future__ import annotations

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


def plot_temporal_trends(df: pd.DataFrame, output_path: str) -> None:
    """Generate temporal trend plots (monthly and diurnal) for each parameter."""
    sns.set_theme(style="whitegrid")

    # Monthly trend
    monthly = (
        df.groupby(["parameter", "month"])  # type: ignore
        ["value"].mean()
        .reset_index()
        .sort_values(["parameter", "month"])
    )
    g = sns.FacetGrid(monthly, col="parameter", sharey=False, height=3, aspect=1.6)
    g.map_dataframe(sns.lineplot, x="month", y="value", marker="o")
    g.set_axis_labels("Month", "Mean concentration")
    g.fig.suptitle("Monthly mean concentration by parameter", y=1.05)
    g.savefig(output_path.replace(".png", "_monthly.png"), bbox_inches="tight")
    plt.close(g.fig)

    # Diurnal trend
    diurnal = df.groupby(["parameter", "hour"])  # type: ignore
    diurnal = diurnal["value"].mean().reset_index().sort_values(["parameter", "hour"])
    g2 = sns.FacetGrid(diurnal, col="parameter", sharey=False, height=3, aspect=1.6)
    g2.map_dataframe(sns.lineplot, x="hour", y="value", marker="o")
    g2.set_axis_labels("Hour", "Mean concentration")
    g2.fig.suptitle("Diurnal mean concentration by parameter", y=1.05)
    g2.savefig(output_path.replace(".png", "_diurnal.png"), bbox_inches="tight")
    plt.close(g2.fig)
