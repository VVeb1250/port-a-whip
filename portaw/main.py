"""portaw CLI entrypoint (v0.3).

Command surface: port-a-whip-spec.md §8. Wires to sets/ (loader, patcher, shim),
kernel/ (ranking, registry, embed), adapters/ (router, memory-hooks),
memory/ (schema, store, retrieval, inject, capture, consolidate, detect, harvest).
6 groups, 29 commands. See CLAUDE.md for architecture + build status.
"""

import sys

import click

from portaw import __version__
from portaw.config import detect_hosts


@click.group()
@click.version_option(version=__version__)
def cli():
    """🐾 port-a-whip — curated sets + capability router + lesson-memory for coding agents."""


@cli.group()
def sets():
    """List / inspect curated sets (L1)."""


@sets.command("list")
def sets_list():
    """List curated sets."""
    from portaw.sets.loader import SetsError, load_all

    try:
        all_sets = load_all()
    except SetsError as e:
        raise click.ClickException(str(e))
    for s in all_sets:
        click.echo(f"  {s.name:<18} mcp={s.mcp_count} non_mcp={len(s.non_mcp)}  — {s.description[:70]}")


@sets.command("show")
@click.argument("set_name")
def sets_show(set_name: str):
    """Show a set: tools + token profile + compat notes."""
    from portaw.sets.loader import SetsError, get_set

    try:
        s = get_set(set_name)
    except SetsError as e:
        raise click.ClickException(str(e))
    click.echo(f"{s.name}  (mcp={s.mcp_count}, non_mcp={len(s.non_mcp)})")
    click.echo(s.description)
    if s.trigger_terms:
        click.echo(f"\ntrigger: {', '.join(s.trigger_terms)}")
    if s.mcp:
        click.echo("\nMCP:")
        for m in s.mcp:
            click.echo(f"  - {m['tool']} ({m.get('ref', '?')})")
    if s.non_mcp:
        click.echo("\nnon-MCP:")
        for m in s.non_mcp:
            click.echo(f"  - {m['tool']} ({m.get('ref', '?')})")
    tp = s.raw.get("token_profile", {})
    if tp:
        click.echo("\ntoken_profile:")
        hosts = tp.get("hosts") if isinstance(tp, dict) else None
        if isinstance(hosts, dict):  # v2 structured (provenance-tagged)
            for host, e in hosts.items():
                if not isinstance(e, dict):
                    continue
                bits = [e.get("provenance", "?")]
                if e.get("delta_pct") is not None:
                    bits.append(f"Δ{e['delta_pct']:+}%")
                if e.get("idle_def_tokens") is not None:
                    bits.append(f"idle {e['idle_def_tokens']} tok")
                click.echo(f"  {host}: {' | '.join(bits)}")
                if e.get("note"):
                    click.echo(f"      {e['note']}")
        else:  # legacy flat string map
            for k, v in tp.items():
                if not k.startswith("_"):
                    click.echo(f"  {k}: {v}")
    if s.raw.get("compat_notes"):
        click.echo(f"\ncompat: {s.raw['compat_notes']}")


def _print_shim(steps, header: str):
    if not steps:
        return
    click.echo(f"\n{header} (run manually — paw does NOT auto-exec vendor installers):")
    for st in steps:
        flag = " [vendor]" if st.runs_vendor_code else ""
        click.echo(f"  • [{st.tool}] {st.label}{flag}\n      {st.cmd}")


@cli.command()
@click.argument("set_name")
@click.option("--host", default=None, help="Target host (claude-code/codex/gemini).")
@click.option("--force", is_flag=True, help="Re-patch even if a server is already present.")
def install(set_name: str, host: str | None, force: bool):
    """Install a set: auto-patch MCP config (backup+validate) + show manual shim steps."""
    from portaw.sets.install import install_set
    from portaw.sets.loader import SetsError
    from portaw.sets.patcher import PatchError

    try:
        res = install_set(set_name, host, force=force)
    except (SetsError, PatchError, ValueError) as e:
        raise click.ClickException(str(e))

    click.echo(f"install '{res.set_name}' → host {res.host}")
    for tool, backup in res.patched:
        b = f" (backup {backup.name})" if backup else " (new config)"
        click.echo(f"  ✓ patched MCP: {tool}{b}")
    for tool in res.skipped:
        click.echo(f"  · skipped (already present): {tool}  — use --force to overwrite")
    for tool in res.alt_skipped:
        click.echo(f"  · skipped (host-conditional alt — anchored to another host): {tool}")
    if not res.patched and not res.skipped:
        click.echo("  (no MCP tools in this set — all steps are manual below)")
    _print_shim(res.shim_steps, "MANUAL STEPS")
    if res.ceiling_warning:
        click.echo(f"\n⚠ N1 ceiling: {res.ceiling_warning}")


@cli.command()
@click.argument("set_name")
@click.option("--host", default=None)
def remove(set_name: str, host: str | None):
    """Remove a set: un-patch MCP config (backup) + show manual reverse steps."""
    from portaw.sets.install import remove_set
    from portaw.sets.loader import SetsError

    try:
        res = remove_set(set_name, host)
    except (SetsError, ValueError) as e:
        raise click.ClickException(str(e))
    click.echo(f"remove '{res.set_name}' → host {res.host}")
    for tool, backup in res.removed:
        b = f" (backup {backup.name})" if backup else ""
        click.echo(f"  ✓ un-patched MCP: {tool}{b}")
    if not res.removed:
        click.echo("  (no MCP tools were present)")
    _print_shim(res.reverse_shim, "MANUAL CLEANUP (reverse these yourself)")


@cli.command()
@click.argument("set_name")
@click.option("--host", default=None, help="Target host (claude-code/codex/gemini) — "
              "resolves host-conditional anchors. Default: auto-detect.")
def verify(set_name: str, host: str | None):
    """§10 health-check: is each tool in the set actually reachable on PATH?"""
    from portaw.sets.healthcheck import check_set
    from portaw.sets.install import resolve_host
    from portaw.sets.loader import SetsError

    try:
        if host is None:
            found = detect_hosts()
            # single detected host wins; ambiguous/none keeps the historical default
            hid = found[0] if len(found) == 1 else "claude-code"
        else:
            hid = resolve_host(host)
        h = check_set(set_name, hid)  # type: ignore[arg-type]
    except (SetsError, ValueError) as e:
        raise click.ClickException(str(e))
    mark = {"ok": "✓", "missing": "✗", "config-only": "·", "alt": "↷"}
    for t in h.tools:
        click.echo(f"  {mark[t.status]} {t.tool} ({t.kind}): {t.status} — {t.detail}")
    click.echo(f"\ngate: {'PASS' if h.ok else 'FAIL — install missing tools'}")
    if not h.ok:
        raise SystemExit(1)


@cli.command()
def doctor():
    """Env check + host detect + host-config parse-validity."""
    import json as _json

    from portaw.config import host_config

    hosts = detect_hosts()
    click.echo(f"detected hosts: {', '.join(hosts) if hosts else 'none'}")
    for h in hosts:
        hc = host_config(h)
        try:
            text = hc.path.read_text(encoding="utf-8")
            if hc.fmt == "json":
                _json.loads(text)
            else:
                import tomllib

                tomllib.loads(text)
            click.echo(f"  ✓ {h}: {hc.path} parses ({hc.fmt})")
        except Exception as e:  # report, don't crash
            click.echo(f"  ✗ {h}: {hc.path} INVALID {hc.fmt} — {e}")
    try:
        from portaw.sets.loader import load_all

        click.echo(f"registry: {len(load_all())} curated sets loaded OK")
    except Exception as e:
        click.echo(f"registry: ERROR — {e}")


@cli.group()
def bench():
    """B1 token-delta bench — diff two runs via ccusage (spec §10, no vibes)."""


@bench.command("list")
@click.option("--agent", default=None, help="Filter host: claude/codex/gemini.")
@click.option("-n", "limit", default=15, help="Rows to show.")
def bench_list(agent: str | None, limit: int):
    """List recent sessions (id + date + tokens) to pick A/B ids from."""
    from portaw.bench import CcusageError, load_sessions

    try:
        sessions = load_sessions(agent)  # type: ignore[arg-type]
    except CcusageError as e:
        raise click.ClickException(str(e))
    sessions.sort(key=lambda s: s.last_activity, reverse=True)
    click.echo(f"{'session':<10}{'date':<12}{'agent':<8}{'totalTokens':>14}{'cost':>10}")
    for s in sessions[:limit]:
        click.echo(
            f"{s.period[:8]:<10}{s.last_activity:<12}{s.agent:<8}"
            f"{s.tokens['totalTokens']:>14,}{s.total_cost:>9.2f}"
        )


@bench.command("ab")
@click.argument("baseline_id")
@click.argument("treated_id")
@click.option("--agent", default=None, help="Filter host before matching ids.")
@click.option("--json", "as_json", is_flag=True, help="Emit raw diff JSON.")
def bench_ab(baseline_id: str, treated_id: str, agent: str | None, as_json: bool):
    """Diff token/cost: BASELINE (tool off) → TREATED (tool on)."""
    import json as _json

    from portaw.bench import CcusageError, diff, find_session, format_report, load_sessions

    try:
        sessions = load_sessions(agent)  # type: ignore[arg-type]
        base = find_session(sessions, baseline_id)
        treat = find_session(sessions, treated_id)
    except CcusageError as e:
        raise click.ClickException(str(e))
    d = diff(base, treat)
    click.echo(_json.dumps(d, indent=2) if as_json else format_report(d))


@bench.command("how")
def bench_how():
    """Print the A/B protocol (controlled-workload requirement)."""
    from portaw.bench import bench_protocol

    click.echo(bench_protocol())


@cli.group()
def router():
    """Capability router (L2)."""


@router.command("run")
@click.option("--host", default="claude-code", help="Host that fired the hook (sets hookEventName).")
def router_run(host: str):
    """Hook entrypoint: read prompt-submit stdin, inject capability matches."""
    # Safe-by-construction: never raise, never block a prompt.
    try:
        from portaw.adapters.router import run_hook

        out = run_hook(host=host)  # type: ignore[arg-type]
        if out:
            sys.stdout.buffer.write(out.encode("utf-8"))
    except Exception:
        pass
    raise SystemExit(0)


@router.command("test")
@click.argument("prompt", nargs=-1, required=True)
def router_test(prompt: tuple[str, ...]):
    """Dry-run: show what the router would inject for a prompt."""
    from portaw.adapters.router import format_context, route_prompt

    hits = route_prompt(" ".join(prompt))
    if not hits:
        click.echo("(silent — nothing cleared the confidence floor)")
        return
    click.echo(format_context(hits))
    for h in hits:
        click.echo(f"    score={h.score:.3f} type={h.cap.ctype}")


@router.command("enable")
@click.option("--host", default=None, help="claude-code (default) / codex / gemini.")
@click.option("--command", default=None, help="Hook command to wire (default: per-host).")
def router_enable(host: str | None, command: str | None):
    """Wire the router hook into the host's hook config (backup + idempotent)."""
    from portaw.adapters.router import default_command, enable
    from portaw.sets.install import resolve_host

    try:
        hid = resolve_host(host) if host is None else host  # type: ignore[arg-type]
        changed, backup = enable(hid, command=command)  # type: ignore[arg-type]
    except ValueError as e:
        raise click.ClickException(str(e))
    cmd = command if command is not None else default_command(hid)  # type: ignore[arg-type]
    if not changed:
        click.echo(f"router already wired on {hid}")
    else:
        b = f" (backup {backup.name})" if backup else " (new config)"
        click.echo(f"router enabled on {hid}: '{cmd}'{b}")
        click.echo("takes effect next session.")


@router.command("disable")
@click.option("--host", default=None)
def router_disable(host: str | None):
    """Remove the router hook from settings.json."""
    from portaw.adapters.router import disable
    from portaw.sets.install import resolve_host

    try:
        hid = resolve_host(host) if host is None else host  # type: ignore[arg-type]
        removed = disable(hid)  # type: ignore[arg-type]
    except ValueError as e:
        raise click.ClickException(str(e))
    click.echo(f"router {'disabled' if removed else 'was not wired'} on {hid}")


@router.command("status")
@click.option("--host", default=None)
def router_status(host: str | None):
    """Show host + router wiring state."""
    from portaw.adapters.router import status
    from portaw.sets.install import resolve_host

    try:
        hid = resolve_host(host) if host is None else host  # type: ignore[arg-type]
        st = status(hid)  # type: ignore[arg-type]
    except ValueError as e:
        raise click.ClickException(str(e))
    click.echo(f"host={st['host']} event={st['event']} wired={st['wired']} settings={st['settings']}")


@cli.group()
def memory():
    """Lesson + project memory (L3)."""


@memory.command("recall")
@click.argument("prompt", nargs=-1, required=True)
@click.option("--symbol", "symbols", multiple=True, help="Edit-target symbol(s) being touched.")
@click.option("--path", "paths", multiple=True, help="Edit-target path(s) being touched.")
@click.option("--stack", "stacks", multiple=True,
              help="Host stack(s) for eligibility (default: auto-detected from cwd markers).")
@click.option("--project", "project_id", default=None,
              help="Project id for project:* eligibility (default: cwd name).")
@click.option("--embed", "use_embed", is_flag=True,
              help="Enable tier-2 semantic fallback (cross-lingual/paraphrase; needs [embed] extra).")
def memory_recall(prompt: tuple[str, ...], symbols: tuple[str, ...],
                  paths: tuple[str, ...], stacks: tuple[str, ...],
                  project_id: str | None, use_embed: bool):
    """Dry-run retrieval: what memory would inject for a prompt (+ optional edit-target)."""
    from pathlib import Path

    from portaw.memory.anchors import AnchorQuery
    from portaw.memory.context import host_context
    from portaw.memory.inject import format_memory, select
    from portaw.memory.retrieval import recall
    from portaw.memory.store import load_lessons, load_project

    entries = load_lessons() + load_project()
    if not entries:
        click.echo("(no memory yet — add some with `portaw memory add`)")
        return
    embed_fn = None
    if use_embed:
        from portaw.kernel.embed import make_embedder
        embed_fn = make_embedder()
        if embed_fn is None:
            click.echo("(--embed requested but model/libs unavailable — TF-IDF only)", err=True)
    q = AnchorQuery(symbols=tuple(symbols), paths=tuple(paths))
    # Without a context, every stack:* / project:* lesson is ineligible and dies
    # silently — derive one from the cwd so scoped lessons can actually fire.
    ctx = host_context(Path.cwd(), stacks=frozenset(stacks) or None,
                       project_id=project_id)
    scored = recall(" ".join(prompt), entries, query=q, ctx=ctx, embed_fn=embed_fn)
    selected = select(scored)
    block = format_memory(selected)
    if not block:
        click.echo("(silent — nothing cleared the floor)")
        return
    click.echo(block)
    for s in selected:
        click.echo(f"    score={s.score:.3f} rel={s.relevance:.2f} "
                   f"anchor={s.anchor:.2f} act={s.activation:.2f} type={s.entry.type}")


@memory.command("list")
@click.option("--type", "etype", default=None, help="Filter: lesson / project.")
def memory_list(etype: str | None):
    """List stored memory entries."""
    from portaw.memory.store import load_lessons, load_project

    entries = load_lessons() + load_project()
    if etype:
        entries = [e for e in entries if e.type == etype]
    if not entries:
        click.echo("(empty)")
        return
    for e in sorted(entries, key=lambda x: -x.recurrence):
        pin = "★" if e.pinned else " "
        click.echo(f"  {pin} {e.id} [{e.type:<7}] {e.applicability:<16} "
                   f"×{e.recurrence:<3} {e.body[:60]}")


@memory.command("add")
@click.argument("body", nargs=-1, required=True)
@click.option("--type", "etype", type=click.Choice(["lesson", "project"]), default="lesson")
@click.option("--scope", type=click.Choice(["global", "project"]), default=None,
              help="Default: global for lessons, project for project-memory.")
@click.option("--applicability", default=None,
              help="universal | stack:<x> | project:<id> (lessons only — a project "
                   "entry is always scoped to the cwd project).")
@click.option("--trigger", "triggers", multiple=True, help="Router trigger term(s).")
@click.option("--symbol", "symbols", multiple=True, help="Anchor symbol(s).")
@click.option("--path", "paths", multiple=True, help="Anchor path(s).")
@click.option("--pin", is_flag=True, help="Always-on tier (highest-ROI universal only).")
@click.option("--confidence", default=0.9, type=float,
              help="Manual adds default to 0.9 (a deliberate human assertion = trusted "
                   "for injection even at universal scope). Lower it for a tentative note.")
def memory_add(body, etype, scope, applicability, triggers, symbols, paths, pin, confidence):
    """Add a memory entry (compressed one-liner body).

    Typing this command IS the human confirm the project-write gate asks for
    (gate.accepts: project writes need explicit confirmation — a deliberate
    `memory add --type project` satisfies it by construction)."""
    from datetime import date

    from portaw.memory.anchors import Anchors
    from portaw.memory.schema import MemoryEntry
    from portaw.memory.store import (
        load_lessons,
        load_project,
        save_lessons,
        save_project,
        upsert,
    )

    from pathlib import Path

    if etype == "project" and applicability is not None:
        # refuse rather than silently override — the flag would be a no-op lie
        raise click.ClickException(
            "--applicability applies to lessons only; a project entry is always "
            f"scoped to project:{Path.cwd().name}"
        )
    scope = scope or ("global" if etype == "lesson" else "project")
    entry = MemoryEntry.new(
        etype, " ".join(body), scope,
        applicability=(applicability or "universal") if etype == "lesson"
        else f"project:{Path.cwd().name}",
        trigger_terms=tuple(triggers),
        anchors=Anchors(symbols=tuple(symbols), paths=tuple(paths)),
        pinned=pin, confidence=confidence,
        source="user", last_seen=date.today().isoformat(),
    )
    today = date.today().isoformat()
    if etype == "lesson":
        save_lessons(upsert(load_lessons(), entry, last_seen=today))
    else:
        save_project(upsert(load_project(), entry, last_seen=today))
    click.echo(f"added [{etype}] {entry.id}: {entry.body[:60]}")


def _curation_store(which: str):
    """(load, save) pair for a curation target: global lessons or this repo's
    project-memory — pin/rm work on both, no hand-editing jsonl."""
    from portaw.memory.store import load_lessons, load_project, save_lessons, save_project

    if which == "project":
        return load_project, save_project
    return load_lessons, save_lessons


@memory.command("pin")
@click.argument("entry_id")
@click.option("--unpin", is_flag=True, help="Remove the always-on flag instead.")
@click.option("--store", "which", type=click.Choice(["global", "project"]), default="global",
              help="Which store to curate (default: global lessons).")
def memory_pin(entry_id: str, unpin: bool, which: str):
    """Pin/unpin an existing entry by id (always-on tier — bypasses the recall floor)."""
    from dataclasses import replace

    load, save = _curation_store(which)
    entries = load()
    hit = next((e for e in entries if e.id == entry_id or e.id.startswith(entry_id)), None)
    if hit is None:
        raise click.ClickException(
            f"no {which} entry with id {entry_id!r} (see `portaw memory list`)")
    save([replace(e, pinned=not unpin) if e.id == hit.id else e for e in entries])
    click.echo(f"{'unpinned' if unpin else 'pinned ★'} {hit.id}: {hit.body[:60]}")


@memory.command("export")
@click.option("--out", "out_path", default=None, help="Write to a file (default: stdout).")
def memory_export(out_path: str | None):
    """Render the lesson store as readable markdown — the human review surface.

    GENERATED VIEW, not a source: editing it changes nothing (the jsonl store is
    the single source; curate with memory add/pin/rm)."""
    from collections import defaultdict
    from pathlib import Path

    from portaw.memory.store import load_lessons

    entries = load_lessons()
    if not entries:
        click.echo("(empty)")
        return
    groups: dict[str, list] = defaultdict(list)
    for e in entries:
        groups[e.applicability].append(e)
    lines = ["# paw lessons (GENERATED — edits here change nothing; "
             "source = ~/.paw/memory/lessons.jsonl)", ""]
    for tag in sorted(groups):
        lines.append(f"## {tag}")
        for e in sorted(groups[tag], key=lambda x: -x.recurrence):
            pin = "★ " if e.pinned else ""
            detail = f" → {e.detail_ref}" if e.detail_ref else ""
            lines.append(f"- {pin}`{e.id[:8]}` {e.body} "
                         f"(×{e.recurrence}, {e.last_seen or '?'}, c={e.confidence:.2f}){detail}")
        lines.append("")
    text = "\n".join(lines)
    if out_path:
        Path(out_path).write_text(text, encoding="utf-8")
        click.echo(f"wrote {len(entries)} lesson(s) to {out_path}")
    else:
        click.echo(text)


@memory.command("observations")
@click.option("--min-count", default=1, help="Only show signatures hit at least this often.")
def memory_observations(min_count: int):
    """Show the runtime error ledger: repeat-offenders + lessons that aren't working.

    Two signals the write-once store can't give: un-lessoned repeats (capture these)
    and lessons whose error STILL recurs after they were written (fix may be wrong /
    not surfacing)."""
    from portaw.memory import observations

    recs = [r for r in observations.load().values()
            if int(r.get("count", 0)) >= min_count]
    if not recs:
        click.echo("(no observations yet — the Bash-failure hook fills this live)")
        return

    uncovered = observations.uncovered_repeats(min_count=2)
    if uncovered:
        click.echo("⚠️  repeated errors with NO lesson (capture these):")
        for r in uncovered:
            click.echo(f"    ×{r['count']:<3} {r['sig']}   (since {r.get('first_seen','?')})")

    leaks = observations.recurring_despite_lesson()
    if leaks:
        click.echo("\n🔁 errors STILL recurring after a lesson exists (fix may be wrong):")
        for r in leaks:
            click.echo(f"    +{observations.linked_misses(r):<3} after lesson {r.get('lesson_id','?')[:8]}"
                       f"   {r['sig']}")

    click.echo(f"\nall signatures (≥{min_count}):")
    for r in sorted(recs, key=lambda x: -int(x.get("count", 0))):
        cov = f"lesson {r['lesson_id'][:8]}" if r.get("lesson_id") else "—"
        click.echo(f"  ×{r['count']:<3} {r['sig']:<40} {cov}")


@memory.command("rm")
@click.argument("entry_ids", nargs=-1, required=True)
@click.option("--store", "which", type=click.Choice(["global", "project"]), default="global",
              help="Which store to curate (default: global lessons).")
def memory_rm(entry_ids: tuple[str, ...], which: str):
    """Remove entr(ies) by id (curation — e.g. a superseded duplicate)."""
    load, save = _curation_store(which)
    entries = load()
    drop = {e.id for e in entries for want in entry_ids
            if e.id == want or e.id.startswith(want)}
    if not drop:
        raise click.ClickException(f"no {which} entry matches {', '.join(entry_ids)}")
    save([e for e in entries if e.id not in drop])
    click.echo(f"removed {len(drop)}: {', '.join(sorted(drop))}")


@memory.command("capture")
@click.option("--trigger", required=True, help="What went wrong (short).")
@click.option("--fix", required=True, help="What to do instead.")
@click.option("--symbol", "symbols", multiple=True)
@click.option("--path", "paths", multiple=True)
@click.option("--stack", default="", help="Framework hint → stack:<x>.")
@click.option("--env", "env_level", is_flag=True, help="Env/shell-level → universal.")
@click.option("--confidence", default=0.6, type=float)
@click.option("--project", "project_id", default=None, help="Project id (default: cwd name).")
def memory_capture(trigger, fix, symbols, paths, stack, env_level, confidence, project_id):
    """Capture a failure→fix as a lesson (gate-checked)."""
    from pathlib import Path

    from portaw.memory.capture import FailureSignal, capture

    pid = project_id or Path.cwd().name
    sig = FailureSignal(
        trigger=trigger, fix=fix, symbols=tuple(symbols), paths=tuple(paths),
        stack=stack, env_level=env_level, confidence=confidence,
    )
    res = capture(sig, pid)
    if res.stored:
        click.echo(f"captured [{res.entry.applicability}] {res.entry.id}: {res.entry.body[:60]}")
    else:
        click.echo(f"NOT stored — {res.verdict.reason}")
        raise SystemExit(1)


@memory.command("enable")
@click.option("--host", default=None, help="claude-code (default) / codex / gemini.")
def memory_enable(host: str | None):
    """Wire the capture hook into the host's Stop event (backup + idempotent)."""
    from portaw.memory.hookwire import capture_command, enable_capture
    from portaw.sets.install import resolve_host

    try:
        hid = resolve_host(host) if host is None else host  # type: ignore[arg-type]
        changed, backup = enable_capture(hid)  # type: ignore[arg-type]
    except ValueError as e:
        raise click.ClickException(str(e))
    if not changed:
        click.echo(f"capture hook already wired on {hid}")
    else:
        b = f" (backup {backup.name})" if backup else " (new config)"
        click.echo(f"capture hook enabled on {hid}: '{capture_command(hid)}'{b}")
        click.echo("takes effect next session.")


@memory.command("disable")
@click.option("--host", default=None)
def memory_disable(host: str | None):
    """Remove the capture hook from the host's Stop event."""
    from portaw.memory.hookwire import disable_capture
    from portaw.sets.install import resolve_host

    try:
        hid = resolve_host(host) if host is None else host  # type: ignore[arg-type]
        removed = disable_capture(hid)  # type: ignore[arg-type]
    except ValueError as e:
        raise click.ClickException(str(e))
    click.echo(f"capture hook {'disabled' if removed else 'was not wired'} on {hid}")


@memory.command("status")
@click.option("--host", default=None)
def memory_status(host: str | None):
    """Show capture-hook wiring state."""
    from portaw.memory.hookwire import capture_status
    from portaw.sets.install import resolve_host

    try:
        hid = resolve_host(host) if host is None else host  # type: ignore[arg-type]
        st = capture_status(hid)  # type: ignore[arg-type]
    except ValueError as e:
        raise click.ClickException(str(e))
    click.echo(f"host={st['host']} event={st['event']} wired={st['wired']} settings={st['settings']}")


@memory.command("capture-hook")
@click.option("--host", default="claude-code", help="Host that fired the Stop event.")
def memory_capture_hook(host: str):
    """Stop-hook entrypoint: read a paw_lesson payload from stdin, store it. Never fails."""
    try:
        from portaw.memory.capture import run_capture_hook

        results = run_capture_hook()
        stored = [r for r in results if r.stored]
        if stored:
            ids = ", ".join(r.entry.id for r in stored)
            click.echo(f"paw memory: captured {len(stored)} ({ids})", err=True)
    except Exception:
        pass
    raise SystemExit(0)


@memory.command("session-hook")
def memory_session_hook():
    """SessionStart entrypoint: inject pinned lessons once per session. Never fails."""
    try:
        from portaw.adapters.memory_hooks import run_session_hook

        out = run_session_hook()
        if out:
            click.echo(out)
    except Exception:
        pass
    raise SystemExit(0)


@memory.command("tool-hook")
def memory_tool_hook():
    """PostToolUse entrypoint: Bash-failure / edit-anchor recall. Never fails."""
    try:
        from portaw.adapters.memory_hooks import run_tool_hook

        out = run_tool_hook()
        if out:
            click.echo(out)
    except Exception:
        pass
    raise SystemExit(0)


@memory.command("inject-enable")
@click.argument("surface", type=click.Choice(["session", "tool", "all"]))
@click.option("--host", default="claude-code")
def memory_inject_enable(surface: str, host: str):
    """Wire a live-inject surface (SessionStart pins / PostToolUse recall)."""
    from portaw.memory.hookwire import enable_inject

    names = ["session", "tool"] if surface == "all" else [surface]
    for name in names:
        try:
            changed, backup = enable_inject(name, host)  # type: ignore[arg-type]
        except ValueError as e:
            raise click.ClickException(str(e))
        if changed:
            b = f" (backup {backup.name})" if backup else ""
            click.echo(f"inject '{name}' enabled on {host}{b} — takes effect next session")
        else:
            click.echo(f"inject '{name}' already wired on {host}")


@memory.command("inject-disable")
@click.argument("surface", type=click.Choice(["session", "tool", "all"]))
@click.option("--host", default="claude-code")
def memory_inject_disable(surface: str, host: str):
    """Remove a live-inject surface."""
    from portaw.memory.hookwire import disable_inject

    names = ["session", "tool"] if surface == "all" else [surface]
    for name in names:
        try:
            removed = disable_inject(name, host)  # type: ignore[arg-type]
        except ValueError as e:
            raise click.ClickException(str(e))
        click.echo(f"inject '{name}' {'disabled' if removed else 'was not wired'} on {host}")


@memory.command("consolidate")
@click.option("--dry-run", is_flag=True, help="Show what would change without writing.")
def memory_consolidate(dry_run: bool):
    """Async 'dream' pass: merge dups, promote, archive stale lessons."""
    from portaw.memory.consolidate import consolidate
    from portaw.memory.store import append_archive, load_lessons, save_lessons

    before = load_lessons()
    res = consolidate(before)
    click.echo(
        f"lessons {len(before)} → kept {len(res.kept)} · "
        f"merged {res.merged_count} · promoted {res.promoted_count} · "
        f"archived {len(res.archived)}"
    )
    if dry_run:
        click.echo("(dry-run — nothing written)")
        return
    # archive FIRST: if the process dies between the two writes, the worst case is
    # a duplicate in the archive — the reverse order would lose the archived
    # lessons forever (already dropped from the store, never written to archive).
    append_archive(res.archived)
    save_lessons(res.kept)
    click.echo("consolidated.")


@memory.command("init")
@click.option("--confirm", is_flag=True, help="Write harvested entries (gate-required).")
@click.option("--adr-dir", default=None, help="ADR dir (default: docs/adr).")
def memory_init(confirm: bool, adr_dir: str | None):
    """Seed project-memory: harvest docs/adr/* (v1). Preview unless --confirm."""
    from portaw.memory.gate import accepts
    from portaw.memory.seed import default_adr_dir, harvest_adrs
    from portaw.memory.store import load_project, save_project, upsert
    from datetime import date

    d = adr_dir or default_adr_dir()
    harvested = harvest_adrs(d)
    if not harvested:
        click.echo(f"no ADRs found under {d} — nothing to harvest")
        return
    click.echo(f"harvested {len(harvested)} ADR(s) from {d}:")
    for e in harvested:
        click.echo(f"  • {e.body[:80]}")
    if not confirm:
        click.echo("\n(preview — re-run with --confirm to write project-memory)")
        return
    today = date.today().isoformat()
    entries = load_project()
    for e in harvested:
        if accepts(e, confirmed=True).ok:  # --confirm satisfies the project gate
            entries = upsert(entries, e, last_seen=today)
    save_project(entries)
    click.echo(f"wrote {len(harvested)} entries to project-memory.")


@memory.command("harvest")
@click.option("--file", "src", default=None,
              help="mistakes-index.md (default: ~/.claude/rules/mistakes-index.md).")
@click.option("--project", "project_id", default="curated",
              help="Project id for project-scoped mistakes (no stack/env hint).")
@click.option("--confirm", is_flag=True, help="Write harvested lessons to the global store.")
def memory_harvest(src: str | None, project_id: str, confirm: bool):
    """Harvest a curated mistakes-index.md into global lessons (idempotent re-key by id)."""
    from dataclasses import replace

    from portaw.memory.harvest import default_mistakes_file, harvest_mistakes_file
    from portaw.memory.store import load_lessons, save_lessons

    path = src or default_mistakes_file()
    harvested = harvest_mistakes_file(path, project_id=project_id)
    if not harvested:
        click.echo(f"no mistakes parsed from {path} — nothing to harvest")
        return
    click.echo(f"parsed {len(harvested)} lesson(s) from {path}:")
    for e in harvested:
        click.echo(f"  • [{e.applicability:<16}] ×{e.recurrence:<3} c={e.confidence:.2f} {e.body[:60]}")
    if not confirm:
        click.echo("\n(preview — re-run with --confirm to write global lessons)")
        return
    # Index is authoritative → re-key by id so a re-harvest is idempotent (no recurrence
    # inflation). Keep the larger recurrence + any store-side pin (live state the index
    # doesn't know about). A REWORDED index line changes the content-hash id — match the
    # stale twin by its mistake-id (trigger_terms[0]) and replace it, don't duplicate.
    by_id = {e.id: e for e in load_lessons()}
    added = updated = replaced = 0
    for e in harvested:
        mid = e.trigger_terms[0] if e.trigger_terms else ""
        prev = by_id.get(e.id)
        if prev is None:
            stale = next(
                (x for x in by_id.values()
                 if x.type == "lesson" and x.trigger_terms[:1] == (mid,)),
                None,
            ) if mid else None
            if stale is not None:
                del by_id[stale.id]
                prev, replaced = stale, replaced + 1
            else:
                added += 1
        else:
            updated += 1
        if prev is not None:
            e = replace(e, recurrence=max(e.recurrence, prev.recurrence),
                        pinned=e.pinned or prev.pinned)
        by_id[e.id] = e
    save_lessons(list(by_id.values()))
    click.echo(f"\nwrote {added} new + {updated} updated"
               + (f" + {replaced} reworded" if replaced else "")
               + " lesson(s) to the global store.")


if __name__ == "__main__":
    cli()
