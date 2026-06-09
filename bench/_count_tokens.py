"""Deterministic token count of arbitrary content (cl100k_base proxy).

HIGH-validity lever for the extract lanes (web-research): tokenize EXACTLY what a
fetch/extract tool returned into context, instead of a noisy ccusage session-diff.
No cache noise, no side-model confound, reproducible to the token.

Usage:
  py bench/_count_tokens.py <file> [<file> ...]   # sum per file + grand total
  <something> | py bench/_count_tokens.py -        # count stdin

Note: cl100k_base is a PROXY; host tokenizers (Anthropic/OpenAI/Gemini) differ
~10-15%. Same proxy across all lanes ⇒ the RELATIVE delta is valid even if the
absolute count is approximate. Always compare lanes with the SAME encoder.
"""

import sys

import tiktoken

enc = tiktoken.get_encoding("cl100k_base")


def count(text: str) -> int:
    return len(enc.encode(text))


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    if argv == ["-"]:
        text = sys.stdin.read()
        print(f"stdin: {len(text)} chars / {count(text)} tokens (cl100k)")
        return 0
    total = 0
    for path in argv:
        try:
            with open(path, encoding="utf-8") as f:
                text = f.read()
        except OSError as e:
            print(f"{path}: ERROR {e}", file=sys.stderr)
            return 1
        toks = count(text)
        total += toks
        print(f"{path}: {len(text)} chars / {toks} tokens (cl100k)")
    if len(argv) > 1:
        print(f"TOTAL: {total} tokens (cl100k)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
