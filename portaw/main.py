"""portaw CLI entrypoint (v0.3 shell).

Command surface matches port-a-whip-spec.md §8. Bodies are Phase-1 stubs —
real impl wires to sets/ (loader, patcher, shim), kernel/ (ranking, registry),
adapters/ (per-host inject). See CLAUDE.md target tree.
"""

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


if __name__ == "__main__":
    cli()
