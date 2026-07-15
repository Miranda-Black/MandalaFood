from __future__ import annotations
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
import chardet
import pandas as pd

DEFAULT_CORPUS_PATH = Path("article_item_group_corpus.json")
DEFAULT_DATA_PATH = Path("input", "impacts_aggregated_GBR.csv")


def get_data(
    data_path: Path | str = DEFAULT_DATA_PATH,
) -> tuple[dict[str, list[str]], list[str], list[str]]:
    with open(data_path, "rb") as f:
        result = chardet.detect(f.read())
        encoding = result["encoding"]
    csv = pd.read_csv(
        data_path, usecols=["Item", "Group"], encoding=encoding
    ).reset_index(drop=True)

    group_pairs = csv.groupby("Group")["Item"].apply(list).to_dict()

    items = sorted(csv["Item"].dropna().unique().tolist())
    groups = sorted(csv["Group"].dropna().unique().tolist())
    return group_pairs, items, groups


def normalize_text(value: object) -> str:
    """Lowercase, strip punctuation, and collapse whitespace."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def canonicalize_text(value: object) -> str:
    """Normalize text and apply basic singularization rules."""
    text = normalize_text(value)
    if not text:
        return ""

    tokens = []
    for token in text.split():
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"
        elif (
            token.endswith("s") and not token.endswith(("ss", "us")) and len(token) > 3
        ):
            token = token[:-1]
        tokens.append(token)

    return " ".join(tokens)


def load_article_group_corpus(
    corpus_path: Path | str = DEFAULT_CORPUS_PATH,
) -> pd.DataFrame:
    """Load the article-to-group corpus from JSON and normalize supported columns."""
    path = Path(corpus_path)
    if not path.exists():
        raise FileNotFoundError(f"Corpus file not found: {path}")

    with open(path, "rb") as f:
        result = chardet.detect(f.read())
        encoding = result["encoding"]

    df = pd.read_json(path, orient="records", encoding=encoding)
    if "article" not in df.columns:
        raise ValueError("Corpus JSON must contain an 'article' field")

    if "expected_item" not in df.columns and "item" in df.columns:
        df["expected_item"] = df["item"]
    if "expected_group" not in df.columns and "group" in df.columns:
        df["expected_group"] = df["group"]

    for col in ("expected_item", "expected_group", "predicted_item", "predicted_group"):
        if col not in df.columns:
            df[col] = None

    df = df.copy()
    df["article"] = df["article"].fillna("")
    df["expected_item"] = df["expected_item"].fillna("")
    df["expected_group"] = df["expected_group"].fillna("")
    df["predicted_item"] = df["predicted_item"].fillna("")
    df["predicted_group"] = df["predicted_group"].fillna("")
    df["article_norm"] = df["article"].map(canonicalize_text)
    df["group_norm"] = df["expected_group"].map(canonicalize_text)
    return df


@dataclass(frozen=True)
class HeuristicLabelModel:
    target_column: str
    label_token_counts: dict[str, Counter[str]]
    label_doc_counts: Counter[str]
    token_document_frequency: Counter[str]
    label_prior_log: dict[str, float]
    inverse_label_count: dict[str, float]
    label_tokens: dict[str, set[str]]
    alpha: float

    @classmethod
    def train(
        cls,
        train_df: pd.DataFrame,
        target_column: str,
        alpha: float = 1.0,
    ) -> "HeuristicLabelModel":
        """Build a heuristic label model from the training set."""
        label_token_counts: dict[str, Counter[str]] = {}
        label_doc_counts: Counter[str] = Counter()
        token_document_frequency: Counter[str] = Counter()
        label_tokens: dict[str, set[str]] = {}

        for _, row in train_df.iterrows():
            label = (
                str(row[target_column]).strip() if pd.notna(row[target_column]) else ""
            )
            article_norm = canonicalize_text(row["article"])
            if not article_norm or not label:
                continue

            label_doc_counts[label] += 1
            tokens = set(article_norm.split())

            if label not in label_token_counts:
                label_token_counts[label] = Counter()
                label_tokens[label] = set(canonicalize_text(label).split())

            label_token_counts[label].update(tokens)
            token_document_frequency.update(tokens)

        num_labels = len(label_doc_counts)
        if num_labels == 0:
            raise ValueError(f"Training set contains no valid {target_column} examples")

        total_docs = sum(label_doc_counts.values())
        label_prior_log = {
            label: math.log(count / total_docs)
            for label, count in label_doc_counts.items()
        }

        inverse_label_count = {
            token: math.log(
                (num_labels + 1)
                / (
                    1
                    + sum(
                        1
                        for label in label_token_counts
                        if token in label_token_counts[label]
                    )
                )
            )
            for token in token_document_frequency
        }

        return cls(
            target_column=target_column,
            label_token_counts=label_token_counts,
            label_doc_counts=label_doc_counts,
            token_document_frequency=token_document_frequency,
            label_prior_log=label_prior_log,
            inverse_label_count=inverse_label_count,
            label_tokens=label_tokens,
            alpha=alpha,
        )

    def _score_label(self, article: str, label: str) -> float:
        article_norm = canonicalize_text(article)
        if not article_norm:
            return float("-inf")

        tokens = article_norm.split()
        if not tokens:
            return float("-inf")

        label_counts = self.label_token_counts[label]
        score = self.label_prior_log.get(label, 0.0)

        for token in tokens:
            token_score = (
                label_counts.get(token, 0) + self.alpha
            ) * self.inverse_label_count.get(token, 1.0)
            score += token_score

        label_norm = canonicalize_text(label)
        if label_norm in article_norm or article_norm in label_norm:
            score += 2.0

        overlap = len(set(tokens).intersection(self.label_tokens.get(label, set())))
        score += overlap * 0.35
        return score

    def predict_with_score(
        self, article: str, candidate_labels: Optional[Iterable[str]] = None
    ) -> tuple[Optional[str], float]:
        """Return the best predicted label and its score for an article."""
        if candidate_labels is None:
            candidate_labels = list(self.label_doc_counts.keys())

        best_label: Optional[str] = None
        best_score = float("-inf")
        for label in candidate_labels:
            if label not in self.label_doc_counts:
                continue
            score = self._score_label(article, label)
            if score > best_score:
                best_score = score
                best_label = label

        return best_label, best_score


GroupHeuristicModel = HeuristicLabelModel


# TESTING METHOD
def accuracy_compare():
    incorrect1 = (
        pd.read_csv("Mandala_output.csv", usecols=["Mand_inflow_article", "temp_item"])
        .reset_index(drop=True)
        .drop_duplicates()
    )
    incorrect2 = (
        pd.read_csv(
            "Mandala_output_2.csv", usecols=["Mand_inflow_article", "temp_item_2"]
        )
        .reset_index(drop=True)
        .drop_duplicates()
    )
    wrong = pd.merge(incorrect1, incorrect2, how="left", on="Mand_inflow_article")
    with open(DEFAULT_CORPUS_PATH, "rb") as f:
        result = chardet.detect(f.read())
        encoding = result["encoding"]

    df = pd.read_json(DEFAULT_CORPUS_PATH, orient="records", encoding=encoding)
    accuracy1 = 0.0
    accuracy2 = 0.0
    total = 0.0
    for article in wrong["Mand_inflow_article"]:
        article = article.strip()
        row = wrong[wrong["Mand_inflow_article"] == article]
        expected_item = df[df["article"] == article]["expected_item"].item()
        if row["temp_item"].item() == expected_item:
            accuracy1 += 1
        if row["temp_item_2"].item() == expected_item:
            accuracy2 += 1
        total += 1
    print(f"First: {(accuracy1 / total):.4f}")
    print(f"Second: {(accuracy2 / total):.4f}")


def actual(test_df: pd.Series) -> list[str]:
    group_pairs, items, groups = get_data()
    train_df = load_article_group_corpus()
    group_model = HeuristicLabelModel.train(train_df, target_column="expected_group")
    item_model = HeuristicLabelModel.train(train_df, target_column="expected_item")
    result = []
    for article in test_df:
        group_pred, group_score = group_model.predict_with_score(
            article, candidate_labels=groups
        )
        item_pred, item_score = item_model.predict_with_score(
            article, candidate_labels=items
        )
        if item_pred and item_score >= group_score:
            predicted_item = item_pred
        else:
            predicted_item = item_pred or ""
            if group_pred:
                allowed_items = group_pairs.get(group_pred, [])
                if allowed_items:
                    subset_df = train_df[
                        train_df["expected_group"].fillna("").astype(str).str.strip()
                        == group_pred
                    ]
                    subset_df = subset_df[
                        subset_df["expected_item"]
                        .fillna("")
                        .astype(str)
                        .isin(allowed_items)
                    ]
                    if not subset_df.empty:
                        refined_item_model = HeuristicLabelModel.train(
                            subset_df, target_column="expected_item"
                        )
                        predicted_item, item_score = (
                            refined_item_model.predict_with_score(
                                article, candidate_labels=allowed_items
                            )
                        )
        result.append(predicted_item)
    return result
