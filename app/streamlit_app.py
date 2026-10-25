import hmac
import altair as alt
import pandas as pd
import streamlit as st
from queries import GRANT_TYPES, MONTH_MARGIN, RATIO_MARGIN, RenewalDefinition, evaluate, load_tables

st.set_page_config(page_title="What counts as a renewal?", layout="wide")

RENEWAL_COLOR = "#064D49"
REPEAT_COLOR = "#fac2de"
ONE_OFF_GRANT_COLOR = "#B2CFED"

def check_password() -> bool:
    """Ask for the app password, unless require_password is turned off in secrets."""
    def password_entered():
        ok = hmac.compare_digest(st.session_state["password"], st.secrets["app_password"])
        st.session_state["authenticated"] = ok
        if ok:
            del st.session_state["password"]
    if st.session_state.get("authenticated") or not st.secrets["require_password"]:
        return True
    url_password = st.query_params.get("password")
    if url_password and hmac.compare_digest(url_password, st.secrets["app_password"]):
        st.session_state["authenticated"] = True
        return True
    st.write("Please enter the password to access this dashboard.")
    st.text_input("Password", type="password", on_change=password_entered, key="password")
    if st.session_state.get("authenticated") is False:
        st.error("Incorrect password")
    return False

st.title("What counts as a renewal?")

if not check_password():
    st.stop()

st.write(
    "This dashboard explores metadata-based definitions of a renewed grant."
)
st.write(
    "Grant renewals, where an organization is given a related grant after an initial grant, "
    "are not indicated in the source data. This dashboard explores whether it is possible to create a definition "
    "that identifies genuine renewals using only grant metadata, such as amount, date and focus area, with no contextual information."
)
st.write(
    "Use the options on the left to choose your definition and see how it changes what counts as a renewal. "
    "Your current definition is:"
)
grants, pairs = load_tables(st.secrets["grants_table"], st.secrets["pairs_table"])

# --- Definition options ---
st.sidebar.header("Define a renewal")
min_months, max_months = st.sidebar.slider(
    "Months between first grant and renewal",
    min_value=0, max_value=160, value=(12, 24),
    help="Only subsequent grants made within the months specified here count as a renewal. For example, 12 to 24 months means the second grant must be at least one year and at most two years after the earlier grant."
)
min_percent, max_percent = st.sidebar.slider(
    "Renewed amount as a percent of first grant amount",
    min_value=0, max_value=500, value=(80, 200), step=5, format="%d%%",
    help="Only subsequent grants worth between these percentages of the first grant count as a renewal. For example, 80% to 200% means the second grant must be at least 80% of the size of the earlier grant, and at most twice as large.",
)
# The renewal logic works in ratios, so 100% is a ratio of 1.0
min_ratio, max_ratio = min_percent / 100, max_percent / 100
same_focus_area = st.sidebar.checkbox("Renewals must be for the same focus area", value=True, help="If selected, this means that subsequent grants only count as renewals if they are in the same focus area.")

months = f"{min_months} month{'s' * (min_months != 1)}" if min_months == max_months else f"{min_months}–{max_months} months"
percent = f"{min_percent}%" if min_percent == max_percent else f"between {min_percent}% and {max_percent}%"
focus = ", `is in the same focus area`" if same_focus_area else ""
st.markdown(
    f"##### A grant is a renewal if it's made `{months}` after an earlier grant to the same "
    f"organization{focus}, and is `{percent}` of the amount of that grant."
)

results = evaluate(
    grants, pairs, RenewalDefinition(min_months, max_months, min_ratio, max_ratio, same_focus_area)
)

# --- Headline numbers ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Grants", f"{results.total_grants:,}", border=True)
col2.metric(
    "Repeat grants",
    f"{results.repeat_grants:,}",
    help="Grants where the same organization received an earlier grant, in any focus area. These are potential candidates to be renewals.",
    border=True,
)
col3.metric(
    "Renewed grants",
    f"{results.renewed_grants:,}",
    border=True,
    help="The number of grants that meet your definition of renewed.")
col4.metric(
    "Repeat grants counted as renewals",
    f"{results.renewal_share:.0%}" if results.renewal_share is not None else "–",
    help=(
        f"Renewals as a share of the {results.repeat_grants:,} grants where the same organization "
        "received an earlier grant."
    ),
    border=True,
)

# --- Grants by year ---
st.subheader("Grants by year")
chart = (
    alt.Chart(results.by_year)
    .mark_bar(stroke="white", strokeWidth=1)
    .encode(
        x=alt.X("year:O", title=None, axis=alt.Axis(labelAngle=0)),
        y=alt.Y("grants:Q", title="Grants"),
        color=alt.Color(
            "type:N",
            scale=alt.Scale(domain=GRANT_TYPES, range=[RENEWAL_COLOR, REPEAT_COLOR, ONE_OFF_GRANT_COLOR]),
            legend=alt.Legend(title=None, orient="top"),
        ),
        # Stack renewals at the bottom of each bar, then other repeat grants
        order=alt.Order("type_order:Q"),
        tooltip=[
            alt.Tooltip("year:O", title="Year"),
            alt.Tooltip("type:N", title="Type"),
            alt.Tooltip("grants:Q", title="Grants", format=","),
        ],
    )
)
st.altair_chart(chart, width="stretch")

# --- Renewal and near-miss tables ---
# Columns shown in the tables; the pop-out shows the rest
PAIR_COLUMNS = {
    "organization": st.column_config.TextColumn("Organization"),
    "first_grant_date": st.column_config.DateColumn("First grant date", format="MMM YYYY"),
    "renewed_grant_date": st.column_config.DateColumn("Second grant date", format="MMM YYYY"),
    "first_amount": st.column_config.NumberColumn("First grant amount", format="dollar"),
    "renewed_amount": st.column_config.NumberColumn("Second grant amount", format="dollar"),
}

def show_grant(pair: pd.Series, prefix: str):
    """Show one side of a pair; prefix is "first" or "renewed", matching the mart's column names."""
    # The name and details aren't in the pairs mart, so look them up in fct_grants
    grant = grants.loc[grants["grant_id"] == pair[f"{prefix}_grant_id"]].iloc[0]
    fields = {
        "Name": grant["grant"],
        "Amount": f"${pair[f'{prefix}_amount']:,.0f}",
        "Focus area": pair[f"{prefix}_focus_area"],
        "Details": grant["details"],
    }
    for label, value in fields.items():
        st.caption(label)
        # Escape $ so Streamlit doesn't render text between two dollar signs as maths
        st.markdown(str(value or "–").replace("$", r"\$"))

def show_pair(pair: pd.Series):
    """Pop-out content: shared figures at the top, then the two grants side by side."""
    months, difference, ratio = st.columns(3)
    months.metric("Months apart", f"{pair['months_since_first']}")
    amount_difference = pair["renewed_amount"] - pair["first_amount"]
    sign = "-" if amount_difference < 0 else "+"
    difference.metric("Difference in Amount", f"{sign}${abs(amount_difference):,.0f}")
    ratio.metric("Amount as % of First Grant", f"{pair['amount_ratio']:.0%}")
    # Only near misses have a reason
    if pair.get("reason"):
        st.markdown(f"**Why it's excluded:** {pair['reason']}")

    first, second = st.columns(2, border=True)
    with first:
        st.subheader(f"First grant: {pd.to_datetime(pair['first_grant_date']):%B %Y}")
        show_grant(pair, "first")
    with second:
        st.subheader(f"Second grant: {pd.to_datetime(pair['renewed_grant_date']):%B %Y}")
        show_grant(pair, "renewed")

# Tables are keyed by a version number. Bumping it when the pop-out closes clears their
# selections, so the pop-out doesn't reopen on the next rerun and the same row can be clicked again.
st.session_state.setdefault("table_version", 0)

def reset_selections():
    st.session_state.table_version += 1

def pair_table(df: pd.DataFrame, key: str) -> pd.Series | None:
    """Show a table of pairs and return the selected pair, if any."""
    event = st.dataframe(
        df[list(PAIR_COLUMNS)],
        column_config=PAIR_COLUMNS,
        hide_index=True,
        width="stretch",
        on_select="rerun",
        # Cell selection lets a click anywhere on a row open it, without a checkbox column
        selection_mode="single-cell",
        key=f"{key}_{st.session_state.table_version}",
    )
    cells = event.selection.cells
    return df.iloc[cells[0][0]] if cells else None

renewals_tab, near_tab = st.tabs(
    [f"Renewals ({len(results.renewals):,})", f"Near misses ({len(results.near_misses):,})"]
)
with renewals_tab:
    st.write(
        "Select a row to see more details and decide whether it fits your chosen definition."
    )
    selected_renewal = pair_table(results.renewals, key="renewals")
with near_tab:
    st.write(
        "This section shows pairs of grants to the same organization that fail just one part of the selected definition, "
        "and are otherwise close to qualifying as a renewal. Like renewals, each grant is only shown against "
        "its most recent near-miss earlier grant."
    )
    st.write(
        "Select a row to see why it doesn't count as a renewal and decide whether to adjust your definition."
    )
    selected_near_miss = pair_table(results.near_misses, key="near_misses")

# Only one pop-out can open per run, so a renewal takes priority over a near miss
selected = selected_renewal if selected_renewal is not None else selected_near_miss
if selected is not None:
    st.dialog(selected["organization"], width="large", on_dismiss=reset_selections)(show_pair)(selected)

# --- Findings ---
st.divider()
st.subheader("My findings")
st.write(
    "This dashboard is designed to be experimented with to find a *good definition* of a renewal. "
     "New definitions can be created and explored to see which grants fall into each category."
)
st.write(
    "However, to decide which definition is best, or whether a metadata-based definition is even possible, "
    "I'd need more context about how the term renewal is used at CG. That context would let me propose "
    "a definition that mirrors the reality on the ground."
)

st.write(
    "From my limited knowledge just from exploring the data, I don't think a simple metadata-only definition is possible. There are many "
    "grants that are independent but look similar, and many renewals that are much larger than the original grant."
)
st.write(
    "One key issue is that focus area names change over time, so related grants focused on the same area "
    "can be categorized as separate. To improve this, I'd seek to understand how focus area names have "
    "changed over time, to enable better historical analysis."
)
st.write(
    "While amount, date and focus area may not be enough to define renewals, the details column holds "
    "rich data that could help inform a definition. Some grants explicitly mention previous grants; others "
    "are clearly focused on the same area. A few techniques could be used to identify renewals:"
)
APPROACHES = {
    "Text embeddings": "Turn each grant's details into embeddings, and use the distance between pairs of "
    "grants to provide another factor that can help determine whether they are similar enough to count as a renewal.",
    "LLM analysis": "Find grants whose details explicitly describe them as a renewal, and identify the previous "
    "grant. This could be a standalone definition for historic data, or a source of truth for uncovering "
    "other factors closely linked to being a renewal.",
    "Decision tree model": "Build a categorization model from a human-reviewed set of renewals and non-renewals.",
    "Human review": "This dataset isn't huge, so reviewing candidate renewals by hand would give the highest "
    "quality result. If a permanent improvement is planned, such as linking grants to their renewals, "
    "combining human review with the options above would ensure high quality historic data.",
}
for row in (list(APPROACHES.items())[:2], list(APPROACHES.items())[2:]):
    for column, (title, description) in zip(st.columns(2), row):
        with column.container(border=True, height="stretch"):
            st.markdown(f"**{title}**")
            st.write(description)


# --- Data note ----

st.info(
    "**A data note:** An organization may have several grants that could each count as renewals "
    "of each other. A grant is only treated as a renewal or near miss of the **most recent** earlier grant "
    "that meets the definition. For example, if grants are given in 2021, 2022 and 2023 and all qualify "
    "as renewals, the 2023 grant is a renewal of 2022, and 2022 is a renewal of 2021. The 2023 grant "
    "is not a renewal of 2021 because the 2022 grant is more recent. This prevents organizations "
    "with many grants from producing exponentially large numbers of similar rows."
)