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
    st.text_input("Password", type="password", on_change=password_entered, key="password")
    if st.session_state.get("authenticated") is False:
        st.error("Incorrect password")
    return False

if not check_password():
    st.stop()

st.title("What counts as a renewal?")
st.write(
    "This dashboard explores metadata based definitions of a renewed grant. "
)
st.write(
    "Grant renewals, which is when one organization is given a related, subsequent grant after an initial grant, "
    "are not indicated in the source data. This dashboard explores whether it is possible to find a definition "
    "for a renewal using only grant metadata, such as amount, date and focus area - without using contextual information"
)
st.write(
    "Using the options on the left, choose your definitions to see how it impacts what counts as a renewal. "
    "Your current definition is:"
)
grants, pairs = load_tables(st.secrets["grants_table"], st.secrets["pairs_table"])

# --- Definition options ---
st.sidebar.header("Define a renewal")
min_months, max_months = st.sidebar.slider(
    "Months between first grant and renewal",
    min_value=0, max_value=160, value=(12, 24),
    help="Only subsequent grants that occured between the months specified here will be counted as a renewal. For example, 12 to 24 months means the second grant must be at least a year after the earlier, and at most 2 years."
)
min_percent, max_percent = st.sidebar.slider(
    "Renewed amount as a percent of first grant amount",
    min_value=0, max_value=500, value=(80, 200), step=5, format="%d%%",
    help="Only subsequent grants that are for a value between the percentages of the first grant defined here will be included. For example, 80% to 200% means the second grant must be the at least 80% of the size of the earlier, and at most twice as large to count as a renewal.",
)
# The renewal logic works in ratios, so 100% is a ratio of 1.0
min_ratio, max_ratio = min_percent / 100, max_percent / 100
same_focus_area = st.sidebar.checkbox("Renewals must be for the same focus area", value=True, help="If selected, this means that subsequent grants only count as renewals if they are in the same focus area.")

months = f"{min_months} month{'s' * (min_months != 1)}" if min_months == max_months else f"{min_months}–{max_months} months"
percent = f"{min_percent}%" if min_percent == max_percent else f"between {min_percent}% and {max_percent}%"
focus = ", `is in the same focus area`" if same_focus_area else ""
st.markdown(
    f"##### A grant is a renewal if it's made `{months}` after an earlier grant to the same "
    f"organisation{focus}, and is `{percent}` of the amount of that grant."
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
    help="Grants where the same organisation received an earlier grant, in any focus area. These are potential candidates to be renewals.",
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
        f"Renewals as a share of the {results.repeat_grants:,} grants where the same organisation "
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
    "organization": st.column_config.TextColumn("Organisation"),
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
        "Date": f"{pd.to_datetime(pair[f'{prefix}_grant_date']):%B %Y}",
        "Focus area": pair[f"{prefix}_focus_area"],
        "Details": grant["details"],
    }
    for label, value in fields.items():
        st.caption(label)
        # Escape $ so Streamlit doesn't render text between two dollar signs as maths
        st.markdown(str(value or "–").replace("$", r"\$"))

def show_pair(pair: pd.Series):
    """Pop-out content: shared figures at the top, then the two grants side by side."""
    months, ratio = st.columns(2)
    months.metric("Months apart", f"{pair['months_since_first']}")
    ratio.metric("Second grant as % of first", f"{pair['amount_ratio']:.0%}")
    # Only near misses have a reason
    if pair.get("reason"):
        st.markdown(f"**Why it's excluded:** {pair['reason']}")

    first, second = st.columns(2, border=True)
    with first:
        st.subheader("First grant")
        show_grant(pair, "first")
    with second:
        st.subheader("Second grant")
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
        "Select a row to see more details and determine whether it fits your chosen definition. "
    )
    selected_renewal = pair_table(results.renewals, key="renewals")
with near_tab:
    st.write(
        "This section shows pairs of grants to the same organisation that fail just one part of the selected definition, "
        f"and are otherwise close to qualifying as a renewal. Like renewals, each grant is only shown against "
        "its most recent near-miss earlier grant."
    )
    st.write(
        "Select a row to see more details of why it does not count as a renewal and decide if you need to adjust your definition."
    )
    selected_near_miss = pair_table(results.near_misses, key="near_misses")

# Only one pop-out can open per run, so a renewal takes priority over a near miss
selected = selected_renewal if selected_renewal is not None else selected_near_miss
if selected is not None:
    st.dialog(selected["organization"], width="large", on_dismiss=reset_selections)(show_pair)(selected)

st.info(
    "**A data note:** An organisation may have several grants that could each count as renewals "
    "of each other. A grant is only treated as a renewal or near miss of the **most recent** earlier grant "
    "that meets the definition. For example, if grants are given in 2021, 2022 and 2023 and all qualify "
    "as renewals, the 2023 grant is a renewal of 2022, and 2022 is a renewal of 2021. 2023 "
    "is not a renewal of grant 2021 because the 2022 grant is more recent. This prevents organizations"
    "with many grants from causing exponentially large numbers of similar rows."
)
