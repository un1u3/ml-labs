from __future__ import annotations

import streamlit as st

from executor import executor
from sql_generator import fix_sql, generate_sql, translate_to_nlp


st.set_page_config(page_title="Text2SQL", layout="wide")

st.title("Text2SQL")
st.write("Ask a question about the database.")

question = st.text_input(
    "Question",
    placeholder="Example: Show the top 5 customers by total payments",
)

run_query = st.button("Run", type="primary")

if run_query:
    if not question.strip():
        st.warning("Please enter a question.")
        st.stop()

    with st.spinner("Generating and running SQL..."):
        sql = generate_sql(question)
        output = executor(sql)

        if output["status"] == "error":
            sql = fix_sql(question, sql, output["error"])
            output = executor(sql)

        summary = ""
        if output["status"] == "success":
            summary = translate_to_nlp(question, output["data"])

    st.subheader("Generated SQL")
    st.code(sql, language="sql")

    if output["status"] == "success":
        st.success("Query completed.")

        st.subheader("Result")
        if output["data"]:
            st.dataframe(output["data"], use_container_width=True)
        else:
            st.info("No rows returned.")

        st.subheader("Summary")
        st.write(summary)
    else:
        st.error("Query failed.")
        st.code(output.get("error", "Unknown error"))
