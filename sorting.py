import os
import re
import difflib
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np


def format_month(chars: str, string: str) -> str:
    string = string.strip()
    templist = []
    for c in chars:
        if c in string:
            templist = string.split(c)
            continue
    if templist == []:
        return "err"
    if templist[1].startswith("0"):
        templist[1] = templist[1][1:]
    if templist[2].startswith("20"):
        templist[2] = templist[2][2:]
    return templist[1] + "-" + templist[2]


def _month(in_df: pd.DataFrame, date_df: pd.DataFrame):
    date_col = [col for col in in_df.columns if "date" in col][0]
    weight_cols = [col for col in in_df.columns if "kg" in col]
    if len(weight_cols) > 1:
        weight_col = weight_cols[1]
    else:
        weight_col = weight_cols[0]
    for idx, in_row in in_df.iterrows():
        in_date = str(in_df.at[idx, date_col])
        if pd.isna(in_date) or re.search(r"\d", in_date) is None:
            month = date_df.loc[len(date_df) - 1, "month"]
        else:
            month = format_month("/.-", in_date)
        if month not in date_df["month"].to_list():
            date_df.loc[len(date_df)] = [
                month,
                in_row["ghg_total"],
                in_row["bd_opp_total"],
                in_row["bd_opp_total_err"],
                in_row[weight_col],
            ]
        else:
            row = date_df[date_df["month"] == month]
            if pd.isna(in_row["ghg_total"]):
                row["kg"] += in_row[weight_col]
                continue
            row["ghg_total"] += in_row["ghg_total"]
            row["bd_opp_total"] += in_row["bd_opp_total"]
            row["bd_opp_total_err"] += in_row["bd_opp_total_err"]
            try:
                row["kg"] += float(in_row[weight_col])
            except ValueError:
                row["kg"] += float(in_row[weight_cols[0]])
            date_df[date_df["month"] == month] = row
    return date_df


def _graphs(df: pd.DataFrame, col: str):
    os.makedirs("output/graphs", exist_ok=True)

    fig, ax = plt.subplots()
    ax.bar(df[col].to_list(), df["ghg_total"].to_list())
    ax.set_title(f"total greenhouse gas emissions per {col}s")
    ax.set_xlabel(f"{col}s")
    ax.set_ylabel("total greenhouse gas emissions")
    fig.savefig(f"output/graphs/{col}_ghg_total.png", bbox_inches="tight")
    plt.close(fig)

    fig, ax = plt.subplots()
    ax.bar(df[col].to_list(), df["ghg_mean"].to_list())
    ax.set_title(f"mean greenhouse gas emissions per {col}")
    ax.set_xlabel(f"{col}s")
    ax.set_ylabel("mean greenhouse gas emissions")
    fig.savefig(f"output/graphs/{col}_ghg_mean.png", bbox_inches="tight")
    plt.close(fig)

    bd_df = pd.DataFrame(columns=[col, "bd_opp"])
    for c in df[col].to_list():
        row = df.loc[df[col] == c]
        bd_df.loc[len(bd_df)] = [c, row["bd_opp_total"].item()]
        bd_df.loc[len(bd_df)] = [
            c,
            row["bd_opp_total"].item() - row["bd_opp_total_err"].item(),
        ]
        bd_df.loc[len(bd_df)] = [
            c,
            row["bd_opp_total"].item() + row["bd_opp_total_err"].item(),
        ]
    bd_df["bd_opp"] = pd.to_numeric(bd_df["bd_opp"], errors="coerce")
    groups = [g["bd_opp"].dropna().tolist() for _, g in bd_df.groupby(col, sort=False)]

    fig, ax = plt.subplots()
    ax.boxplot(groups)
    fig.savefig(f"output/graphs/{col}_bd_opp.png", bbox_inches="tight")
    plt.close(fig)


def sort_by_month(mandala, taws):
    date_df = pd.DataFrame(
        columns=["month", "ghg_total", "bd_opp_total", "bd_opp_total_err", "kg"]
    )
    date_df = _month(taws, date_df)
    date_df = _month(mandala, date_df)
    date_df["ghg_mean"] = date_df["ghg_total"] / date_df["kg"]
    date_df["bd_opp_mean"] = date_df["bd_opp_total"] / date_df["kg"]
    date_df["bd_opp_mean_err"] = date_df["bd_opp_total_err"] / date_df["kg"]
    date_df.to_csv("output/month.csv", index=False)
    _graphs(date_df, "month")


def _destination(in_dfs: list[pd.DataFrame]):
    df = pd.DataFrame(
        columns=[
            "destination",
            "ghg_total",
            "bd_opp_total",
            "bd_opp_total_err",
            "kg",
        ]
    )
    for in_df in in_dfs:
        destination_col = [col for col in in_df.columns if "destination" in col][0]
        weight_cols = [col for col in in_df.columns if "kg" in col]
        if len(weight_cols) > 1:
            weight_col = weight_cols[1]
        else:
            weight_col = weight_cols[0]
        for idx, in_row in in_df.iterrows():
            if pd.isna(in_df.at[idx, destination_col]):
                destinations = ["Unknown"]
            else:
                destinations = str(in_df.at[idx, destination_col]).split(",")
            for dest in destinations:
                dest = dest.strip()
                if dest not in df["destination"].to_list():
                    df.loc[len(df)] = [
                        dest,
                        in_row["ghg_total"] / len(destinations),
                        in_row["bd_opp_total"] / len(destinations),
                        in_row["bd_opp_total_err"] / len(destinations),
                        in_row[weight_col] / len(destinations),
                    ]
                else:
                    row = df[df["destination"] == dest]
                    if pd.isna(in_row["ghg_total"]):
                        row["kg"] += in_row[weight_col]
                        continue
                    row["ghg_total"] += in_row["ghg_total"] / len(destinations)
                    row["bd_opp_total"] += in_row["bd_opp_total"] / len(destinations)
                    row["bd_opp_total_err"] += in_row["bd_opp_total_err"] / len(
                        destinations
                    )
                    try:
                        row["kg"] += float(in_row[weight_col]) / len(destinations)
                    except ValueError:
                        row["kg"] += float(in_row[weight_cols[0]]) / len(destinations)
                    df[df["destination"] == dest] = row
    df["ghg_mean"] = df["ghg_total"] / df["kg"]
    df["bd_opp_mean"] = df["bd_opp_total"] / df["kg"]
    df["bd_opp_mean_err"] = df["bd_opp_total_err"] / df["kg"]
    df = df.sort_values("destination", ascending=True).reset_index(drop=True)
    df.to_csv("output/dest.csv", index=False)
    _graphs(df, "destination")


def refactor_dates(df: pd.DataFrame):
    date_col = [col for col in df.columns if "date" in col][0]
    df[date_col] = df[date_col].str.replace("-", "/").str.replace(".", "/")
    for idx, row in df.iterrows():
        tmp = str(row[date_col]).split("/")
        if len(tmp) == 1:
            continue
        if len(tmp[1]) < 2:
            tmp[1] = "0" + tmp[1]
        df.loc[idx, date_col] = "/".join(tmp)
    return df


def refactor_dest(mandala: pd.DataFrame):
    df = pd.DataFrame(
        columns=[
            "date",
            "destination",
            "article",
            "kg",
            "ghg_total",
            "bd_opp_total",
            "bd_opp_total_err",
        ]
    ).reset_index(drop=True)
    for _, row in mandala.iterrows():
        destinations = row["Mand_outflow_destination"].split("/")
        for dest in destinations:
            df.loc[len(df)] = [
                row["Mand_outflow_date"],
                dest,
                row["Mand_outflow_article"],
                row["Mand_outflow_redistrib_weightkg"] / len(destinations),
                row["ghg_total"] / len(destinations),
                row["bd_opp_total"] / len(destinations),
                row["bd_opp_total_err"] / len(destinations),
            ]
    return df.reset_index(drop=True)


def _normalise_destination(dest: str) -> str:
    dest = dest.lower()
    dest = "".join(ch for ch in dest if ch.isalnum() or ch.isspace())
    return " ".join(dest.split())


def group_dest(destinations: list[str], threshold: float = 0.75) -> dict[str, str]:
    groups = []
    mapping = {}

    for dest in destinations:
        norm = _normalise_destination(dest)
        if not norm:
            mapping[dest] = dest
            continue

        matched = False
        for group in groups:
            score = difflib.SequenceMatcher(None, norm, group["norm"]).ratio()
            if score >= threshold:
                mapping[dest] = group["canon"]
                group["members"].append(dest)
                matched = True
                break

        if not matched:
            groups.append({"canon": dest.strip(), "norm": norm, "members": [dest]})
            mapping[dest] = dest.strip()

    return mapping


def mandala_extra(mandala: pd.DataFrame):
    refactored = refactor_dest(refactor_dates(mandala))
    refactored["month"] = refactored["date"].apply(lambda d: format_month("/", d))
    dest_dict = group_dest(list(refactored["destination"].unique()))
    refactored["dest"] = refactored["destination"].apply(lambda d: dest_dict[d])
    final = pd.DataFrame(
        columns=[
            "month",
            "destination",
            "kg",
            "ghg_total",
            "bd_opp_total",
            "bd_opp_total_err",
            "ghg_mean",
            "bd_opp_mean",
            "bd_opp_mean_err",
        ]
    )
    for month in refactored["month"].unique():
        subset1 = refactored[refactored["month"] == month]
        for dest in subset1["dest"].unique():
            subset2 = subset1[subset1["dest"] == dest]
            final.loc[len(final)] = [
                month,
                dest,
                sum(subset2["kg"]),
                sum(subset2["ghg_total"]),
                sum(subset2["bd_opp_total"]),
                sum(subset2["bd_opp_total_err"]),
                sum(subset2["ghg_total"]) / sum(subset2["kg"]),
                sum(subset2["bd_opp_total"]) / sum(subset2["kg"]),
                sum(subset2["bd_opp_total_err"]) / sum(subset2["kg"]),
            ]
    final.to_csv("output/month_dest.csv")
    extra_graph(final, "ghg_total")
    extra_graph(final, "ghg_mean")


def extra_graph(final: pd.DataFrame, col: str):
    final[col] = pd.to_numeric(final[col], errors="coerce").fillna(0)
    graph = final.pivot(index="month", columns="destination", values=col).fillna(0)
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
    plt.xlabel("month")
    plt.ylabel(col)
    max_stack = graph.sum(axis=1).max()
    plt.ylim(0, max(1, max_stack * 1.1))
    plt.legend(title="destination", bbox_to_anchor=(1.05, 1), loc="upper left")
    plt.tight_layout()
    plt.savefig(f"output/graphs/mandala_dest_{col}.png")
    plt.close()


def format_df(df: pd.DataFrame):
    date = [col for col in df.columns if "date" in col or "month" in col][0]
    weight = [col for col in df.columns if "kg" in col or "tonnes" in col][0]
    if "tonnes" in weight:
        df[weight] = df[weight] * 1000
    return df[[date, weight]].rename(columns={date: "date", weight: "kg"})


def sort_month_column(df, col="month"):
    # Split "M-YY" into numeric month and year
    temp = df[col].str.split("-", expand=True)
    temp.columns = ["m", "y"]

    # Convert to integers
    temp["m"] = temp["m"].astype(int)
    temp["y"] = temp["y"].astype(int)

    # Build a sortable key: year * 12 + month
    df["_sort_key"] = temp["y"] * 12 + temp["m"]

    # Sort by the key, preserve original appearance
    df = df.sort_values("_sort_key").drop(columns="_sort_key")

    return df


def waste_vs_distrib(waste_df: pd.DataFrame, kg1: pd.DataFrame, kg2: pd.DataFrame):
    kg1 = refactor_dates(format_df(kg1))
    kg2 = refactor_dates(format_df(kg2))
    distrib = pd.concat([kg1, kg2], ignore_index=True)
    sum_df = pd.DataFrame(columns=["month", "kg"])
    distrib["month"] = ""
    for idx, row in distrib.iterrows():
        in_date = distrib.at[idx, "date"]
        if pd.isna(in_date) or re.search(r"\d", str(in_date)) is None:
            distrib.at[idx, "date"] = distrib.at[idx - 1, "date"]
            month = format_month("/.-", str(distrib.at[idx, "date"]))
        else:
            month = format_month("/.-", str(in_date))
        if pd.isna(row["kg"]) or row["kg"] is None:
            continue
        if month not in sum_df["month"].to_list():
            sum_df.loc[len(sum_df)] = [month, row["kg"]]
        else:
            sum_df.loc[sum_df["month"] == month, "kg"] += row["kg"]

    waste_df = format_df(waste_df)
    months = []
    for idx, row in waste_df.iterrows():
        date = row["date"].split("-")
        if date[0] not in months:
            months.append(date[0])
            date[0] = str(len(months))
        else:
            date[0] = str(months.index(date[0]) + 1)
        waste_df.at[idx, "date"] = "-".join(date)
    waste_df = waste_df.rename(columns={"date": "month"})

    waste_df["month"] = waste_df["month"].astype(str)
    sum_df["month"] = sum_df["month"].astype(str)
    waste_df = waste_df.reset_index(drop=True)
    sum_df = sum_df.reset_index(drop=True)
    waste_df["month"] = waste_df["month"].astype(str)
    sum_df["month"] = sum_df["month"].astype(str)

    final_df = sort_month_column(
        waste_df.merge(sum_df, on="month", how="outer", sort=False)
    )

    final_df.to_csv("output/waste_vs_redistribution.csv")

    plt.plot(final_df["month"], final_df["kg_x"], marker="o", label="wasted_kg")
    plt.plot(final_df["month"], final_df["kg_y"], marker="o", label="redistributed_kg")
    plt.savefig("output/graphs/waste_vs_redistribution.png")
    plt.close()


def main():
    mandala_in = pd.read_csv("output/Mandala_in_output.csv")
    mandala_out = pd.read_csv("output/Mandala_out_output.csv")
    taws = pd.read_csv("output/TAWS_output.csv")
    bwm = pd.read_csv("input/BWM_waste.csv")

    sort_by_month(mandala_in, taws)
    _destination([taws, mandala_out])
    mandala_extra(mandala_out)
    waste_vs_distrib(bwm, taws, mandala_out)


main()
