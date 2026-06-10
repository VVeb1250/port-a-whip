"""portaw CLI entrypoint (v0.3 shell).

Command surface matches port-a-whip-spec.md §8. Bodies are Phase-1 stubs —
real impl wires to sets/ (loader, patcher, shim), kernel/ (ranking, registry),
adapters/ (per-host inject). See CLAUDE.md target tree.
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
def verify(set_name: str):
    """§10 health-check: is each tool in the set actually reachable on PATH?"""
    from portaw.sets.healthcheck import check_set
    from portaw.sets.loader import SetsError

    try:
        h = check_set(set_name)
    except SetsError as e:
        raise click.ClickException(str(e))
    mark = {"ok": "✓", "missing": "✗", "config-only": "·"}
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
def memory_recall(prompt: tuple[str, ...], symbols: tuple[str, ...], paths: tuple[str, ...]):
    """Dry-run retrieval: what memory would inject for a prompt (+ optional edit-target)."""
    from portaw.memory.anchors import AnchorQuery
    from portaw.memory.inject import format_memory, select
    from portaw.memory.retrieval import recall
    from portaw.memory.store import load_lessons, load_project

    entries = load_lessons() + load_project()
    if not entries:
        click.echo("(no memory yet — add some with `portaw memory add`)")
        return
    q = AnchorQuery(symbols=tuple(symbols), paths=tuple(paths))
    scored = recall(" ".join(prompt), entries, query=q)
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
        click.echo(f"  {pin} [{e.type:<7}] {e.applicability:<16} ×{e.recurrence:<3} {e.body[:70]}")


@memory.command("add")
@click.argument("body", nargs=-1, required=True)
@click.option("--type", "etype", type=click.Choice(["lesson", "project"]), default="lesson")
@click.option("--scope", type=click.Choice(["global", "project"]), default=None,
              help="Default: global for lessons, project for project-memory.")
@click.option("--applicability", default="universal", help="universal | stack:<x> | project:<id>.")
@click.option("--trigger", "triggers", multiple=True, help="Router trigger term(s).")
@click.option("--symbol", "symbols", multiple=True, help="Anchor symbol(s).")
@click.option("--path", "paths", multiple=True, help="Anchor path(s).")
@click.option("--pin", is_flag=True, help="Always-on tier (highest-ROI universal only).")
def memory_add(body, etype, scope, applicability, triggers, symbols, paths, pin):
    """Add a memory entry (compressed one-liner body)."""
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

    scope = scope or ("global" if etype == "lesson" else "project")
    entry = MemoryEntry.new(
        etype, " ".join(body), scope,
        applicability=applicability if etype == "lesson" else f"project:{scope}",
        trigger_terms=tuple(triggers),
        anchors=Anchors(symbols=tuple(symbols), paths=tuple(paths)),
        source="user", last_seen=date.today().isoformat(),
    )
    today = date.today().isoformat()
    if etype == "lesson":
        save_lessons(upsert(load_lessons(), entry, last_seen=today))
    else:
        save_project(upsert(load_project(), entry, last_seen=today))
    click.echo(f"added [{etype}] {entry.id}: {entry.body[:60]}")


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
    save_lessons(res.kept)
    append_archive(res.archived)
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


if __name__ == "__main__":
    cli()
