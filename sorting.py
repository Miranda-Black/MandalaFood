"""
Module for sorting and aggregating food impact data by destination, time, and food group.
Created by: Miranda Black
Created on: 13 July 2026 11:41:41
"""

import os
import re
from itertools import chain
from typing import cast
import pandas as pd
import chardet
import graphs
import helpers

# %%


def destination(in_dfs: list[pd.DataFrame]):
    """
    Aggregate environmental impact data by destination.

    :param in_dfs: List of DataFrames with destination and impact columns
    """
    df = pd.DataFrame(
        columns=[
            "destination",
            "water_total",
            "ghg_total",
            "bd_opp_total",
            "bd_opp_total_err",
            "kg",
        ]
    )

    all_dest = []
    for in_df in in_dfs:
        dest = [col for col in in_df.columns if "destination" in col][0]
        all_dest += map(helpers.double_split, in_df[dest].unique())
    all_dest = sorted(
        list(set(map((lambda d: d.strip()), chain.from_iterable(all_dest))))
    )
    dest_dict = helpers.group_dest(all_dest)

    for in_df in in_dfs:
        # find relevant column names in the incoming dataframe
        orig_destination_col = [col for col in in_df.columns if "destination" in col][0]
        weight_cols = [col for col in in_df.columns if "kg" in col]
        if len(weight_cols) > 1:
            weight_col = weight_cols[1]
        else:
            weight_col = weight_cols[0]

        # refactor_dest returns rows already split by destination
        ref_df = helpers.refactor_dest(in_df, orig_destination_col, weight_col)

        # normalise / group similar destination names
        ref_df["destination"] = ref_df["destination"].apply(
            lambda d: dest_dict.get(d, "Unknown") if pd.notna(d) else "Unknown"
        )

        # accumulate into the result dataframe; ref_df rows are per destination
        for _, in_row in ref_df.iterrows():
            dest = (
                in_row["destination"] if pd.notna(in_row["destination"]) else "Unknown"
            )

            if dest not in df["destination"].to_list():
                ghg = (
                    in_row.get("ghg_total", 0)
                    if not pd.isna(in_row.get("ghg_total", 0))
                    else 0
                )
                bd = (
                    in_row.get("bd_opp_total", 0)
                    if not pd.isna(in_row.get("bd_opp_total", 0))
                    else 0
                )
                bd_err = (
                    in_row.get("bd_opp_total_err", 0)
                    if not pd.isna(in_row.get("bd_opp_total_err", 0))
                    else 0
                )
                sw = (
                    in_row.get("water_total", 0)
                    if not pd.isna(in_row.get("water_total", 0))
                    else 0
                )
                kg = in_row.get("kg", 0) if not pd.isna(in_row.get("kg", 0)) else 0
                df.loc[len(df)] = [dest, sw, ghg, bd, bd_err, kg]
            else:
                idxs = df["destination"] == dest
                # if ghg is missing, only add kg
                if pd.isna(in_row.get("ghg_total", None)):
                    df.loc[idxs, "kg"] += (
                        in_row.get("kg", 0) if not pd.isna(in_row.get("kg", 0)) else 0
                    )
                    continue
                df.loc[idxs, "water_total"] += in_row.get("water_total", 0)
                df.loc[idxs, "ghg_total"] += in_row.get("ghg_total", 0)
                df.loc[idxs, "bd_opp_total"] += in_row.get("bd_opp_total", 0)
                df.loc[idxs, "bd_opp_total_err"] += in_row.get("bd_opp_total_err", 0)
                df.loc[idxs, "kg"] += (
                    in_row.get("kg", 0) if not pd.isna(in_row.get("kg", 0)) else 0
                )
    df["water_mean"] = df["water_total"] / df["kg"]
    df["ghg_mean"] = df["ghg_total"] / df["kg"]
    df["bd_opp_mean"] = df["bd_opp_total"] / df["kg"]
    df["bd_opp_mean_err"] = df["bd_opp_total_err"] / df["kg"]
    df = df.sort_values("destination", ascending=True).reset_index(drop=True)
    df.to_csv("output/dest.csv", index=False)

    graphs.dest_table(df, "water_total")
    graphs.ghg_bar(df, "destination", "water_total")
    graphs.dest_table(df, "water_mean")
    graphs.ghg_bar(df, "destination", "water_mean")

    graphs.dest_table(df, "ghg_total")
    graphs.ghg_bar(df, "destination", "ghg_total")
    graphs.dest_table(df, "ghg_mean")
    graphs.ghg_bar(df, "destination", "ghg_mean")

    graphs.dest_table(df, "bd_opp_total")
    graphs.bd_error(df, "destination")


# %%


def _month(in_df: pd.DataFrame, date_df: pd.DataFrame):
    """
    Helper function to accumulate environmental impact data by month.

    :param in_df: Input DataFrame with date and impact columns
    :param date_df: Accumulator DataFrame for monthly aggregated data
    :return: Updated date_df with new month's data accumulated
    """
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
            month = helpers.format_month("/.-", in_date)
        if month not in date_df["month"].to_list():
            date_df.loc[len(date_df)] = [
                month,
                in_row["Scarcity_weighted_water_l"],
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
            row["water_total"] += in_row["Scarcity_weighted_water_l"]
            row["ghg_total"] += in_row["ghg_total"]
            row["bd_opp_total"] += in_row["bd_opp_total"]
            row["bd_opp_total_err"] += in_row["bd_opp_total_err"]
            try:
                row["kg"] += float(in_row[weight_col])
            except ValueError:
                row["kg"] += float(in_row[weight_cols[0]])
            date_df[date_df["month"] == month] = row
    return date_df


def sort_by_month(mandala, taws):
    """
    Aggregate environmental impact data by month for Mandala and TAWS datasets.

    :param mandala: Mandala outflow DataFrame with date and impact columns
    :param taws: TAWS DataFrame with date and impact columns
    """
    date_df = pd.DataFrame(
        columns=[
            "month",
            "water_total",
            "ghg_total",
            "bd_opp_total",
            "bd_opp_total_err",
            "kg",
        ]
    )
    date_df = _month(taws, date_df)
    date_df = _month(mandala, date_df)
    date_df["water_mean"] = date_df["water_total"] / date_df["kg"]
    date_df["ghg_mean"] = date_df["ghg_total"] / date_df["kg"]
    date_df["bd_opp_mean"] = date_df["bd_opp_total"] / date_df["kg"]
    date_df["bd_opp_mean_err"] = date_df["bd_opp_total_err"] / date_df["kg"]
    date_df.to_csv("output/month.csv", index=False)
    graphs.ghg_bar(date_df, "month", "water_total")
    graphs.ghg_bar(date_df, "month", "water_mean")
    graphs.ghg_bar(date_df, "month", "ghg_total")
    graphs.ghg_bar(date_df, "month", "ghg_mean")
    graphs.bd_error(date_df, "month")


# %%


def date_and_dest(mandala: pd.DataFrame, unknown_dest: pd.DataFrame):
    """
    Aggregate environmental impact data by both date and destination.

    :param mandala: Mandala outflow DataFrame with destination and date columns
    :param unknown_dest: DataFrame with unknown destinations requiring special handling
    """
    refactored = helpers.refactor_dest(
        helpers.refactor_dates(mandala),
        str([col for col in mandala.columns if "destination" in col][0]),
        str([col for col in mandala.columns if "weight" in col][0]),
    )
    refactored["month"] = refactored["date"].apply(
        lambda d: helpers.format_month("/", d)
    )
    dest_dict = helpers.group_dest(list(refactored["destination"].unique()))
    refactored["dest"] = refactored["destination"].apply(lambda d: dest_dict[d])

    unknown_dest = helpers.refactor_dates(unknown_dest)
    unknown_dest["month"] = unknown_dest["Mand_inflow_date"].apply(
        lambda d: helpers.format_month("/", d)
    )

    final = pd.DataFrame(
        columns=[
            "month",
            "destination",
            "kg",
            "water_total",
            "ghg_total",
            "bd_opp_total",
            "bd_opp_total_err",
            "water_mean",
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
                sum(subset2["water_total"]),
                sum(subset2["ghg_total"]),
                sum(subset2["bd_opp_total"]),
                sum(subset2["bd_opp_total_err"]),
                sum(subset2["water_total"]) / sum(subset2["kg"]),
                sum(subset2["ghg_total"]) / sum(subset2["kg"]),
                sum(subset2["bd_opp_total"]) / sum(subset2["kg"]),
                sum(subset2["bd_opp_total_err"]) / sum(subset2["kg"]),
            ]
        unknown_subset = unknown_dest[unknown_dest["month"] == month]
        if not unknown_subset.empty:
            cols_to_convert = [
                "Mand_inflow_offered_weightkg",
                "Mand_inflow_accepted_weightkg",
                "Scarcity_weighted_water_l",
                "ghg_total",
                "bd_opp_total",
                "bd_opp_total_err",
            ]
            for col in cols_to_convert:
                unknown_subset[col] = pd.to_numeric(
                    unknown_subset[col], errors="coerce"
                ).fillna(unknown_subset["Mand_inflow_offered_weightkg"])

            weight_val = sum(unknown_subset["Mand_inflow_accepted_weightkg"].values)

            final.loc[len(final)] = [
                month,
                "Unknown",
                weight_val,
                sum(unknown_subset["Scarcity_weighted_water_l"].values),
                sum(unknown_subset["ghg_total"].values),
                sum(unknown_subset["bd_opp_total"].values),
                sum(unknown_subset["bd_opp_total_err"].values),
                sum(unknown_subset["Scarcity_weighted_water_l"].values) / weight_val,
                sum(unknown_subset["ghg_total"].values) / weight_val,
                sum(unknown_subset["bd_opp_total"].values) / weight_val,
                sum(unknown_subset["bd_opp_total_err"].values) / weight_val,
            ]
    final.to_csv("output/month_dest.csv")
    graphs.ghg_stacked_bar(final, "total", True)
    graphs.ghg_stacked_bar(final, "total")
    graphs.ghg_stacked_bar(final, "mean", True)
    graphs.ghg_stacked_bar(final, "mean")


# %%


def waste_vs_distrib(waste_df: pd.DataFrame, kg1: pd.DataFrame, kg2: pd.DataFrame):
    """
    Compare waste data with redistribution data by month.

    :param waste_df: DataFrame with waste data
    :param kg1: First distribution DataFrame (TAWS)
    :param kg2: Second distribution DataFrame (Mandala outflow)
    """
    kg1 = helpers.refactor_dates(helpers.format_df(kg1))
    kg2 = helpers.refactor_dates(helpers.format_df(kg2))
    distrib = pd.concat([kg1, kg2], ignore_index=True)
    sum_df = pd.DataFrame(columns=["month", "kg"])
    distrib["month"] = ""
    distrib.index = distrib.index.astype(int)
    for idx, row in distrib.iterrows():
        in_date = distrib.at[idx, "date"]
        if pd.isna(in_date) or re.search(r"\d", str(in_date)) is None:
            distrib.at[idx, "date"] = distrib.at[cast(int, idx) - 1, "date"]
            month = helpers.format_month("/.-", str(distrib.at[idx, "date"]))
        else:
            month = helpers.format_month("/.-", str(in_date))
        if pd.isna(row["kg"]) or row["kg"] is None:
            continue
        if month not in sum_df["month"].to_list():
            sum_df.loc[len(sum_df)] = [month, row["kg"]]
        else:
            sum_df.loc[sum_df["month"] == month, "kg"] += row["kg"]

    waste_df = helpers.format_df(waste_df)
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

    final_df = helpers.sort_month_column(
        waste_df.merge(sum_df, on="month", how="outer", sort=False)
    )

    final_df.to_csv("output/waste_vs_redistribution.csv")

    graphs.waste_stacked(final_df)


# %%


def mandala_varying_weight(in_df: pd.DataFrame, out_df: pd.DataFrame):
    """
    Calculate monthly weight statistics for Mandala inflow vs outflow.

    :param in_df: Mandala inflow DataFrame
    :param out_df: Mandala outflow DataFrame
    :return: DataFrame with rows that have no matching outflow data
    """
    in_df = helpers.refactor_dates(in_df)
    in_datecol = [col for col in in_df.columns if "date" in col][0]
    in_df["month"] = in_df[in_datecol].apply(lambda d: helpers.format_month("/", d))

    out_df = helpers.refactor_dates(out_df)
    out_datecol = [col for col in out_df.columns if "date" in col][0]
    out_df["month"] = out_df[out_datecol].apply(lambda d: helpers.format_month("/", d))

    mandala_weights = pd.DataFrame(
        columns=[
            "month",
            "offered_kg",
            "accepted_kg",
            "redistributed_kg",
        ]
    )
    in_article_col = [col for col in in_df.columns if "article" in col][0]
    out_article_col = [col for col in out_df.columns if "article" in col][0]
    other_df = pd.DataFrame(columns=in_df.columns.tolist())
    for date in in_df[in_datecol].unique():
        in_subset = in_df[in_df[in_datecol] == date]
        out_subset = out_df[out_df[out_datecol] == date]
        for article in in_subset[in_article_col].unique():
            in_article_subset = in_subset[
                in_subset[in_article_col] == article
            ].reset_index(drop=True)

            out_article_subset = out_subset[
                out_subset[out_article_col] == article
            ].reset_index(drop=True)
            if out_article_subset.empty and date != "12/06/2025":
                out_article_subset = out_subset[
                    out_subset[out_article_col].apply(
                        lambda x: helpers.close_enough(x, article)
                    )
                ].reset_index(drop=True)
            for idx, in_row in in_article_subset.iterrows():
                out_row = (
                    out_article_subset.loc[idx]
                    if idx < len(out_article_subset)
                    else pd.Series()
                )
                if out_row.empty:
                    print(
                        f"Warning: No matching outflow row for date {date} and article {article}."
                    )
                    other_df.loc[len(other_df)] = in_row
                if not out_row.empty:
                    month = helpers.format_month("/", date)
                    if month not in mandala_weights["month"].to_list():
                        mandala_weights.loc[len(mandala_weights)] = [
                            month,
                            float(in_row["Mand_inflow_offered_weightkg"]),
                            float(in_row["Mand_inflow_accepted_weightkg"]),
                            float(out_row["Mand_outflow_redistrib_weightkg"]),
                        ]
                    else:
                        mandala_weights.loc[
                            mandala_weights["month"] == month, "offered_kg"
                        ] += float(in_row["Mand_inflow_offered_weightkg"])
                        mandala_weights.loc[
                            mandala_weights["month"] == month, "accepted_kg"
                        ] += float(in_row["Mand_inflow_accepted_weightkg"])
                        mandala_weights.loc[
                            mandala_weights["month"] == month, "redistributed_kg"
                        ] += float(out_row["Mand_outflow_redistrib_weightkg"])
    float_cols = mandala_weights.select_dtypes(include=["float64", "float32"]).columns
    mandala_weights[float_cols] = mandala_weights[float_cols].round(2)
    mandala_weights = helpers.sort_month_column(mandala_weights)
    mandala_weights.to_csv("output/mandala_weights.csv", index=False)
    graphs.weights_timeseries(mandala_weights)
    graphs.weights_percentage(mandala_weights)
    return other_df


# %%


def bygroup(
    df: pd.DataFrame,
    df_impacts: pd.DataFrame,
    df_groups: pd.DataFrame,
    odf: pd.DataFrame,
):
    """
    Aggregate weight data by food group and calculate impact metrics.

    :param df: DataFrame with articles and their weights
    :param df_impacts: DataFrame mapping items to environmental impacts
    :param df_groups: DataFrame mapping items to food groups
    :param odf: Output DataFrame to accumulate group-level statistics
    """
    odf["kg"] = 0.0
    weight_col = [col for col in df.columns if "kg" in col][-1]
    second_pass: dict[str, str] = {}

    for _, row in df.iterrows():
        pred_item = cast(str, row["predicted_item"])
        search_row = df_groups[df_groups["Item"] == pred_item]
        if search_row.empty and pred_item not in second_pass:
            new_search = df_groups[
                df_groups["group_name_v7"]
                == df_impacts[df_impacts["Item"] == pred_item]["Group"].values[0]
            ]
            new_pred_item = helpers.most_similar(pred_item, new_search["Item"])
            second_pass[pred_item] = new_pred_item
            pred_item = new_pred_item
        elif search_row.empty:
            pred_item = second_pass[pred_item]
        group = df_groups[df_groups["Item"] == pred_item]["group_name_v5"].values[0]
        odf.loc[odf["g"] == group, "kg"] += float(row[weight_col])
    odf.to_csv("output/bygroup.csv", index=False)
    graphs.scatter(odf, "kg", "MQ", "g")


# %%


def main():
    """
    Main execution function that orchestrates all sorting and aggregation operations.
    Reads processed data files and generates analysis outputs and visualizations.
    """
    mandala_in = pd.read_csv("output/Mandala_in_output.csv")
    mandala_out = pd.read_csv("output/Mandala_out_output.csv")
    taws = pd.read_csv("output/TAWS_output.csv")
    bwm = pd.read_csv("input/BWM_waste.csv")

    with open("input/impacts_aggregated_GBR.csv", "rb") as f:
        result = chardet.detect(f.read())
        encoding = result["encoding"]
    df_impacts = pd.read_csv(
        "input/impacts_aggregated_GBR.csv",
        usecols=["Item", "Group"],
        encoding=encoding,
    ).reset_index(drop=True)

    with open("input/commodity_crosswalk.csv", "rb") as f:
        result = chardet.detect(f.read())
        encoding = result["encoding"]
    df_groups = pd.read_csv(
        "input/commodity_crosswalk.csv",
        usecols=["Item", "group_name_v5", "group_name_v7"],
        encoding=encoding,
    ).reset_index(drop=True)

    os.makedirs("output/graphs", exist_ok=True)

    bygroup(
        mandala_out,
        df_impacts,
        df_groups,
        pd.read_csv("impacts/group_quartile_impacts.csv"),
    )
    unknown_df = mandala_varying_weight(mandala_in, mandala_out)

    sort_by_month(mandala_out, taws)
    destination([taws, mandala_out])
    date_and_dest(mandala_out, unknown_df)
    waste_vs_distrib(bwm, taws, mandala_out)


main()
