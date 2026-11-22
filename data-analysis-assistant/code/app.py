import os

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from google import genai

from car_assistant import make_plan, calculate, explain_result, make_chart

st.set_page_config(page_title="Data Analysis Assistant")
st.title("Data Analysis Assistant")

uploaded = st.file_uploader("Upload a CSV", type=["csv"])
if uploaded is None:
    st.stop()

try:
    df = pd.read_csv(uploaded)
except (ValueError, UnicodeError) as error:
    st.error(f"Could not read this CSV: {error}")
    st.stop()

if df.empty:
    st.warning("The CSV has no data rows.")
    st.stop()

st.caption(f"{len(df):,} records · {df.shape[1]} columns")
st.dataframe(df.head(10))

api_key = os.getenv("GEMINI_API_KEY") or st.text_input("Gemini API key", type="password")
model = st.text_input("Gemini model", value=os.getenv("GEMINI_MODEL", ""))

with st.form("analysis"):
    question = st.text_input("Ask a question", placeholder="Which fuel type has the most records?")
    submitted = st.form_submit_button("Analyze")

if submitted:
    if not api_key or not model.strip() or not question.strip():
        st.warning("Enter your API key, model name, and question.")
        st.stop()

    client = genai.Client(api_key=api_key)

    try:
        with st.spinner("Analyzing the dataset..."):
            plan = make_plan(df, question, client, model.strip())
            result = calculate(df, plan)
            answer = explain_result(question, plan, result, client, model.strip())

        st.subheader("Answer")
        st.write(answer)

        if isinstance(result, pd.Series):
            st.dataframe(result.rename("Result").to_frame())
        elif plan["operation"] not in {"clarify", "unsupported"}:
            st.write("Pandas result", result)

        chart = make_chart(plan, result)
        if chart is not None:
            st.pyplot(chart)
            plt.close(chart)

        with st.expander("Analysis plan"):
            st.json(plan)

    except Exception as error:
        st.error(f"Could not complete the analysis ({type(error).__name__}). Check the model name, API access, and question.")
