import streamlit as st
from snowflake.snowpark import Session
import os

# --------------------------------------------------
# Page Config
# --------------------------------------------------
st.set_page_config(
    page_title="QA Bot",
    page_icon="🤖",
    layout="centered"
)

# --------------------------------------------------
# Header (Agent Display)
# --------------------------------------------------
st.markdown(
    """
    <h1 style="text-align:center;">🤖 QA Bot</h1>
    <p style="text-align:center; color: gray;">
        QA bot powered by Snowflake Cortex & Semantic View
    </p>
    """,
    unsafe_allow_html=True
)

st.divider()

# --------------------------------------------------
# Example Questions (Clickable)
# --------------------------------------------------
st.markdown("### 💡 Try an example question")

example_questions = [
    "List all customers and their orders",
    "Which customer has the highest total sales",
    "Show total sales by city",
]

cols = st.columns(len(example_questions))
for i, q in enumerate(example_questions):
    if cols[i].button(q):
        st.session_state["question"] = q

st.divider()

# --------------------------------------------------
# Question Input
# --------------------------------------------------
question = st.text_input(
    "Ask a question about Sales or Customers",
    key="question",
    placeholder="e.g. Which customer has the highest total sales"
)

# --------------------------------------------------
# Ask Button
# --------------------------------------------------
if st.button("Ask 🤔", use_container_width=True):

    # ---- Rule: Minimum 4 words ----
    if len(question.strip().split()) < 4:
        st.error("❌ Invalid Length")
        st.stop()

    with st.spinner("Thinking..."):

        # ---- Snowflake Connection ----
        session = Session.builder.configs({
            "account": os.getenv("SNOWFLAKE_ACCOUNT"),
            "user": os.getenv("SNOWFLAKE_USER"),
            "password": os.getenv("SNOWFLAKE_PASSWORD"),
            "role": os.getenv("SNOWFLAKE_ROLE"),
            "warehouse": "DEMO_WH",
            "database": "DEMO_DB",
            "schema": "PUBLIC"
        }).create()

        # ---- Disable Caching ----
        session.sql("ALTER SESSION SET USE_CACHED_RESULT = FALSE").collect()

        # ---- Cortex Prompt ----
        prompt = f"""
You are a Snowflake Cortex Analyst.

You understand the business using this semantic model:
- Customers place sales orders
- SALES.CUSTOMER_ID joins to CUSTOMERS.CUSTOMER_ID
- Measures: AMOUNT
- Time dimension: ORDER_DATE

Generate ONE valid Snowflake SELECT query.
Do not explain.
Do not include markdown.
Do not include comments.

Execute queries ONLY on this view:
DEMO_DB.PUBLIC.SHIVANSHI_EXEC_VIEW

Question:
{question}
"""

        cortex_sql = f"""
        SELECT SNOWFLAKE.CORTEX.COMPLETE(
            'snowflake-arctic',
            $$ {prompt} $$
        ) AS SQL_QUERY
        """

        # ---- Generate SQL ----
        generated_sql = session.sql(cortex_sql).collect()[0]["SQL_QUERY"]

        if not generated_sql.strip().lower().startswith("select"):
            st.error("⚠️ Unable to generate a valid query")
            st.stop()

        # ---- Execute SQL ----
        df = session.sql(generated_sql).to_pandas()
        session.close()

    # --------------------------------------------------
    # Results
    # --------------------------------------------------
    st.success("✅ Answer generated")

    with st.expander("🔍 View generated SQL"):
        st.code(generated_sql, language="sql")

    st.markdown("### 📊 Result")
    st.dataframe(df, use_container_width=True)
