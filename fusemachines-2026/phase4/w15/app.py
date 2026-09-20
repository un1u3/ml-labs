import streamlit as st

import assistant
import rag

if "ready" not in st.session_state:
    st.session_state.ready = rag.ingest()

st.title("Course Assistant")
q = st.text_input("Ask about the assignment documents")

if q:
    with st.spinner("Thinking..."):
        try:
            out = assistant.ask(q)
        except RuntimeError as e:
            st.warning(str(e))
            st.stop()
    st.write(out["answer"])
    if out["sources"]:
        st.caption("Sources: " + ", ".join(out["sources"]))
    st.caption(f"Answered by: {out['provider']}")
