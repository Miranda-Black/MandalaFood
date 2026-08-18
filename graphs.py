"""
Module creates all the graphs for the calculated output data
Created by: Miranda Black
Created on: 20 July 2026 09:47:13
"""

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# %%


def present(string: str) -> str:
    """
    :param string: input string to be formatted
    """
    if string == "ghg":
        return "GHGs"
    return string[0].capitalize() + string[1:]


def fmt_val(v):
    """
    :param v: value to be formatted
    :returns: either v to 4dp or v to 4sf or v (if neither possible)
    """
    try:
        v = float(v)
        if abs(v) >= 1e-4:
            return str(f"{v:.4f}")
        return str(f"{v:.4e}")
    except ValueError:
        return v


# %%


def ghg_bar(df: pd.DataFrame, col: str, instr: str):
    """
    Bar graph
    :param df: Dataframe with data to be displayed
    :param col: Column which is being measured (x-axis)
    :param instr: The impact and how it is being measured
    """
    parts = instr.rsplit("_", 1)
    impact = parts[0]
    measure = parts[1]

    fig, ax = plt.subplots(constrained_layout=True)
    ax.bar(df[col].to_list(), df[instr].to_list())
    ax.set_title(f"{present(measure)} {present(impact)} per {col}")
    ax.set_xticks(df[col].to_list())
    ax.set_xticklabels(df[col].to_list(), rotation=45, ha="right")
    ax.set_xlabel(present(col) + "s")

    unit = ""
    if impact == "ghg":
        unit = "kg CO2eq"
    elif impact == "water":
        unit = "scarcity weighted litres"

    ax.set_ylabel(f"{present(measure)} {present(impact)}/{col} ({unit})")
    fig.savefig(f"output/graphs/{col}_{instr}.png", bbox_inches="tight")
    plt.show()
    plt.close(fig)


def bd_error(df: pd.DataFrame, col: str):
    """
    Biodiversity error graph, with error bars

    :param df: Input dataframe with data
    :param col: Column being measured
    """
    fig, ax = plt.subplots(constrained_layout=True)
    ax.errorbar(
        x=df[col].to_list(),
        y=df["bd_opp_total"].to_list(),
        yerr=df["bd_opp_total_err"].to_list(),
        fmt="o",
        capsize=5,
    )
    ax.set_title(f"Biodiversity impacts per {col}")
    ax.set_xticks(df[col].to_list())
    ax.set_xticklabels(df[col].to_list(), rotation=45, ha="right")
    ax.set_xlabel(present(col) + "s")
    ax.set_ylabel("Mean change in extinction risk\n(ΔE per species)")
    fig.savefig(f"output/graphs/{col}_bd_opp.png")
    plt.close(fig)


def dest_table(df: pd.DataFrame, incol: str):
    """
    Create and display a table showing environmental impact data per destination

    :param df: DataFrame with destination and impact columns
    :param incol: Column name with impact data to display
    """
    parts = incol.rsplit("_", 1)
    impact = parts[0]
    measure = parts[1]

    df = df[["destination", incol]]
    df["percentage"] = (df[incol] / sum(df[incol])) * 100.0
    df = df.sort_values(by="percentage", ascending=False)
    fig, ax = plt.subplots()
    ax.axis("off")

    cell_text = []
    for i in range(len(df)):
        cell_text += [list(map(fmt_val, df.iloc[i].tolist()))]

    if impact == "ghg":
        c_label = present(measure) + " GHGs (kg CO2eq)"
    elif impact == "water":
        c_label = present(measure) + " water use\n(scarcity weighted l)"
    else:
        c_label = "Mean " + measure + " change in extinction risk\n(ΔE per species)"

    labels = [
        "Name of destination",
        c_label,
        f"% share of {measure}",
    ]

    tbl = ax.table(cellText=cell_text, colLabels=labels, loc="center", cellLoc="center")

    if "\n" in c_label:
        for (row, _), cell in tbl.get_celld().items():
            if row == 0:
                cell.set_height(0.1)

    tbl.auto_set_column_width(col=list(range(len(labels))))
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(7.5)
    plt.tight_layout()
    plt.savefig(f"output/graphs/destination_{incol}_table.png")
    plt.show()
    plt.close(fig)


# %%


def ghg_stacked_bar(final: pd.DataFrame, measure: str, all_destinations: bool = False):
    """
    Create a stacked bar chart of GHG emissions by destination and month.

    :param final: DataFrame with month, destination, and ghg data columns
    :param measure: Measure type
    :param all_destinations: If True, show all destinations; if False, aggregate others
    (default: False)
    """
    final[f"ghg_{measure}"] = pd.to_numeric(
        final[f"ghg_{measure}"], errors="coerce"
    ).fillna(0)
    graph = final.pivot(
        index="month", columns="destination", values=f"ghg_{measure}"
    ).fillna(0)
    graph = graph.sort_index()

    indices = np.arange(len(graph.index))
    bottom = np.zeros(len(graph.index))

    destinations = graph.columns.tolist()

    colours = plt.get_cmap("tab20").colors
    colour_map = {
        dest: colours[i % len(colours)] for i, dest in enumerate(destinations)
    }

    if all_destinations:
        for dest in graph.columns:
            plt.bar(
                indices,
                graph[dest].values,
                bottom=bottom,
                label=dest,
                color=colour_map[dest],
            )
            bottom += graph[dest].values
    else:
        plt.bar(
            indices,
            graph["TAWS kitchen"].values,
            label="TAWS kitchen",
            color=colour_map["TAWS kitchen"],
        )
        other = sum(
            graph[dest].values
            for dest in graph.columns
            if (dest != "TAWS kitchen" and dest != "Unknown")
        )
        plt.bar(
            indices,
            other,
            bottom=graph["TAWS kitchen"].values,
            label="Other",
            color=colour_map.get("Other", "gray"),
        )
        plt.bar(
            indices,
            graph["Unknown"].values,
            bottom=graph.sum(axis=1).values - graph["Unknown"].values,
            label="Unknown",
            color=colour_map.get("Unknown", "lightgray"),
        )

    plt.xticks(indices, graph.index)
    plt.xlabel("Month")
    plt.ylabel(present(measure) + " GHGs (kg CO2eq)")
    max_stack = graph.sum(axis=1).max()
    plt.ylim(0, max(1, max_stack * 1.1))
    plt.legend(title="Destination", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.title(
        present(measure) + " GHGs per destination per month from Mandala data",
        loc="left",
    )
    plt.tight_layout()

    if all_destinations:
        plt.savefig(f"output/graphs/month_dest_ghg_{measure}_all.png")
    else:
        plt.savefig(f"output/graphs/month_dest_ghg_{measure}.png")
    plt.close()


# %%


def waste_stacked(final_df: pd.DataFrame):
    """
    Create a stacked bar chart comparing wasted vs redistributed produce by month.

    :param final_df: DataFrame with month, kg_x (waste), and kg_y (redistributed) columns
    """
    final_df["kg_x"] = pd.to_numeric(final_df.get("kg_x", 0), errors="coerce").fillna(0)
    final_df["kg_y"] = pd.to_numeric(final_df.get("kg_y", 0), errors="coerce").fillna(0)

    graph = final_df.set_index("month")[["kg_x", "kg_y"]].fillna(0)

    indices = np.arange(len(graph.index)) * 1.5

    fig, ax = plt.subplots(figsize=(12, 6), constrained_layout=True)

    ax.bar(indices, graph["kg_x"].values, label="Waste")
    ax.bar(
        indices,
        graph["kg_y"].values,
        bottom=graph["kg_x"].values,
        label="Redistributed",
    )

    ax.set_xticks(indices, graph.index, rotation=45, ha="right")
    ax.set_xlabel("Month")
    ax.set_ylabel("Weight (kg)")
    max_stack = graph.sum(axis=1).max()
    ax.set_ylim(0, max(1, max_stack * 1.1))
    ax.legend()
    ax.set_title("Weight of wasted and redistributed produce by month")

    plt.savefig("output/graphs/waste_vs_redistribution.png")
    plt.show()
    plt.close(fig)


# %%


def weights_timeseries(months_weights: pd.DataFrame):
    """
    Create a stacked bar chart showing offered, accepted, and redistributed produce
    weights by month.

    :param months_weights: DataFrame with month, offered, accepted, and redistributed
    weight columns
    """
    fig, ax = plt.subplots()
    x_axis = np.arange(len(months_weights["month"]))
    ax.bar(
        x_axis, months_weights["redistributed_kg"], label="Redistributed", color="green"
    )
    ax.bar(
        x_axis,
        months_weights["accepted_kg"] - months_weights["redistributed_kg"],
        bottom=months_weights["redistributed_kg"],
        label="Accepted",
        color="blue",
    )
    ax.bar(
        x_axis,
        months_weights["offered_kg"] - months_weights["accepted_kg"],
        bottom=months_weights["accepted_kg"],
        label="Offered",
        color="orange",
    )
    plt.xticks(x_axis, months_weights["month"].to_list())
    ax.set_title("Weights of Offered, Accepted, and Redistributed Produce by Month")
    ax.legend(loc="upper right", reverse=True)
    ax.set_xlabel("Month")
    ax.set_ylabel("Weight (kg)")
    plt.savefig("output/graphs/weights_timeseries.png")
    plt.show()
    plt.close(fig)


def weights_percentage(months_weights: pd.DataFrame):
    """
    Create a stacked bar chart showing percentage breakdown of redistributed, accepted
    and rejected produce of the offered produce by month.

    :param months_weights: DataFrame with month, offered, accepted, and redistributed
    weight columns
    """
    fig, ax = plt.subplots()
    x_axis = np.arange(len(months_weights["month"]))
    ax.bar(
        x_axis,
        months_weights["redistributed_kg"] / months_weights["offered_kg"],
        label="Redistributed",
        color="green",
    )
    ax.bar(
        x_axis,
        months_weights["accepted_kg"] / months_weights["offered_kg"]
        - months_weights["redistributed_kg"] / months_weights["offered_kg"],
        bottom=months_weights["redistributed_kg"] / months_weights["offered_kg"],
        label="Accepted",
        color="blue",
    )
    ax.bar(
        x_axis,
        months_weights["offered_kg"] / months_weights["offered_kg"]
        - months_weights["accepted_kg"] / months_weights["offered_kg"],
        bottom=months_weights["accepted_kg"] / months_weights["offered_kg"],
        label="Rejected",
        color="orange",
    )
    plt.xticks(x_axis, months_weights["month"].to_list())
    ax.set_title("Percentage of Rejected, Accepted, and Redistributed Produce by Month")
    ax.legend(loc="upper right", reverse=True)
    ax.set_xlabel("Month")
    ax.set_ylabel("Percentage of Offered Weight (%)")
    plt.savefig("output/graphs/weights_percentage.png")
    plt.show()
    plt.close(fig)


# %%


def scatter(df: pd.DataFrame, x_col: str, y_col: str, colour_col: str):
    """
    Create a scatter plot with error bars comparing weight vs extinction opportunity
    cost by food group.

    :param df: DataFrame with weight, impact, and uncertainty quantile columns
    :param x_col: Column name for x-axis (typically 'kg')
    :param y_col: Column name for y-axis (typically 'MQ' for median quantile)
    :param colour_col: Column name for determining colours (food grouping)
    """
    fig, ax = plt.subplots(constrained_layout=True)
    colours = plt.get_cmap("tab20").colors
    colour_map = {
        group: colours[i % len(colours)] for i, group in enumerate(df[colour_col])
    }
    for _, row in df.iterrows():
        if row["kg"] == 0.0:
            continue
        ax.errorbar(
            x=np.log10(row[x_col]),
            y=np.log10(row[y_col]),
            yerr=[
                [np.log10(row["MQ"]) - np.log10(row["LQ"])],
                [np.log10(row["HQ"]) - np.log10(row["MQ"])],
            ],
            fmt="o",
            label=row[colour_col],
            alpha=0.7,
            capsize=5,
            color=colour_map[row[colour_col]],
        )

    ax.set_xlabel("Weight distribution (log10 kg)")
    ax.set_ylabel("Extinction opportunity cost distribution (log10 ΔE per kilogram)")
    ax.set_title(
        "Total mass for each food group vs the impact/kg of that group", loc="left"
    )
    plt.legend(title="Food Group", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.savefig(f"output/graphs/scatter_log_{x_col}_vs_log_{y_col}.png")
    plt.show()
    plt.close(fig)
