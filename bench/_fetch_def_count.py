"""tiktoken cl100k count of the verbatim Fetch MCP tool-def (idle_def_tokens).

Same method as context-quality (Context7) + efficiency-starter (semble):
tokenize the literal {name, description, inputSchema} JSON the host loads at
startup. Source: modelcontextprotocol/servers src/fetch server.py list_tools().
"""

import json

import tiktoken

# VERBATIM from server.py list_tools() (captured 2026-06-07).
fetch_def = {
    "name": "fetch",
    "description": (
        "Fetches a URL from the internet and optionally extracts its contents as markdown.\n\n"
        "Although originally you did not have internet access, and were advised to refuse and "
        "tell the user this, this tool now grants you internet access. Now you can fetch the "
        "most up-to-date information and let the user know that."
    ),
    "inputSchema": {
        "properties": {
            "url": {"title": "Url", "type": "string", "description": "URL to fetch"},
            "max_length": {
                "title": "Max Length",
                "default": 5000,
                "type": "integer",
                "description": "Maximum number of characters to return.",
                "exclusiveMinimum": 0,
                "exclusiveMaximum": 1000000,
            },
            "start_index": {
                "title": "Start Index",
                "default": 0,
                "type": "integer",
                "description": (
                    "On return output starting at this character index, useful if a previous "
                    "fetch was truncated and more context is required."
                ),
                "minimum": 0,
            },
            "raw": {
                "title": "Raw",
                "default": False,
                "type": "boolean",
                "description": "Get the actual HTML content of the requested page, without simplification.",
            },
        },
        "required": ["url"],
        "type": "object",
    },
}

enc = tiktoken.get_encoding("cl100k_base")
blob = json.dumps(fetch_def, ensure_ascii=False)
print("fetch def chars:", len(blob))
print("fetch def cl100k tokens:", len(enc.encode(blob)))
