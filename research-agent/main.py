"""Main entry point — run the research assistant agent."""

import asyncio
import sys

from dotenv import load_dotenv

load_dotenv()

from agent import run_agent


async def main():
    """Parse CLI args, run the agent, and print the research result."""
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Explain retrieval augmented generation"

    print(f"\n🔍 Research Agent")
    print(f"   Query: {query}\n")

    result = await run_agent(query)

    print("=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    print(result.get("summary", "No summary generated."))
    print()
    print("🔗 SOURCES")
    for url in result.get("sources", []):
        print(f"   • {url}")
    print()
    print(f"💾 STATUS: {result.get('status', 'Unknown')}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
