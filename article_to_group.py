from __future__ import annotations
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional
import chardet

import pandas as pd

DEFAULT_CORPUS_PATH = Path(__file__).with_name("article_item_group_corpus.json")

with open("impacts_aggregated_GBR.csv", "rb") as f:
    result = chardet.detect(f.read())
    encoding = result["encoding"]
csv = pd.read_csv(
    "impacts_aggregated_GBR.csv", usecols=["Item", "Group"], encoding=encoding
).reset_index(drop=True)

item_pairs = csv.to_dict()
group_pairs = csv.groupby("Group")["Item"].apply(list).to_dict()
item_to_group = {
    item: group
    for group, items in group_pairs.items()
    for item in items
    if pd.notna(item)
}

ITEMS = sorted(csv["Item"].dropna().unique().tolist())
GROUPS = sorted(csv["Group"].dropna().unique().tolist())


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


def build_test_corpus_dataframe(
    corpus_df: pd.DataFrame, test_corpus: Iterable[str]
) -> pd.DataFrame:
    """Create a dataframe from the TESTCORPUS list for prediction."""
    test_df = pd.DataFrame(
        columns=[
            "article",
            "expected_item",
            "expected_group",
            "predicted_item",
            "predicted_group",
        ]
    )
    for article in test_corpus:
        new_row = corpus_df[corpus_df["article"] == article].assign(
            **{"predicted_item": "", "predicted_group": ""}
        )
        test_df = pd.concat([test_df, new_row], ignore_index=True)
    test_df["article_norm"] = test_df["article"].map(canonicalize_text)
    test_df["group_norm"] = ""
    return test_df


def train_test_split_corpus(
    corpus_df: pd.DataFrame,
    test_size: float = 0.2,
    target_column: str = "expected_group",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split the corpus into random training and test sets using an 80/20 split."""
    if not 0 < test_size < 1:
        raise ValueError("test_size must be between 0 and 1")

    if corpus_df.empty:
        return corpus_df.copy().reset_index(drop=True), corpus_df.copy().reset_index(
            drop=True
        )

    has_label = corpus_df[target_column].fillna("").astype(str).str.strip() != ""

    labeled_df = corpus_df.loc[has_label].copy()
    unlabeled_df = corpus_df.loc[~has_label].copy()

    if not unlabeled_df.empty:
        return labeled_df.reset_index(drop=True), unlabeled_df.reset_index(drop=True)

    if labeled_df.empty:
        return (
            labeled_df.reset_index(drop=True),
            pd.concat([unlabeled_df, labeled_df], ignore_index=True),
        )

    shuffled_df = labeled_df.sample(frac=1.0).reset_index(drop=True)
    split_idx = int(len(shuffled_df) * (1 - test_size))
    split_idx = max(1, min(split_idx, len(shuffled_df) - 1))

    train_df = shuffled_df.iloc[:split_idx].copy()
    test_df = shuffled_df.iloc[split_idx:].copy()

    return train_df.reset_index(drop=True), test_df.reset_index(drop=True)


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

    def predict(
        self, article: str, candidate_labels: Optional[Iterable[str]] = None
    ) -> Optional[str]:
        """Return the best predicted label for an article."""
        best_label, _ = self.predict_with_score(
            article, candidate_labels=candidate_labels
        )
        return best_label

    def evaluate(
        self, test_df: pd.DataFrame, labelset: Iterable[str]
    ) -> dict[str, object]:
        """Evaluate the model on a test set and return summary metrics."""
        correct = 0
        total = 0
        predictions: list[tuple[str, str, str]] = []

        for _, row in test_df.iterrows():
            article = str(row["article"])
            expected_label = (
                str(row[self.target_column])
                if row[self.target_column] is not None
                else ""
            )
            predicted_label = self.predict(article, candidate_labels=labelset)
            if predicted_label == expected_label:
                correct += 1
            predictions.append((article, expected_label, predicted_label or ""))
            total += 1

        accuracy = correct / total if total else 0.0
        return {
            "accuracy": accuracy,
            "correct": correct,
            "total": total,
            "predictions": predictions,
        }


GroupHeuristicModel = HeuristicLabelModel


def build_label_matcher(
    corpus_path: Path | str = DEFAULT_CORPUS_PATH,
    target_column: str = "expected_group",
    test_size: float = 0.2,
) -> tuple[HeuristicLabelModel, pd.DataFrame, pd.DataFrame]:
    """Load the corpus, split it, train the heuristic model, and return the model."""
    corpus_df = load_article_group_corpus(corpus_path)
    train_df, test_df = train_test_split_corpus(
        corpus_df, test_size=test_size, target_column=target_column
    )
    model = HeuristicLabelModel.train(train_df, target_column=target_column)
    return model, train_df, test_df


def evaluate_label_matcher(
    corpus_path: Path | str = DEFAULT_CORPUS_PATH,
    target_column: str = "expected_group",
    test_corpus: Optional[Iterable[str]] = None,
) -> dict[str, object]:
    """Train on the full corpus and evaluate on TESTCORPUS when provided."""
    corpus_df = load_article_group_corpus(corpus_path)
    model = HeuristicLabelModel.train(corpus_df, target_column=target_column)
    test_df = build_test_corpus_dataframe(corpus_df, test_corpus)

    if target_column == "expected_item":
        labelset = ITEMS
    else:
        labelset = GROUPS

    predictions: list[tuple[str, str, str]] = []
    for _, row in test_df.iterrows():
        article = str(row["article"])
        predicted_label = model.predict(article, candidate_labels=labelset)
        predictions.append((article, "", predicted_label or ""))

    evaluation = {
        "accuracy": 0.0,
        "correct": 0,
        "total": len(test_df),
        "predictions": predictions,
    }
    evaluation["train_size"] = len(corpus_df)
    evaluation["test_size"] = len(test_df)
    evaluation["labels"] = sorted(model.label_doc_counts.keys())
    evaluation["target_column"] = target_column
    return evaluation


def evaluate_group_and_item_matchers(
    corpus_path: Path | str = DEFAULT_CORPUS_PATH,
    test_corpus: Optional[Iterable[str]] = None,
) -> dict[str, dict[str, object]]:
    """Evaluate separate group and item heuristic models on TESTCORPUS."""
    return {
        "group": evaluate_label_matcher(
            corpus_path=corpus_path,
            target_column="expected_group",
            test_corpus=test_corpus,
        ),
        "item": evaluate_label_matcher(
            corpus_path=corpus_path,
            target_column="expected_item",
            test_corpus=test_corpus,
        ),
    }


def testing(use_score_reconciliation: bool = True):
    corpus_df = load_article_group_corpus(DEFAULT_CORPUS_PATH)
    train_df, test_df = train_test_split_corpus(corpus_df)
    # train_df = corpus_df
    # test_df = build_test_corpus_dataframe(corpus_df, TESTCORPUS)

    group_model = HeuristicLabelModel.train(train_df, target_column="expected_group")
    item_model = HeuristicLabelModel.train(train_df, target_column="expected_item")

    print(f"Training size: {len(train_df)}")
    print(f"Test size: {len(test_df)}")

    item_accuracy = 0.0
    group_accuracy = 0.0
    total = 0.0

    for article in test_df["article"]:
        group_pred, group_score = group_model.predict_with_score(
            article, candidate_labels=GROUPS
        )
        item_pred, item_score = item_model.predict_with_score(
            article, candidate_labels=ITEMS
        )

        if use_score_reconciliation:
            if item_pred and item_score >= group_score:
                predicted_item = item_pred
                predicted_group = item_to_group.get(predicted_item, group_pred or "")
            else:
                predicted_item = item_pred or ""
                predicted_group = group_pred or ""
                if group_pred:
                    allowed_items = group_pairs.get(group_pred, [])
                    if allowed_items:
                        subset_df = corpus_df[
                            corpus_df["expected_group"]
                            .fillna("")
                            .astype(str)
                            .str.strip()
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
                            predicted_group = group_pred
        else:
            predicted_item = item_pred or ""
            predicted_group = group_pred or ""

        row = test_df[test_df["article"] == article]
        expected_item = str(row["expected_item"].item())
        expected_group = str(row["expected_group"].item())

        if predicted_item == expected_item:
            item_accuracy += 1
        else:
            print(
                f"Item - {article!r} => predicted item={predicted_item!r}, predicted group={predicted_group!r}, expected item={expected_item!r}, expected_group={expected_group!r}, item score={item_score:.3f}, group_score={group_score:.3f}"
            )
        if predicted_group == expected_group:
            group_accuracy += 1
        else:
            print(
                f"Group - {article!r} => predicted item={predicted_item!r}, predicted group={predicted_group!r}, expected item={expected_item!r}, expected_group={expected_group!r}, item score={item_score:.3f}, group_score={group_score:.3f}"
            )
        total += 1

        # print(
        #    f"- {article!r} => predicted item={predicted_item!r}, predicted group={predicted_group!r}, item_score={item_score:.3f}, group_score={group_score:.3f}"
        # )

    print(
        f"Accuracy - Items: {(item_accuracy / total):.4f}, Groups: {(group_accuracy / total):.4f}, Total: {((item_accuracy + group_accuracy)/(total * 2)):.4f}"
    )
    # accuracy_compare()


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
    train_df = load_article_group_corpus(DEFAULT_CORPUS_PATH)
    group_model = HeuristicLabelModel.train(train_df, target_column="expected_group")
    item_model = HeuristicLabelModel.train(train_df, target_column="expected_item")
    result = []
    for article in test_df:
        group_pred, group_score = group_model.predict_with_score(
            article, candidate_labels=GROUPS
        )
        item_pred, item_score = item_model.predict_with_score(
            article, candidate_labels=ITEMS
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
