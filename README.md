# ARCON Vetting Agent

This is a stateless ReAct agent built with LangGraph and GPT-4o to vet advertising content against ARCON regulations.


## Architecture

-   **Agent**: Stateless ReAct Agent (`src/agent.py`) using `langgraph`.
-   **LLM**: GPT-4o (handles text and images).
-   **Tools**: RAG Tool (`tools.py`) to query Supabase vector store.
-   **Database**: Supabase (`pgvector`).
-   **Frontend**: Streamlit.
