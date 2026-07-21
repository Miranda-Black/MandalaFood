import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def present(string: str):
    return string[0].capitalize() + string[1:]


def fmt_val(v):
    try:
        v = float(v)
        if abs(v) >= 1e-4:
            return str(f"{v:.4f}")
        return str(f"{v:.4e}")
    except ValueError:
        return v


def ghg_bar(df: pd.DataFrame, col: str, measure: str):

    fig, ax = plt.subplots(constrained_layout=True)
    ax.bar(df[col].to_list(), df[f"ghg_{measure}"].to_list())
    ax.set_title(f"{present(measure)} GHGs per {col}")
    ax.set_xticks(df[col].to_list())
    ax.set_xticklabels(df[col].to_list(), rotation=45, ha="right")
    ax.set_xlabel(present(col) + "s")
    ax.set_ylabel(f"{present(measure)} GHGs/{col} (kg CO2eq)")
    fig.savefig(f"output/graphs/{col}_ghg_{measure}.png", bbox_inches="tight")
    plt.show()
    plt.close(fig)


def bd_error(df: pd.DataFrame, col: str):
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
    else:
        c_label = "Mean " + measure + " change in extinction risk\n(ΔE per species)"

    labels = [
        "Name of destination",
        c_label,
        f"% share of {measure}",
    ]

    tbl = ax.table(cellText=cell_text, colLabels=labels, loc="center", cellLoc="center")

    if ("\n") in c_label:
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


def ghg_stacked_bar(final: pd.DataFrame, measure: str):
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

    for dest in graph.columns:
        plt.bar(
            indices,
            graph[dest].values,
            bottom=bottom,
            label=dest,
            color=colour_map[dest],
        )
        bottom += graph[dest].values
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
    plt.savefig(f"output/graphs/month_dest_ghg_{measure}.png")
    plt.close()


def waste_stacked(final_df: pd.DataFrame):
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
