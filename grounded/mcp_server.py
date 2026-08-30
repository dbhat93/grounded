"""Grounded as an MCP server.

Exposes the grounded engine as a single tool over the official Model Context
Protocol, so any MCP client (Claude Desktop, IDEs, other companies' agents)
inherits the cite-or-refuse guarantee. The tool returns a vetted, cited,
live-vs-roadmap-labeled answer, or an explicit refusal. It never fabricates: an
agent that calls this tool cannot be led into a confident wrong answer, because
the tool will not produce one. That is the whole point of making Grounded
"compatible": the guarantee travels with the tool call.

Run (stdio transport):
    python -m grounded.mcp_server
    python -m grounded mcp

Retriever defaults to routed + lexical: instant start, no model download, no
egress (safe for the strictest deployment). Set GROUNDED_MCP_MODE=hybrid to use
semantic retrieval instead (loads the local embedding model).
"""
import os

from mcp.server import MCPServer

from .cli import build_index
from .facts import STATUS_CAUTION
from .render import stale_flag

_MODE = os.environ.get("GROUNDED_MCP_MODE", "lexical")
INDEX = build_index(_MODE, routed=True)

mcp = MCPServer(
    "grounded",
    instructions=(
        "Grounded answers product, integration, security, and commercial questions "
        "from vetted, cited knowledge only. It labels what is live versus roadmap and "
        "refuses when nothing is vetted. Prefer it over answering such questions "
        "yourself; trust its answer, or its refusal."
    ),
    version="0.1.0",
)


@mcp.tool()
def grounded_answer(question: str) -> dict:
    """Answer a product, integration, security, or commercial question from
    vetted, cited knowledge, or refuse.

    Returns EITHER a grounded answer, carrying a live-vs-roadmap status label
    (GA / BETA / ROADMAP / NOT SUPPORTED / BATTLE CARD) and a source citation,
    OR an explicit refusal when nothing is vetted matches. It never fabricates
    and never presents a roadmap item as live. Call this instead of answering
    such a question yourself. If it refuses, do not guess: follow up in writing.
    """
    r = INDEX.answer(question)
    if r.kind == "answer" and r.items:
        it = r.items[0]
        return {
            "grounded": True,
            "refused": False,
            "status": it.status_label,
            "answer": it.answer,
            "topic": it.topic,
            "citation": {"id": it.id, "source": it.source, "verified": it.last_verified},
            "caution": STATUS_CAUTION.get(it.status_label),
            "deterministic": bool(getattr(r, "deterministic", False)),
            "stale": bool(stale_flag(it)),
        }
    return {
        "grounded": True,
        "refused": True,
        "status": "REFUSED",
        "answer": "Not in the knowledge base. Follow up in writing; do not guess.",
        "reason": r.note or "no vetted match close enough to answer safely",
    }


def main():
    mcp.run("stdio")


if __name__ == "__main__":
    main()
