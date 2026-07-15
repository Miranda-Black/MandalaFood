from pathlib import Path
import pandas as pd
import chardet

from article_to_group import actual as match_article

MANDALA_IN = [
    "Mand_inflow_article",
    "Mand_inflow_accepted_weightkg",
    "Mand_inflow_offered_weightkg",
]
MANDALA_OUT = ["Mand_outflow_article", "Mand_outflow_redistrib_weightkg"]
TAWS = ["TAWS_article", "TAWS_article_weight_kg"]


def getdata(base_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    mandala_inflow_df = pd.read_csv(base_dir / "Mandala_inflow_data.csv")
    with open(base_dir / "impacts_aggregated_GBR.csv", "rb") as f:
        result = chardet.detect(f.read())
        encoding = result["encoding"]
    impacts_aggregated_df = pd.read_csv(
        base_dir / "impacts_aggregated_GBR.csv", encoding=encoding
    )
    taws_quantitative_surplus_df = pd.read_csv(
        base_dir / "TAWS_quantitative_surplus_data.csv"
    )

    required_columns = [
        "Item",
        "Group",
        "ghg_total",
        "bd_opp_total",
        "bd_opp_total_err",
        "primary_tonnage",
    ]

    impacts_filtered_df = impacts_aggregated_df.loc[
        :,
        [col for col in required_columns if col in impacts_aggregated_df.columns],
    ]
    return impacts_filtered_df, mandala_inflow_df, taws_quantitative_surplus_df


def append_impacts_cols(
    impacts_filtered_df: pd.DataFrame, other_df: pd.DataFrame, columns: list[str]
) -> pd.DataFrame:
    """Append new columns to the other_row based on the matching row in impacts_filtered_df."""
    cols_to_add = ["ghg_total", "bd_opp_total", "bd_opp_total_err"]
    other_df = other_df.assign(
        **{col: None for col in cols_to_add}
    )  # Initialize new columns with None

    other_df["predicted_item"] = match_article(other_df[columns[0]])

    for idx, other_row in other_df.iterrows():
        accepted_weight = other_row[columns[1]]
        if accepted_weight == "not sorted yet" and len(columns) > 2:
            accepted_weight = other_row[columns[2]]
        elif accepted_weight == "":
            continue

        matched_row = impacts_filtered_df[
            impacts_filtered_df["Item"] == other_df.at[idx, "predicted_item"]
        ]

        for col in cols_to_add:
            other_df.at[idx, col] = impact_per_item(
                float(accepted_weight),
                matched_row[col].item(),
                matched_row["primary_tonnage"].item(),
            )

    return other_df


def impact_per_item(
    kg_of_item: float, impact_value: float, primary_tonnage: float
) -> float:
    return (
        (impact_value / (primary_tonnage * 1000)) * kg_of_item
        if primary_tonnage > 0
        else 0.0
    )


def main():
    base_dir = Path(__file__).resolve().parent
    in_dir = Path(base_dir, "input")
    out_dir = Path(base_dir, "output")

    impacts_filtered_df, mandala_inflow_df, taws_df = getdata(in_dir)

    mandala_df = append_impacts_cols(impacts_filtered_df, mandala_inflow_df, MANDALA_IN)
    mandala_df.to_csv(out_dir / "Mandala_output.csv", index=False)

    taws_df = append_impacts_cols(impacts_filtered_df, taws_df, TAWS)
    taws_df.to_csv(out_dir / "TAWS_output.csv", index=False)

    mandala_outflow_df = pd.read_csv(in_dir / "Mandala_outflow_data.csv")
    df = append_impacts_cols(impacts_filtered_df, mandala_outflow_df, MANDALA_OUT)
    df.to_csv(out_dir / "Mandala_out_output.csv", index=False)


main()
