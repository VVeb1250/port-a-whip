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
        raise click.ClickException(str(e)) from e
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
        raise click.ClickException(str(e)) from e
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
    import platform

    click.echo(f"\n{header}:")
    for st in steps:
        flag = " [vendor]" if st.runs_vendor_code else ""
        if not st.cmd:
            click.echo(f"  • [{st.tool}] {st.label}{flag}\n"
                       f"      (no install command for {platform.system()} — see the set's upstream docs)")
        else:
            click.echo(f"  • [{st.tool}] {st.label}{flag}\n      {st.cmd}")


def _run_shim(set_name: str, steps, cs, host: str, assume_yes: bool):
    """Execute a curated set's shim steps via argv (shell=False), after confirm.

    A non_mcp tool already on PATH is skipped (idempotent; avoids vendor
    'already installed' nonzero exits). MCP setup_shim steps (e.g. codegraph
    index) are NEVER PATH-skipped — the binary being present does not mean the
    build step ran. Steps needing a shell (pipe/chain) stay print-only."""
    from portaw.sets.healthcheck import check_set
    from portaw.sets.runner import needs_shell, run_shim_steps

    if cs.raw.get("untrusted"):  # community/unverified — never auto-run (§12)
        click.echo("\n⚠ set is untrusted — printing steps instead of running (hash/sig verify pending):")
        _print_shim(steps, "MANUAL STEPS")
        return

    healthy = {t.tool for t in check_set(set_name, host).tools if t.status == "ok"}
    pending = []
    for st in steps:
        if st.kind == "non_mcp" and st.tool in healthy:
            click.echo(f"  · skipped (already on PATH): {st.tool}")
        else:
            pending.append(st)
    if not pending:
        click.echo("\nall install steps already satisfied.")
        return

    import platform

    unavailable = [st for st in pending if not st.cmd]
    have_cmd = [st for st in pending if st.cmd]
    runnable = [st for st in have_cmd if not needs_shell(st.cmd)]
    manual = [st for st in have_cmd if needs_shell(st.cmd)]
    if unavailable:
        click.echo(f"\nNO COMMAND for {platform.system()} (install manually — see upstream docs):")
        for st in unavailable:
            click.echo(f"  • [{st.tool}] {st.label}")
    if manual:
        click.echo("\nMANUAL (needs a shell — pipe/chain/redirect/instruction; run yourself):")
        for st in manual:
            click.echo(f"  • [{st.tool}] {st.cmd}")
    if not runnable:
        click.echo(f"\nnothing paw can auto-run. verify with: portaw verify {set_name}")
        return

    click.echo("\nWILL RUN (argv exec, shell=False — no shell metachars interpreted):")
    for st in runnable:
        click.echo(f"  • [{st.tool}] {st.cmd}")
    if not assume_yes:
        click.confirm(f"\nRun {len(runnable)} install step(s) now?", abort=True)
    click.echo("")
    for r in run_shim_steps(runnable, curated=True):
        mark = "✓" if r.ok else "✗"
        tail = "" if r.ok else f" — {r.error}"
        click.echo(f"  {mark} [{r.tool}] {r.cmd}{tail}")
    click.echo(f"\nverify with: portaw verify {set_name}")


@cli.command()
@click.argument("set_name")
@click.option("--host", default=None, help="Target host (claude-code/codex/gemini).")
@click.option("--force", is_flag=True, help="Re-patch even if a server is already present.")
@click.option("--run", "do_run", is_flag=True,
              help="Execute the shim/install steps now (curated sets only; argv exec, no shell).")
@click.option("--yes", "-y", "assume_yes", is_flag=True, help="Skip the confirm prompt with --run.")
def install(set_name: str, host: str | None, force: bool, do_run: bool, assume_yes: bool):
    """Install a set: auto-patch MCP config (backup+validate), then run or print shim steps."""
    from portaw.sets.install import get_set, install_set
    from portaw.sets.loader import SetsError
    from portaw.sets.patcher import PatchError

    try:
        res = install_set(set_name, host, force=force)
    except (SetsError, PatchError, ValueError) as e:
        raise click.ClickException(str(e)) from e

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

    if res.shim_steps and do_run:
        _run_shim(res.set_name, res.shim_steps, get_set(set_name), res.host, assume_yes)
    else:
        _print_shim(res.shim_steps, "MANUAL STEPS")
        if res.shim_steps:
            click.echo("\n(re-run with --run to let paw execute these — curated set, argv exec no shell)")
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
        raise click.ClickException(str(e)) from e
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
        raise click.ClickException(str(e)) from e
    mark = {"ok": "✓", "missing": "✗", "config-only": "·", "alt": "↷"}
    for t in h.tools:
        click.echo(f"  {mark[t.status]} {t.tool} ({t.kind}): {t.status} — {t.detail}")
    click.echo(f"\ngate: {'PASS' if h.ok else 'FAIL — install missing tools'}")
    if not h.ok:
        raise SystemExit(1)


@cli.command()
@click.option("--usage", "show_usage", is_flag=True,
              help="Scan recent transcripts for MCP tool-call evidence — flags "
                   "servers paying idle def tokens with zero observed use.")
@click.option("--days", default=30, show_default=True,
              help="Usage scan window (with --usage).")
def doctor(show_usage: bool, days: int):
    """Env check + host detect + config parse-validity + paw-managed drift report."""
    import json as _json

    from portaw.config import host_config
    from portaw.sets import state as state_mod
    from portaw.sets.patcher import get_entry

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
            continue
        managed = state_mod.installed_sets(h)
        if managed:
            summary = ", ".join(
                f"{s} ({len(r.get('tools', {}))} mcp)" for s, r in sorted(managed.items()))
            click.echo(f"    paw-managed: {summary}")
            mark = {"orphaned": "✗", "drift": "≠", "unreadable": "?"}
            for tool, kind, detail in state_mod.check_drift(h, lambda t, _hc=hc: get_entry(_hc, t)):
                click.echo(f"    {mark.get(kind, '?')} {tool} [{kind}]: {detail}")
    try:
        from portaw.sets.loader import load_all

        click.echo(f"registry: {len(load_all())} curated sets loaded OK")
    except Exception as e:
        click.echo(f"registry: ERROR — {e}")
    if show_usage:
        from portaw.sets.usage import usage_report

        click.echo("")
        for line in usage_report(days=days):
            click.echo(line)


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
        raise click.ClickException(str(e)) from e
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
        raise click.ClickException(str(e)) from e
    d = diff(base, treat)
    click.echo(_json.dumps(d, indent=2) if as_json else format_report(d))


@bench.command("gain")
@click.argument("set_name")
@click.option("--host", default="claude-code", help="Host whose install date anchors the split.")
@click.option("--agent", default="claude", help="ccusage agent rows: claude/codex/gemini.")
def bench_gain(set_name: str, host: str, agent: str):
    """Auto-attribute token delta for a set using its install date as the A/B split.

    Directional only (uncontrolled windows) — for a defensible number run
    `bench ab` on an identical task. Inconclusive below 2 sessions a side."""
    from portaw.bench import CcusageError
    from portaw.sets.gain import format_report, gain_for_set

    try:
        rep = gain_for_set(set_name, host=host, agent=agent)  # type: ignore[arg-type]
    except CcusageError as e:
        raise click.ClickException(str(e)) from e
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    click.echo(format_report(rep))


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


@router.command("outcomes")
@click.option("--forget", "forget_name", default=None, metavar="NAME",
              help="Reset one capability's counters (un-demote it).")
def router_outcomes(forget_name: str | None):
    """Suggestion → conversion ledger: what the router emits vs what gets used.

    A set suggested ≥5 times that never converted is DEMOTED (stops surfacing)
    until its `portaw install` runs or you --forget it here."""
    from portaw.memory import outcomes

    if forget_name:
        if outcomes.forget(forget_name):
            click.echo(f"reset: {forget_name}")
        else:
            raise click.ClickException(f"no outcome record for {forget_name!r}")
        return
    records = outcomes.load()
    if not records:
        click.echo("(no outcomes yet — the router hook fills this live)")
        return
    demoted = outcomes.demoted_names()
    for n, r in sorted(records.items(), key=lambda kv: -kv[1].get("suggested", 0)):
        flag = "  ⛔ demoted" if n in demoted else ""
        click.echo(f"  {n:<22} suggested ×{r.get('suggested', 0):<4} "
                   f"used ×{r.get('used', 0):<3}{flag}")


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
        raise click.ClickException(str(e)) from e
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
        raise click.ClickException(str(e)) from e
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
        raise click.ClickException(str(e)) from e
    click.echo(f"host={st['host']} event={st['event']} wired={st['wired']} settings={st['settings']}")
    # Surface the silent demotion loop: a set the router stopped suggesting leaves
    # no trace in wiring state, so a confused "why isn't X surfacing?" has no answer
    # here. Name the demoted sets + how to undo (`router outcomes --forget`).
    try:
        from portaw.memory import outcomes

        demoted = sorted(outcomes.demoted_names())
        if demoted:
            click.echo(f"demoted (suggested ≥{outcomes.DEMOTE_MIN_SUGGESTED}, never used; "
                       f"`router outcomes --forget <name>` to reset): {', '.join(demoted)}")
    except Exception:
        pass


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
@click.option("--explain", is_flag=True,
              help="Report scoped lessons this context makes ineligible (silent-miss check).")
def memory_recall(prompt: tuple[str, ...], symbols: tuple[str, ...],
                  paths: tuple[str, ...], stacks: tuple[str, ...],
                  project_id: str | None, use_embed: bool, explain: bool):
    """Dry-run retrieval: what memory would inject for a prompt (+ optional edit-target)."""
    from pathlib import Path

    from portaw.memory.anchors import AnchorQuery
    from portaw.memory.context import host_context, scoped_drop_report
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
    if explain:
        report = scoped_drop_report(entries, ctx)
        if report:
            click.echo("scoped lessons ineligible in THIS context (not a ranking miss):", err=True)
            for line in report:
                click.echo(f"  ⚠ {line}", err=True)
        else:
            click.echo("no scoped lessons dropped by this context.", err=True)
        # which retrieval tier actually ran — absent this, a TF-IDF score is
        # indistinguishable from an embed cosine, so "did tier-2 fire?" is unanswerable.
        if embed_fn is not None:
            tier = "tier-1 TF-IDF + tier-2 MiniLM (tier-2 fires only on tier-1 misses)"
        elif use_embed:
            tier = "tier-1 TF-IDF only (tier-2 requested but model/libs unavailable)"
        else:
            tier = "tier-1 TF-IDF only — pass --embed for tier-2 MiniLM (paraphrase/cross-lingual)"
        click.echo(f"retrieval tier: {tier}", err=True)
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


@memory.command("health")
@click.option("--backfill", is_flag=True,
              help="Fill trigger_terms from each body for lessons missing them (backup first).")
def memory_health(backfill: bool):
    """Report metadata unevenness (recall = f(metadata)) and optionally backfill it."""
    import shutil
    import time

    from portaw.memory.health import backfill_trigger_terms, format_report, metadata_report
    from portaw.memory.store import global_dir, load_lessons, save_lessons

    lessons = load_lessons()
    click.echo(format_report(metadata_report(lessons)))
    if not backfill:
        return
    new, changed = backfill_trigger_terms(lessons)
    if not changed:
        click.echo("nothing to backfill.")
        return
    lf = global_dir() / "lessons.jsonl"
    bak = lf.with_name(f"lessons.jsonl.bak-{time.strftime('%Y%m%dT%H%M%S')}")
    shutil.copy2(lf, bak)
    save_lessons(new)
    click.echo(f"backfilled trigger_terms on {changed} lessons (backup {bak.name}).")


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
        edges = f" →{len(e.relations)}" if e.relations else ""
        click.echo(f"  {pin} {e.id} [{e.type:<7}] {e.applicability:<16} "
                   f"×{e.recurrence:<3} {e.body[:60]}{edges}")


@memory.command("link")
@click.argument("src_id")
@click.argument("rel", type=click.Choice(
    ["related", "caused_by", "superseded_by", "contradicts"]))
@click.argument("dst_id")
def memory_link(src_id: str, rel: str, dst_id: str):
    """Add a typed edge SRC --rel--> DST between two existing entries (R13).

    The manual half of the memoir layer: a human can assert the suppressive edges
    (superseded_by / contradicts) that auto-capture is forbidden to seed. Works
    across stores (a lesson can point at the project decision it violates) — DST
    only has to exist somewhere so recall can resolve it. Ids are short content
    hashes (see `memory list`); a unique prefix is accepted."""
    from portaw.memory.store import (
        load_lessons,
        load_project,
        save_lessons,
        save_project,
    )

    lessons, project = load_lessons(), load_project()

    def _resolve(frag: str) -> str | None:
        ids = [e.id for e in (*lessons, *project)]
        if frag in ids:
            return frag
        hits = [i for i in ids if i.startswith(frag)]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise click.ClickException(f"ambiguous id prefix {frag!r} ({len(hits)} matches)")
        return None

    src, dst = _resolve(src_id), _resolve(dst_id)
    if src is None:
        raise click.ClickException(f"no entry matches src id {src_id!r}")
    if dst is None:
        raise click.ClickException(f"no entry matches dst id {dst_id!r} (edge to a "
                                   "phantom id would be dead weight)")

    for entries, save in ((lessons, save_lessons), (project, save_project)):
        idx = next((k for k, e in enumerate(entries) if e.id == src), None)
        if idx is None:
            continue
        linked = entries[idx].with_relation(rel, dst)
        if linked is entries[idx]:
            click.echo(f"edge {rel} already present (or self/invalid) — nothing changed")
            return
        save([*entries[:idx], linked, *entries[idx + 1:]])
        click.echo(f"linked {src} --{rel}--> {dst}")
        return


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
    from pathlib import Path

    from portaw.memory.anchors import Anchors
    from portaw.memory.schema import MemoryEntry
    from portaw.memory.store import (
        load_lessons,
        load_project,
        save_lessons,
        save_project,
        upsert,
    )

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
        raise click.ClickException(str(e)) from e
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
        raise click.ClickException(str(e)) from e
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
        raise click.ClickException(str(e)) from e
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
    """SessionStart entrypoint: inject pinned lessons once per session. Never fails.

    Also the opportunistic consolidation trigger: session boundaries are the
    'between sessions' the dream pass is designed for, and this hook is the only
    paw code guaranteed to run there. Rate-limited by a marker file (~weekly)."""
    try:
        from portaw.adapters.memory_hooks import run_session_hook

        out = run_session_hook()
        if out:
            click.echo(out)
    except Exception:
        pass
    try:
        from portaw.memory.consolidate import maybe_consolidate

        maybe_consolidate()
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
            raise click.ClickException(str(e)) from e
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
            raise click.ClickException(str(e)) from e
        click.echo(f"inject '{name}' {'disabled' if removed else 'was not wired'} on {host}")


@memory.command("consolidate")
@click.option("--dry-run", is_flag=True, help="Show what would change without writing.")
@click.option("--every", "every", default=None, metavar="DAYS|session",
              help="Set the auto-dream cadence (N days, or 'session' = every session end) and exit.")
def memory_consolidate(dry_run: bool, every: str | None):
    """Async 'dream' pass: merge dups, promote, archive stale lessons."""
    from portaw.memory.consolidate import consolidate
    from portaw.memory.store import append_archive, load_lessons, save_lessons

    if every is not None:
        from portaw.memory.consolidate import set_dream_interval

        if every.lower() == "session":
            days = 0
        else:
            try:
                days = int(every)
            except ValueError:
                raise click.ClickException(
                    f"--every takes a day count or 'session', not {every!r}"
                ) from None
        set_dream_interval(days)
        label = "every session end" if days == 0 else f"every {days} day(s)"
        click.echo(f"dream cadence set: {label}")
        return

    before = load_lessons()
    try:
        from portaw.memory.similarity import supersede_pairs

        supersedes = supersede_pairs(before)
    except Exception:
        supersedes = []
    res = consolidate(before, supersedes=supersedes)
    click.echo(
        f"lessons {len(before)} → kept {len(res.kept)} · "
        f"merged {res.merged_count} · promoted {res.promoted_count} · "
        f"superseded {res.superseded_count} · archived {len(res.archived)}"
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
    from datetime import date

    from portaw.memory.gate import accepts
    from portaw.memory.seed import default_adr_dir, harvest_adrs
    from portaw.memory.store import load_project, save_project, upsert

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


@memory.command("sync")
@click.option("--init", "remote_url", default=None, metavar="REMOTE_URL",
              help="One-time setup: make ~/.paw/memory a git repo against this "
                   "remote (use a PRIVATE repo — lessons can reference your env).")
def memory_sync(remote_url: str | None):
    """Cross-host lesson sync (git-backed, no daemon).

    Content-hash ids make the merge conflict-free: the same mistake captured on
    two machines is the same id; counts fold field-wise (idempotent). Imported
    lessons arrive confidence-capped until they recur locally."""
    from portaw.memory.sync import SyncError, init_sync, sync

    try:
        if remote_url:
            click.echo(init_sync(remote_url))
            return
        res = sync()
        click.echo(f"sync: {res.message}")
        if not res.pushed:
            raise SystemExit(1)
    except SyncError as e:
        raise click.ClickException(str(e)) from e


@memory.command("harvest")
@click.option("--file", "src", default=None,
              help="mistakes-index.md (default: ~/.claude/rules/mistakes-index.md).")
@click.option("--project", "project_id", default=None,
              help="Project id for project-scoped mistakes. Omit → unclassified "
                   "lessons fall to universal (a placeholder would orphan them).")
@click.option("--confirm", is_flag=True, help="Write harvested lessons to the global store.")
def memory_harvest(src: str | None, project_id: str | None, confirm: bool):
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
