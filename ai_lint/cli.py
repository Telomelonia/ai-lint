"""Click CLI for ai-lint."""

import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import click

from ai_lint.checker import (
    ClaudeNotFoundError,
    check_claude_installed,
    count_verdicts,
    extract_insights,
    format_insights,
    format_report_markdown,
    format_verdicts,
    run_check,
)
from ai_lint.config import (
    PERSONAS,
    install_policy,
    open_policy_in_editor,
    policy_exists,
    read_policy,
)
from ai_lint.sessions import (
    discover_sessions,
    format_transcript,
    parse_session,
)
from ai_lint.setup_hook import install_hook, is_hook_installed
from ai_lint.spinner import Spinner


@click.group()
@click.version_option(package_name="ai-lint")
def cli():
    """ai-lint: Check AI coding sessions against your own rules."""


@cli.command()
def init():
    """Setup wizard: choose persona, create policy, install hook."""
    click.echo("Welcome to ai-lint!\n")

    # 1. Check claude CLI
    if check_claude_installed():
        click.echo("[ok] claude CLI found")
    else:
        click.echo("[!!] claude CLI not found")
        click.echo("     Install it: curl -fsSL https://claude.ai/install.sh | bash")
        click.echo("     ai-lint needs claude CLI to analyze sessions.\n")

    # 2. Choose persona
    click.echo("Who are you?\n")
    click.echo("  1. self — Individual developer checking your own habits")
    click.echo("  2. team — Team lead/manager enforcing guidelines")
    click.echo()

    choice = click.prompt(
        "Choose a persona",
        type=click.Choice(["1", "2", "self", "team"]),
    )
    persona_map = {"1": "self", "2": "team"}
    persona = persona_map.get(choice, choice)

    # 3. Install policy
    if policy_exists():
        overwrite = click.confirm("Policy already exists. Overwrite?", default=False)
        if not overwrite:
            click.echo("Keeping existing policy.")
        else:
            install_policy(persona)
            click.echo(f"Installed '{persona}' policy to ~/.ai-lint/policy.md")
    else:
        install_policy(persona)
        click.echo(f"Installed '{persona}' policy to ~/.ai-lint/policy.md")

    # 4. Offer to install hook
    if is_hook_installed():
        click.echo("[ok] SessionEnd hook already installed")
    else:
        if click.confirm("\nInstall a SessionEnd hook to auto-check after each session?", default=True):
            install_hook()
        else:
            click.echo("Skipped hook installation. You can add it later with 'ai-lint hook --install'.")

    click.echo("\nDone! Run 'ai-lint check' to check a session, or 'ai-lint policy' to edit your rules.")


@cli.command()
@click.option("--last", is_flag=True, help="Check the most recent session without prompting.")
@click.option("--quiet", is_flag=True, help="Minimal output (for hook usage).")
@click.option("--no-insights", is_flag=True, help="Skip session insights.")
def check(last, quiet, no_insights):
    """Pick a session and check it against your policy."""
    if not policy_exists():
        click.echo("No policy found. Run 'ai-lint init' first.")
        sys.exit(1)

    sessions = discover_sessions()
    if not sessions:
        click.echo("No sessions found in ~/.claude/projects/")
        sys.exit(1)

    if last:
        selected = sessions[0]  # already sorted most recent first
    else:
        # Parse just enough to build labels
        for s in sessions[:20]:
            parse_session(s, max_messages=3)

        click.echo("Recent sessions:\n")
        display = sessions[:20]
        for i, s in enumerate(display, 1):
            click.echo(f"  {i:>2}. {s.label}")
        click.echo()

        idx = click.prompt("Choose a session", type=click.IntRange(1, len(display)))
        selected = display[idx - 1]

    # Full parse
    if not quiet:
        click.echo(f"Parsing session {selected.session_id[:8]}...")
    parse_session(selected)

    if not selected.messages:
        click.echo("Session has no messages.")
        sys.exit(0)

    transcript = format_transcript(selected)
    policy = read_policy()

    if not quiet:
        click.echo(f"Checking {len(selected.messages)} messages against policy...")

    skip_insights = quiet or no_insights

    try:
        with Spinner("Analyzing with claude..."):
            if skip_insights:
                result = run_check(transcript, policy)
                insights = None
            else:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    verdict_future = pool.submit(run_check, transcript, policy)
                    insight_future = pool.submit(extract_insights, transcript, policy)
                    result = verdict_future.result()
                    try:
                        insights = insight_future.result()
                    except Exception:
                        insights = None
    except (ClaudeNotFoundError, RuntimeError) as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    output = format_verdicts(result)
    click.echo(output)

    if insights:
        click.echo(format_insights(insights))


@cli.command()
@click.option("-n", "--count", default=5, help="Number of recent sessions to check.")
@click.option("-o", "--output", "outfile", type=click.Path(), default=None, help="Export markdown report to file.")
def report(count, outfile):
    """Check multiple recent sessions and generate a report."""
    if not policy_exists():
        click.echo("No policy found. Run 'ai-lint init' first.")
        sys.exit(1)

    sessions = discover_sessions()
    if not sessions:
        click.echo("No sessions found in ~/.claude/projects/")
        sys.exit(1)

    to_check = sessions[:count]
    policy = read_policy()
    session_results = []

    for i, s in enumerate(to_check, 1):
        parse_session(s)
        if not s.messages:
            continue
        transcript = format_transcript(s)
        try:
            with Spinner(f"[{i}/{len(to_check)}] Checking {s.label}..."):
                result = run_check(transcript, policy)
        except (ClaudeNotFoundError, RuntimeError) as e:
            click.echo(f"  Error: {e}", err=True)
            continue
        session_results.append({"session_label": s.label, "result": result})

        # Show inline summary
        counts = count_verdicts(result.get("verdicts", []))
        click.echo(f"  -> {counts['pass']} passed, {counts['fail']} failed")

    if not session_results:
        click.echo("No sessions had messages to check.")
        sys.exit(0)

    # Terminal summary
    click.echo(f"\nChecked {len(session_results)} sessions.")
    total_fail = sum(
        count_verdicts(r["result"].get("verdicts", []))["fail"]
        for r in session_results
    )
    if total_fail == 0:
        click.echo("All clear — no policy violations found.")
    else:
        click.echo(f"Found {total_fail} total violation(s) across sessions.")

    # Export markdown
    md = format_report_markdown(session_results)
    if outfile:
        Path(outfile).write_text(md)
        click.echo(f"\nReport saved to {outfile}")
    else:
        default_name = f"ai-lint-report-{datetime.now().strftime('%Y%m%d-%H%M%S')}.md"
        Path(default_name).write_text(md)
        click.echo(f"\nReport saved to {default_name}")


@cli.command()
def policy():
    """Open your policy file in your default editor."""
    if not policy_exists():
        click.echo("No policy found. Run 'ai-lint init' first.")
        sys.exit(1)
    open_policy_in_editor()


@cli.group()
def hook():
    """Manage the SessionEnd hook."""


@hook.command("install")
def hook_install():
    """Install the SessionEnd hook in ~/.claude/settings.json."""
    install_hook()


@hook.command("uninstall")
def hook_uninstall():
    """Remove the SessionEnd hook."""
    from ai_lint.setup_hook import uninstall_hook
    uninstall_hook()


def main():
    cli()


if __name__ == "__main__":
    main()
