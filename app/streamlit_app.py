import hmac
import streamlit as st
from queries import load_table

st.set_page_config(page_title="Defining a grant renewal", layout="wide")

def check_password() -> bool:
    def password_entered():
        ok = hmac.compare_digest(st.session_state["password"], st.secrets["app_password"])
        st.session_state["authenticated"] = ok
        if ok:
            del st.session_state["password"]
    if st.session_state.get("authenticated"):
        return True
    st.text_input("Password", type="password", on_change=password_entered, key="password")
    if st.session_state.get("authenticated") is False:
        st.error("Incorrect password")
    return False

if not check_password():
    st.stop()

st.title("What counts as a renewal?")

pairs = load_table(st.secrets["pairs_table"])
st.write(f"Loaded {len(pairs):,} candidate grant pairs")
st.dataframe(pairs.head(20))