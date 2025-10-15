from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from src.utils.io import ensure_directory, save_figure


@dataclass(frozen=True)
class TemporalConfig:
    parameter: str = "pm25"


def _prep(df: pd.DataFrame, parameter: str) -> pd.DataFrame:
    sub = df[df["parameter"].str.lower() == parameter.lower()].copy()
    if sub.empty:
        return sub
    sub["timestamp"] = pd.to_datetime(sub["timestamp"], utc=True, errors="coerce")
    sub = sub.dropna(subset=["timestamp"])  # ensure
    sub["date"] = sub["timestamp"].dt.date
    sub["hour"] = sub["timestamp"].dt.hour
    sub["dow"] = sub["timestamp"].dt.dayofweek
    sub["month"] = sub["timestamp"].dt.month
    return sub


def daily_trend(df: pd.DataFrame, cfg: TemporalConfig, output_png: str) -> pd.DataFrame:
    data = _prep(df, cfg.parameter)
    if data.empty:
        return data
    daily = data.groupby("date")["value"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(9, 3))
    sns.lineplot(data=daily, x="date", y="value", ax=ax)
    ax.set_title(f"Daily trend of {cfg.parameter.upper()}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Mean concentration")
    save_figure(fig, output_png)
    return daily


def hourly_profile(df: pd.DataFrame, cfg: TemporalConfig, output_png: str) -> pd.DataFrame:
    data = _prep(df, cfg.parameter)
    if data.empty:
        return data
    hourly = data.groupby("hour")["value"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(6, 3))
    sns.barplot(data=hourly, x="hour", y="value", ax=ax, color="#69b3a2")
    ax.set_title(f"Hourly profile of {cfg.parameter.upper()}")
    ax.set_xlabel("Hour of day")
    ax.set_ylabel("Mean concentration")
    save_figure(fig, output_png)
    return hourly


def weekday_profile(df: pd.DataFrame, cfg: TemporalConfig, output_png: str) -> pd.DataFrame:
    data = _prep(df, cfg.parameter)
    if data.empty:
        return data
    weekday = data.groupby("dow")["value"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(6, 3))
    sns.barplot(data=weekday, x="dow", y="value", ax=ax, palette="viridis")
    ax.set_title(f"Weekday profile of {cfg.parameter.upper()} (0=Mon)")
    ax.set_xlabel("Day of week")
    ax.set_ylabel("Mean concentration")
    save_figure(fig, output_png)
    return weekday


def monthly_profile(df: pd.DataFrame, cfg: TemporalConfig, output_png: str) -> pd.DataFrame:
    data = _prep(df, cfg.parameter)
    if data.empty:
        return data
    monthly = data.groupby("month")["value"].mean().reset_index()

    fig, ax = plt.subplots(figsize=(6, 3))
    sns.barplot(data=monthly, x="month", y="value", ax=ax, palette="magma")
    ax.set_title(f"Monthly profile of {cfg.parameter.upper()}")
    ax.set_xlabel("Month")
    ax.set_ylabel("Mean concentration")
    save_figure(fig, output_png)
    return monthly
