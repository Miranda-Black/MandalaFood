import re
import pandas as pd
import matplotlib.pyplot as plt


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
    for idx, in_row in in_df.iterrows():
        in_date = in_df.loc[idx, date_col]
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
                1,
            ]
        else:
            row = date_df[date_df["month"] == month]
            if pd.isna(in_row["ghg_total"]):
                row["count"] += 1
                continue
            row["ghg_total"] += in_row["ghg_total"]
            row["bd_opp_total"] += in_row["bd_opp_total"]
            row["bd_opp_total_err"] += in_row["bd_opp_total_err"]
            row["count"] += 1
            date_df[date_df["month"] == month] = row
    return date_df


def _graphs(df: pd.DataFrame, col: str):
    fig, axes = plt.subplots(1, 3)
    axes[0].bar(df[col].to_list(), df["ghg_total"].to_list())
    axes[0].set_title(f"total greenhouse gas emissions per {col}s")
    axes[0].set_xlabel(f"{col}s")
    axes[0].set_ylabel("total greenhouse gas emissions")

    axes[1].bar(df[col].to_list(), df["ghg_mean"].to_list())
    axes[1].set_title(f"mean greenhouse gas emissions per {col}")
    axes[1].set_xlabel(f"{col}s")
    axes[1].set_ylabel("mean greenhouse gas emissions")

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
    # convert bd_opp to numeric and group by month for boxplot
    bd_df["bd_opp"] = pd.to_numeric(bd_df["bd_opp"], errors="coerce")
    groups = [g["bd_opp"].dropna().tolist() for _, g in bd_df.groupby(col, sort=False)]
    labels = bd_df[col].drop_duplicates().tolist()
    axes[2].boxplot(groups)
    plt.show()


def sort_by_month(mandala, taws):
    date_df = pd.DataFrame(
        columns=["month", "ghg_total", "bd_opp_total", "bd_opp_total_err", "count"]
    )
    date_df = _month(taws, date_df)
    date_df = _month(mandala, date_df)
    date_df["ghg_mean"] = date_df["ghg_total"] / date_df["count"]
    date_df["bd_opp_mean"] = date_df["bd_opp_total"] / date_df["count"]
    date_df["bd_opp_mean_err"] = date_df["bd_opp_total_err"] / date_df["count"]
    date_df.to_csv("month.csv", index=False)
    _graphs(date_df, "month")


def _destination(in_df: pd.DataFrame):
    df = pd.DataFrame(
        columns=[
            "destination",
            "ghg_total",
            "bd_opp_total",
            "bd_opp_total_err",
            "count",
        ]
    )
    destination_col = [col for col in in_df.columns if "destination" in col][0]
    for idx, in_row in in_df.iterrows():
        if pd.isna(in_df.loc[idx, destination_col]):
            destinations = ["Unknown"]
        else:
            destinations = in_df.loc[idx, destination_col].split(",")
        for dest in destinations:
            dest = dest.strip()
            if dest not in df["destination"].to_list():
                df.loc[len(df)] = [
                    dest,
                    in_row["ghg_total"] / len(destinations),
                    in_row["bd_opp_total"] / len(destinations),
                    in_row["bd_opp_total_err"] / len(destinations),
                    1,
                ]
            else:
                row = df[df["destination"] == dest]
                if pd.isna(in_row["ghg_total"]):
                    row["count"] += 1
                    continue
                row["ghg_total"] += in_row["ghg_total"] / len(destinations)
                row["bd_opp_total"] += in_row["bd_opp_total"] / len(destinations)
                row["bd_opp_total_err"] += in_row["bd_opp_total_err"] / len(
                    destinations
                )
                row["count"] += 1
                df[df["destination"] == dest] = row
    df["ghg_mean"] = df["ghg_total"] / df["count"]
    df["bd_opp_mean"] = df["bd_opp_total"] / df["count"]
    df["bd_opp_mean_err"] = df["bd_opp_total_err"] / df["count"]
    df = df.sort_values("destination", ascending=True).reset_index(drop=True)
    df.to_csv("dest.csv", index=False)
    _graphs(df, "destination")


def sort_by_supplier(mandala: pd.DataFrame, taws: pd.DataFrame):
    supplier = pd.DataFrame(
        columns=["supplier", "ghg_total", "bd_opp_total", "bd_opp_total_err", "count"]
    )
    supplier_dict1 = (
        taws.groupby("TAWS_supplier_unit_number")["TAWS_supplier_name"]
        .apply(set)
        .to_dict()
    )
    supplier_dict2 = (
        taws.groupby("TAWS_supplier_name")["TAWS_supplier_unit_number"]
        .apply(set)
        .to_dict()
    )
    random = []


def main():
    mandala = pd.read_csv("Mandala_output.csv")
    taws = pd.read_csv("TAWS_output.csv")
    sort_by_month(mandala, taws)
    _destination(taws)
    # sort_by_supplier(mandala, taws)


main()
