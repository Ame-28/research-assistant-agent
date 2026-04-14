# Research Assistant Agent

AI agent built with **LangGraph** that accepts a research topic from the user, searches the web using **Tavily**, extracts and cleans the returned content, summarizes it with an **OpenAI LLM**, and stores the structured research note in a **SQLite** database through a **Model Context Protocol (MCP)** server.

---

## Architecture

```
User Query
    │
    ▼
┌──────────────┐
│  search_node │  ← Calls Tavily Search API
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ extract_node │  ← Cleans / de-duplicates / truncates text
└──────┬───────┘
       │
       ▼
┌───────────────┐
│summarize_node │  ← ChatOpenAI structured summary
└──────┬────────┘
       │
       ▼
┌──────────────┐
│  store_node  │  ← MCP client → save_research → SQLite
└──────────────┘
```

```
MCP Server (stdio)
├── save_research   — Insert research entry into SQLite
├── list_research   — List all saved entries
└── search_research — Search entries by keyword
```

---

## Setup

1. Clone the repository.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows
   .venv\Scripts\activate
   # macOS / Linux
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create your `.env` file from the template and fill in your API keys:
   ```bash
   cp .env.example .env
   ```
   Required keys:
   - `OPENAI_API_KEY`
   - `TAVILY_API_KEY`
5. Run the agent:
   ```bash
   python main.py "your research topic here"
   ```

---

## Usage

```bash
python main.py "What is retrieval augmented generation"
```

Expected output:

```
🔍 Research Agent
   Query: What is retrieval augmented generation

============================================================
📋 SUMMARY
============================================================
Retrieval-Augmented Generation (RAG) is a technique that ...
- Key point 1 ...
- Key point 2 ...
...

🔗 SOURCES
   • https://example.com/rag-overview
   • https://example.com/rag-paper
   ...

💾 STATUS: Saved research: What is retrieval augmented generation
============================================================
```

Inspect the saved data directly:
```bash
python -c "import sqlite3; print(sqlite3.connect('research.db').execute('SELECT id, title, timestamp FROM research').fetchall())"
```

---

## MCP Server

The MCP server (`mcp_server.py`) uses the FastMCP high-level API and communicates over **stdio**. It exposes three tools:

| Tool | Parameters | Returns | Purpose |
|------|------------|---------|---------|
| `save_research` | `title: str`, `summary: str`, `sources: str` (JSON array), `timestamp: str` (ISO 8601) | Confirmation string | Inserts a research entry into SQLite. |
| `list_research` | *(none)* | Formatted text of all entries, or a "no entries" message | Lists every saved research entry. |
| `search_research` | `keyword: str` | Matching entries or a "no matches" message | Case-insensitive keyword search over title and summary. |

The server auto-creates `research.db` and the `research` table on first startup.

You can run it standalone for debugging:
```bash
python mcp_server.py
```
It will wait for stdio MCP traffic; press `Ctrl+C` to exit.

---

## Technologies Used

| Library | Purpose |
|---------|---------|
| `langgraph` | Defines the 4-node research workflow (state graph). |
| `langchain-openai` | `ChatOpenAI` wrapper used by `summarize_node`. |
| `langchain-core` | Message primitives (`SystemMessage`, `HumanMessage`). |
| `mcp` | Model Context Protocol SDK — FastMCP server + stdio client. |
| `tavily-python` | Tavily web search API client used by `search_node`. |
| `pydantic` / `pydantic-settings` | Typed settings loaded from `.env`. |
| `python-dotenv` | Loads environment variables at startup. |
| `sqlite3` (stdlib) | Local persistence for research entries. |

---

