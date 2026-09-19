import streamlit as st

import agent
import rag

if "ready" not in st.session_state:
    st.session_state.ready = rag.ingest()
    st.session_state.messages = []

st.title("Course Assistant")
q = st.text_input("Ask about the assignment documents")

if q:
    with st.spinner("Working on it..."):
        try:
            out = agent.run(q, st.session_state.messages)
        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.stop()
    if out["status"] == "clarify":
        st.info("I need a bit more info: " + out["answer"])
    else:
        st.write(out["answer"])
        if out["sources"]:
            st.caption("Sources: " + ", ".join(out["sources"]))
        if not out["verified"]:
            st.caption("Not fully verified against the documents.")
    st.caption(f"Steps: {out['iterations']}, tokens: {out['tokens']}")
    if st.button("New conversation"):
        st.session_state.messages = []
