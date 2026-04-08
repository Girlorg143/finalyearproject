import pathlib

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


DATA_DIR = pathlib.Path(__file__).resolve().parent / "agri_supply_chain_datasets"


def load_datasets():
    seasonal = pd.read_csv(DATA_DIR / "crop_freshness_shelf_life_seasonal_corrected.csv")
    legacy = pd.read_csv(DATA_DIR / "crop_freshness_shelf_life.csv")
    climate = pd.read_csv(DATA_DIR / "warehouse_climate_timeseries.csv")
    return seasonal, legacy, climate


def fig1_correlation_heatmap(seasonal: pd.DataFrame, legacy: pd.DataFrame):
    """Correlation heatmap: temperature, humidity, shelf life.

    This shows how shelf life (Max_Shelf_Life_Days) relates to optimal
    temperature and humidity, grounding the freshness model in the
    underlying crop metadata.
    """

    cols_legacy = [
        "Max_Shelf_Life_Days",
        "Optimal_Temp_C",
        "Optimal_Humidity_%",
    ]
    legacy_sub = legacy[cols_legacy].copy()

    cols_seasonal = [
        "Max_Shelf_Life_Days",
        "Optimal_Temp_C",
        "Optimal_Humidity_%",
    ]
    seasonal_sub = seasonal[cols_seasonal].copy()

    combined = pd.concat([legacy_sub, seasonal_sub], ignore_index=True)
    corr = combined.corr(numeric_only=True)

    plt.figure(figsize=(6, 5))
    sns.heatmap(corr, annot=True, cmap="coolwarm", fmt=".2f")
    plt.title("Correlation: Shelf Life vs Temperature & Humidity")
    plt.tight_layout()
    plt.savefig("fig1_correlation_heatmap.png", dpi=150)
    plt.close()


def fig2_boxplot_shelf_life_by_season(seasonal: pd.DataFrame):
    """Box plot of shelf life distribution across Kharif / Rabi / Zaid.

    This visualizes how Max_Shelf_Life_Days varies by growing season,
    supporting the seasonal warning logic in the farmer dashboard.
    """

    df = seasonal.copy()
    # Normalize season labels
    df["Season"] = df["Season"].astype(str).str.strip().str.title()

    plt.figure(figsize=(7, 5))
    sns.boxplot(data=df, x="Season", y="Max_Shelf_Life_Days")
    plt.ylabel("Max Shelf Life (days)")
    plt.xlabel("Season")
    plt.title("Shelf Life Distribution by Season")
    plt.tight_layout()
    plt.savefig("fig2_shelf_life_by_season.png", dpi=150)
    plt.close()


def fig3_boxplot_shelf_life_by_crop(seasonal: pd.DataFrame, top_n: int = 10):
    """Box plot of shelf life distribution across crops.

    This shows which crops are inherently more or less stable, which
    feeds directly into freshness prediction and risk assessment.
    """

    df = seasonal.copy()
    df["Crop"] = df["Crop"].astype(str).str.strip().str.title()

    # Focus on crops with the most rows for clearer plots
    top_crops = (
        df["Crop"].value_counts().head(top_n).index.tolist()
    )
    df_top = df[df["Crop"].isin(top_crops)]

    plt.figure(figsize=(10, 5))
    sns.boxplot(
        data=df_top,
        x="Crop",
        y="Max_Shelf_Life_Days",
        order=top_crops,
    )
    plt.ylabel("Max Shelf Life (days)")
    plt.xlabel("Crop")
    plt.title("Shelf Life Distribution by Crop (Top {} Crops)".format(top_n))
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig("fig3_shelf_life_by_crop.png", dpi=150)
    plt.close()


def _simulate_linear_decay(max_days: float, num_points: int = 100) -> pd.DataFrame:
    """Simulate linear freshness decay used in farmer freshness logic.

    The farmer routes effectively use a linear model:
        freshness = max(0, 1 - days_since_harvest / base_shelf_life_days)
    """

    if max_days <= 0:
        max_days = 1.0
    # Use numpy.linspace; pandas does not expose a top-level linspace helper.
    t = pd.Series(np.linspace(0, max_days, num_points), name="days")
    freshness = (1.0 - t / max_days).clip(lower=0.0)
    return pd.DataFrame({"days": t, "freshness": freshness})


def fig4_freshness_decay_curve(seasonal: pd.DataFrame):
    """Freshness decay curve (time vs freshness score).

    Demonstrates how a crop's freshness decreases over time using the
    same linear decay idea as the digital twin / farmer logic.
    """

    df = seasonal.copy()
    # Pick a few representative crops
    crops = ["tomato", "cabbage", "banana"]
    curves = []
    for crop in crops:
        sub = df[df["Crop"].str.lower() == crop]
        if sub.empty:
            continue
        max_days = sub["Max_Shelf_Life_Days"].median()
        sim = _simulate_linear_decay(max_days)
        sim["Crop"] = crop.title()
        curves.append(sim)

    if not curves:
        return

    all_curves = pd.concat(curves, ignore_index=True)

    plt.figure(figsize=(8, 5))
    sns.lineplot(data=all_curves, x="days", y="freshness", hue="Crop")
    plt.xlabel("Days Since Harvest")
    plt.ylabel("Freshness (0–1)")
    plt.title("Illustrative Freshness Decay Curves by Crop")
    plt.tight_layout()
    plt.savefig("fig4_freshness_decay_curves.png", dpi=150)
    plt.close()


def fig5_warehouse_climate_lines(climate: pd.DataFrame):
    """Line charts for warehouse climate data.

    These plots show temperature and humidity trends per warehouse,
    which directly drive warehouse risk and predicted freshness.
    """

    df = climate.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Temperature vs time
    plt.figure(figsize=(10, 5))
    sns.lineplot(
        data=df,
        x="timestamp",
        y="temperature_c",
        hue="warehouse_name",
        linewidth=1,
    )
    plt.xlabel("Time")
    plt.ylabel("Temperature (°C)")
    plt.title("Warehouse Temperature Over Time")
    plt.tight_layout()
    plt.savefig("fig5_temperature_timeseries.png", dpi=150)
    plt.close()

    # Humidity vs time
    plt.figure(figsize=(10, 5))
    sns.lineplot(
        data=df,
        x="timestamp",
        y="humidity_pct",
        hue="warehouse_name",
        linewidth=1,
    )
    plt.xlabel("Time")
    plt.ylabel("Humidity (%)")
    plt.title("Warehouse Humidity Over Time")
    plt.tight_layout()
    plt.savefig("fig5_humidity_timeseries.png", dpi=150)
    plt.close()


def _risk_status_from_freshness(f: float) -> str:
    """Match backend rule used in farmer/warehouse routes.

    SAFE: f > 0.70
    RISK: 0.40 <= f <= 0.70
    HIGH SPOILAGE RISK: f < 0.40
    """

    if float(f) > 0.70:
        return "SAFE"
    if float(f) >= 0.40:
        return "RISK"
    return "HIGH SPOILAGE RISK"


def fig6_risk_classification_bar(seasonal: pd.DataFrame):
    """Bar chart of risk classification counts.

    We simulate freshness trajectories using shelf-life metadata and
    classify each point into SAFE / RISK / HIGH SPOILAGE RISK using the
    same thresholds as the backend. This explains how much of the
    lifecycle each crop spends in each risk band.
    """

    df = seasonal.copy()
    df["Crop"] = df["Crop"].astype(str).str.strip().str.title()

    # Use a subset of crops for clarity
    crops = df["Crop"].value_counts().head(8).index.tolist()

    records = []
    for crop in crops:
        sub = df[df["Crop"] == crop]
        if sub.empty:
            continue
        max_days = sub["Max_Shelf_Life_Days"].median()
        sim = _simulate_linear_decay(max_days, num_points=60)
        for _, row in sim.iterrows():
            status = _risk_status_from_freshness(row["freshness"])
            records.append({"Crop": crop, "risk_status": status})

    if not records:
        return

    risk_df = pd.DataFrame.from_records(records)
    counts = (
        risk_df.groupby("risk_status")["Crop"].count().reindex(["SAFE", "RISK", "HIGH SPOILAGE RISK"], fill_value=0)
    )

    plt.figure(figsize=(6, 4))
    sns.barplot(x=counts.index, y=counts.values, palette="viridis")
    plt.ylabel("Count (simulated time points)")
    plt.xlabel("Risk Status")
    plt.title("Risk Classification Distribution Across Simulated Freshness Trajectories")
    plt.tight_layout()
    plt.savefig("fig6_risk_classification_counts.png", dpi=150)
    plt.close()


def main():
    seasonal, legacy, climate = load_datasets()

    fig1_correlation_heatmap(seasonal, legacy)
    fig2_boxplot_shelf_life_by_season(seasonal)
    fig3_boxplot_shelf_life_by_crop(seasonal)
    fig4_freshness_decay_curve(seasonal)
    fig5_warehouse_climate_lines(climate)
    fig6_risk_classification_bar(seasonal)


if __name__ == "__main__":
    sns.set_theme(style="whitegrid")
    main()
