"""Loads the grant data and works out which grants count as renewals.

A "pair" is a row of mart_grant_pairs: two grants to the same organisation, where the
second (renewed) grant came after the first. Each grant can appear in many pairs.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account

# How far outside the ranges a pair can be and still show as a near miss
MONTH_MARGIN = 2
RATIO_MARGIN = 0.2

# --- Loading data ---

@st.cache_resource
def get_client():
    creds = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"])
    )
    return bigquery.Client(credentials=creds, project=creds.project_id)

@st.cache_data(ttl=3600)
def load_tables(*tables: str) -> list[pd.DataFrame]:
    """Load each table in full, running the queries concurrently."""
    client = get_client()
    with ThreadPoolExecutor() as pool:
        return list(pool.map(lambda table: client.query(f"select * from `{table}`").to_dataframe(), tables))

# --- Renewal logic ---

@dataclass(frozen=True)
class RenewalDefinition:
    """The options chosen in the sidebar."""
    min_months: int
    max_months: int
    min_ratio: float
    max_ratio: float
    same_focus_area: bool

@dataclass
class RenewalResults:
    """Everything the dashboard shows for a given definition."""
    total_grants: int
    renewed_grants: int
    grants_with_prior: int  # grants where the organisation had an earlier grant
    by_year: pd.DataFrame
    renewals: pd.DataFrame
    near_misses: pd.DataFrame

    @property
    def renewal_share(self) -> float | None:
        return self.renewed_grants / self.grants_with_prior if self.grants_with_prior else None

def apply_definition(pairs: pd.DataFrame, definition: RenewalDefinition) -> pd.DataFrame:
    """Flag which parts of the definition each candidate pair meets."""
    # Same-month pairs appear in both directions in the mart, so neither can be a renewal of the other
    pairs = pairs[pairs["months_since_first"] >= 1].copy()
    pairs["months_ok"] = pairs["months_since_first"].between(definition.min_months, definition.max_months)
    pairs["ratio_ok"] = pairs["amount_ratio"].between(definition.min_ratio, definition.max_ratio)
    pairs["focus_ok"] = pairs["same_focus_area"].fillna(False) | (not definition.same_focus_area)
    pairs["qualifies"] = pairs["months_ok"] & pairs["ratio_ok"] & pairs["focus_ok"]
    return pairs

def find_renewals(pairs: pd.DataFrame) -> pd.DataFrame:
    """Pair each renewed grant with its most recent qualifying earlier grant, tie-breaking on the closest amount."""
    return (
        pairs[pairs["qualifies"]]
        .assign(ratio_distance=lambda df: (df["amount_ratio"] - 1).abs())
        .sort_values(["first_grant_date", "ratio_distance"], ascending=[False, True])
        .drop_duplicates("renewed_grant_id")
        .sort_values("renewed_grant_date", ascending=False)
    )

def exclusion_reason(pair: pd.Series, d: RenewalDefinition) -> str:
    """Describe the one rule a near miss fails."""
    if not pair["months_ok"]:
        side = "fewer" if pair["months_since_first"] < d.min_months else "more"
        return f"{pair['months_since_first']} months apart ({side} than {d.min_months}–{d.max_months})"
    if not pair["ratio_ok"]:
        side = "below" if pair["amount_ratio"] < d.min_ratio else "above"
        return f"Second grant is {pair['amount_ratio']:.0%} of the first ({side} {d.min_ratio:.0%}–{d.max_ratio:.0%})"
    return f"Different focus area ({pair['first_focus_area']} → {pair['renewed_focus_area']})"

def find_near_misses(pairs: pd.DataFrame, renewed_ids: set, d: RenewalDefinition) -> pd.DataFrame:
    """Pairs that fail exactly one rule, close to the threshold, where the later grant isn't already a renewal."""
    near = pairs[~pairs["renewed_grant_id"].isin(renewed_ids)].copy()
    rules_failed = (~near[["months_ok", "ratio_ok", "focus_ok"]]).sum(axis=1)
    months_close = near["months_since_first"].between(d.min_months - MONTH_MARGIN, d.max_months + MONTH_MARGIN)
    ratio_close = near["amount_ratio"].between(d.min_ratio - RATIO_MARGIN, d.max_ratio + RATIO_MARGIN)
    near = near[
        (rules_failed == 1)
        # A failed month or ratio rule only counts if it's within the margin
        & (near["months_ok"] | months_close)
        & (near["ratio_ok"] | ratio_close)
    ].sort_values("renewed_grant_date", ascending=False)
    near["reason"] = [exclusion_reason(pair, d) for _, pair in near.iterrows()]
    return near

# Grant types in the chart, in stacking order from the bottom of each bar
GRANT_TYPES = ["Renewal", "Repeat grant", "First grants"]

def grants_by_year(grants: pd.DataFrame, repeat_ids: set, renewed_ids: set) -> pd.DataFrame:
    """Count grants per year, split into renewals, other repeat grants and non-repeat grants."""
    type_index = grants["grant_id"].isin(renewed_ids).map({True: 0, False: 2})
    type_index[grants["grant_id"].isin(repeat_ids - renewed_ids)] = 1
    return (
        grants.assign(
            year=pd.to_datetime(grants["grant_date"]).dt.year,
            type_order=type_index,
            type=type_index.map(dict(enumerate(GRANT_TYPES))),
        )
        .groupby(["year", "type", "type_order"])
        .size()
        .reset_index(name="grants")
    )

def evaluate(grants: pd.DataFrame, pairs: pd.DataFrame, definition: RenewalDefinition) -> RenewalResults:
    """Apply a renewal definition and calculate everything the dashboard shows."""
    pairs = apply_definition(pairs, definition)
    renewals = find_renewals(pairs)
    renewed_ids = set(renewals["renewed_grant_id"])
    repeat_ids = set(pairs["renewed_grant_id"])
    return RenewalResults(
        total_grants=len(grants),
        renewed_grants=len(renewed_ids),
        grants_with_prior=len(repeat_ids),
        by_year=grants_by_year(grants, repeat_ids, renewed_ids),
        renewals=renewals,
        near_misses=find_near_misses(pairs, renewed_ids, definition),
    )
