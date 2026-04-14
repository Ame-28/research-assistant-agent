"""LangGraph research agent — 4-node linear workflow.

Pipeline:
    search_node -> extract_node -> summarize_node -> store_node
"""

from datetime import datetime, timezone

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from tavily import TavilyClient
from typing_extensions import TypedDict

from config import settings


class ResearchState(TypedDict):
    """State flowing through the LangGraph pipeline."""

    query: str
    search_results: str
    extracted_content: str
    summary: str
    sources: list[str]
    status: str


async def search_node(state: ResearchState) -> dict:
    """Search the web using Tavily and collect raw results + source URLs."""
    try:
        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(query=state["query"], max_results=5)
        results = response.get("results", []) if isinstance(response, dict) else []

        sources: list[str] = []
        formatted_blocks: list[str] = []
        for item in results:
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()
            content = item.get("content", "").strip()
            if url:
                sources.append(url)
            formatted_blocks.append(
                f"Title: {title}\nURL: {url}\nContent: {content}"
            )

        formatted = "\n\n---\n\n".join(formatted_blocks) or "No results returned."
        return {"search_results": formatted, "sources": sources}
    except Exception as exc:
        return {
            "search_results": f"Search failed: {exc}",
            "sources": [],
        }


async def extract_node(state: ResearchState) -> dict:
    """Clean and extract the most useful text from the raw search results."""
    raw = state.get("search_results", "") or ""

    lines = [line.strip() for line in raw.splitlines()]
    seen: set[str] = set()
    deduped: list[str] = []
    for line in lines:
        if not line:
            if deduped and deduped[-1] != "":
                deduped.append("")
            continue
        if line in seen:
            continue
        seen.add(line)
        deduped.append(line)

    cleaned = "\n".join(deduped).strip()
    if len(cleaned) > 3000:
        cleaned = cleaned[:3000].rstrip() + "..."

    return {"extracted_content": cleaned}


async def summarize_node(state: ResearchState) -> dict:
    """Summarize the extracted content into a structured research note."""
    try:
        llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.3,
        )

        sources_block = "\n".join(f"- {url}" for url in state.get("sources", [])) or "- (none)"
        system = SystemMessage(
            content=(
                "You are a meticulous research assistant. Produce a concise, "
                "well-structured summary (200-400 words) with key-point bullets "
                "and reference the provided sources by URL where relevant."
            )
        )
        human = HumanMessage(
            content=(
                f"Research topic: {state['query']}\n\n"
                f"Source URLs:\n{sources_block}\n\n"
                f"Extracted content:\n{state.get('extracted_content', '')}\n\n"
                "Write the structured summary now."
            )
        )

        response = await llm.ainvoke([system, human])
        summary_text = response.content if hasattr(response, "content") else str(response)
        return {"summary": summary_text.strip()}
    except Exception as exc:
        return {"summary": f"Summarization failed: {exc}"}


async def store_node(state: ResearchState) -> dict:
    """Persist the research via the MCP server's save_research tool."""
    server_params = StdioServerParameters(
        command="python",
        args=["mcp_server.py"],
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                result = await session.call_tool(
                    "save_research",
                    arguments={
                        "title": state["query"],
                        "summary": state["summary"],
                        "sources": state["sources"],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

                status_text = (
                    result.content[0].text
                    if getattr(result, "content", None)
                    else "Saved successfully"
                )
                return {"status": status_text}
    except Exception as exc:
        return {"status": f"MCP storage failed: {exc}"}


def build_graph():
    """Assemble the linear 4-node LangGraph workflow."""
    workflow = StateGraph(ResearchState)

    workflow.add_node("search", search_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("summarize", summarize_node)
    workflow.add_node("store", store_node)

    workflow.set_entry_point("search")
    workflow.add_edge("search", "extract")
    workflow.add_edge("extract", "summarize")
    workflow.add_edge("summarize", "store")
    workflow.add_edge("store", END)

    return workflow.compile()


async def run_agent(query: str) -> dict:
    """Run the full research pipeline for a user query and return final state."""
    graph = build_graph()
    initial_state: ResearchState = {
        "query": query,
        "search_results": "",
        "extracted_content": "",
        "summary": "",
        "sources": [],
        "status": "",
    }
    result = await graph.ainvoke(initial_state)
    return result
