"""
Helper functions for data processing and text normalization.
Provides utilities for date formatting, dataframe manipulation, and string similarity
matching.
Created by: Miranda Black
Created on: 12 August 2026 16:27:41
"""

import re
import difflib
import pandas as pd
from article_to_group import actual as match_article


def format_month(chars: str, string: str) -> str:
    """
    Extract and format month and year from a date string.

    :param chars: Character delimiters to search for in the date string
    :param string: Date string to parse
    :return: Formatted month-year string as "M-YY" or "err" if failure
    """
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


def format_df(df: pd.DataFrame):
    """
    Standardize DataFrame by extracting date and weight columns and normalizing units.

    :param df: Input DataFrame with date and weight columns
    :return: DataFrame with only date and weight columns, renamed to standard names
    """
    date = [col for col in df.columns if "date" in col or "month" in col][0]
    weight = [col for col in df.columns if "kg" in col or "tonnes" in col][0]
    if "tonnes" in weight:
        df[weight] = df[weight] * 1000
    return df[[date, weight]].rename(columns={date: "date", weight: "kg"})


def sort_month_column(df, col="month"):
    """
    Sort a DataFrame by month-year column in chronological order.

    :param df: Input DataFrame
    :param col: Column name containing month-year data in "M-YY" format (default: "month")
    :return: Sorted DataFrame
    """
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


def refactor_dates(df: pd.DataFrame):
    """
    Normalize date format in a DataFrame to "DD/MM/YY" format.

    :param df: Input DataFrame with a date column
    :return: DataFrame with standardized date format
    """
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


def refactor_dest(in_df: pd.DataFrame, destcol: str, weightcol: str):
    """
    Split rows with multiple destinations into separate rows and split impact data
    proportionally.

    :param in_df: Input DataFrame with destination and impact columns
    :param destcol: Name of the destination column
    :param weightcol: Name of the weight column
    :return: DataFrame with one row per destination-item combination
    """
    df = pd.DataFrame(
        columns=[
            "date",
            "destination",
            "article",
            "kg",
            "water_total",
            "ghg_total",
            "bd_opp_total",
            "bd_opp_total_err",
        ]
    ).reset_index(drop=True)
    date_col = [col for col in in_df.columns if "date" in col][0]
    article_col = [col for col in in_df.columns if "article" in col][0]
    for _, row in in_df.iterrows():
        if pd.isna(row[destcol]):
            destinations = ["Unknown"]
        else:
            destinations = re.split(r"[,/]", row[destcol])
        for dest in destinations:
            df.loc[len(df)] = [
                row[date_col],
                dest,
                row[article_col],
                row[weightcol] / len(destinations),
                row["Scarcity_weighted_water_l"] / len(destinations),
                row["ghg_total"] / len(destinations),
                row["bd_opp_total"] / len(destinations),
                row["bd_opp_total_err"] / len(destinations),
            ]
    return df.reset_index(drop=True)


def _normalise_destination(dest: str) -> str:
    """
    Normalize a destination string for comparison (lowercase, remove punctuation).

    :param dest: Destination string to normalize
    :return: Normalized destination string
    """
    dest = dest.lower()
    dest = "".join(ch for ch in dest if ch.isalnum() or ch.isspace())
    return " ".join(dest.split())


def group_dest(destinations: list[str], threshold: float = 0.75) -> dict[str, str]:
    """
    Group similar destination names using sequence matching above a similarity threshold.

    :param destinations: List of destination strings to group
    :param threshold: Minimum similarity score for grouping (default: 0.75)
    :return: Dictionary mapping each destination to its canonical group name
    """
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


def double_split(in_str: str):
    """
    Split a string by common delimiters (comma or forward slash).

    :param in_str: String to split
    :return: List of split strings, or ["Unknown"] if input is None/NaN
    """
    if in_str is None or str(in_str) == "nan":
        return ["Unknown"]
    else:
        return re.split(r"[,/]", in_str)


def close_enough(str1: str, str2: str, threshold: float = 0.8) -> bool:
    """
    Check if two strings are similar enough to be considered a match.

    :param str1: First string to compare
    :param str2: Second string to compare
    :param threshold: Minimum similarity score for match (default: 0.8)
    :return: True if strings are similar enough, False otherwise
    """
    str1 = _normalise_destination(str1)
    str2 = _normalise_destination(str2)
    score = difflib.SequenceMatcher(None, str1, str2).ratio()
    return score >= threshold


def most_similar(string: str, comparisons: pd.Series):
    """
    Find the most similar string from a series to the input string using article
    matching.

    :param string: String to match
    :param comparisons: Series of strings to search within
    :return: The most similar string from comparisons
    """
    outlist = match_article(comparisons)
    if string in outlist:
        mylist = [
            comparisons.to_list()[i]
            for i in range(len(outlist))
            if outlist[i] == string
        ]
        boollist = list(map((lambda x: close_enough(string, x)), mylist))
        if True in boollist:
            return mylist[boollist.index(True)]
        else:
            return mylist[0]
    else:
        for i in comparisons:
            if close_enough(string, i):
                return i
