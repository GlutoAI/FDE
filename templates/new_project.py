"""Create a new agentic project from templates/agentic-project/ in seconds.

Copies the template, replaces its four placeholder names, creates a protected .env from
.env.example, and prints the next steps. Standard library only; it makes no network call.

    python3 templates/new_project.py expense-review-copilot --prefix EXPENSE --cli expense \
        --purpose "Helps a small-business owner review expenses before month-end close."
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

TEMPLATE_DIRECTORY = Path(__file__).resolve().parent / "agentic-project"
WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
PURPOSE_LINE = re.compile(r"^PURPOSE: .*$", re.MULTILINE)
IGNORED_NAMES = (
    ".venv",
    ".tools",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".DS_Store",
    ".env",
)
NAME_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
PREFIX_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*[A-Z0-9]$")


def run_new_project(arguments: list[str] | None = None) -> int:
    """Parse options, create the project, and print what to do next.

    Args:
        arguments: Command-line arguments; defaults to ``sys.argv[1:]``.

    Returns:
        Zero on success; one when an option is invalid or the destination exists.
    """
    options = _parse_arguments(arguments)
    try:
        replacements = _build_replacements(options)
        destination = (options.destination or WORKSPACE_ROOT) / options.name
        if destination.exists():
            raise ValueError(f"{destination} already exists; choose another name")
        _copy_template(destination)
        changed = _apply_replacements(destination, replacements, options.purpose)
        _create_env_file(destination)
        _mark_format_pending(destination)
    except ValueError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    _print_next_steps(destination, options, changed)
    return 0


def _parse_arguments(arguments: list[str] | None) -> argparse.Namespace:
    """Read the project name and the optional names derived from it."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("name", help="Project directory, kebab-case, e.g. expense-review-copilot")
    parser.add_argument("--prefix", help="Environment prefix without '_'; default: first word")
    parser.add_argument("--cli", help="Command name; default: the prefix in lowercase")
    parser.add_argument("--title", help="Display title; default: the name in title case")
    parser.add_argument("--purpose", help="One sentence for the README's first line")
    parser.add_argument("--destination", type=Path, help="Parent directory; default: workspace")
    return parser.parse_args(arguments)


def _build_replacements(options: argparse.Namespace) -> list[tuple[str, str]]:
    """Validate the names and return the placeholder replacements, longest first."""
    if not NAME_PATTERN.match(options.name):
        raise ValueError("name must be kebab-case, e.g. expense-review-copilot")
    prefix = (options.prefix or options.name.split("-")[0]).upper().rstrip("_")
    if not PREFIX_PATTERN.match(prefix) or prefix == "TEMPLATE":
        raise ValueError("prefix must be UPPER_SNAKE, e.g. EXPENSE, and not TEMPLATE")
    cli = options.cli or prefix.lower().replace("_", "-")
    if not NAME_PATTERN.match(cli):
        raise ValueError("cli must be kebab-case, e.g. expense")
    title = options.title or " ".join(word.capitalize() for word in options.name.split("-"))
    return [
        ("agentic-project-template", options.name),
        ("Agentic Project Template", title),
        ("TEMPLATE_", f"{prefix}_"),
        ("template-cli", cli),
    ]


def _copy_template(destination: Path) -> None:
    """Copy the template without environments, builds, caches, or secrets."""
    if not TEMPLATE_DIRECTORY.is_dir():
        raise ValueError(f"template not found at {TEMPLATE_DIRECTORY}")
    shutil.copytree(
        TEMPLATE_DIRECTORY, destination, ignore=shutil.ignore_patterns(*IGNORED_NAMES)
    )
    shutil.rmtree(destination / "backend" / "data", ignore_errors=True)


def _apply_replacements(
    destination: Path, replacements: list[tuple[str, str]], purpose: str | None
) -> int:
    """Replace placeholders in every text file; return how many files changed."""
    changed = 0
    for path in sorted(destination.rglob("*")):
        if not path.is_file():
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        text = original
        for placeholder, value in replacements:
            text = text.replace(placeholder, value)
        if purpose and path == destination / "README.md":
            text = PURPOSE_LINE.sub(purpose.strip(), text, count=1)
        if text != original:
            path.write_text(text, encoding="utf-8")
            changed += 1
    return changed


def _create_env_file(destination: Path) -> None:
    """Create .env from .env.example with owner-only permissions; keys stay empty."""
    env_file = destination / ".env"
    shutil.copyfile(destination / ".env.example", env_file)
    env_file.chmod(0o600)


def _mark_format_pending(destination: Path) -> None:
    """Ask the first ``scripts/check.sh`` run to format once; new names change line lengths."""
    (destination / "backend" / ".format-pending").write_text("")


def _print_next_steps(destination: Path, options: argparse.Namespace, changed: int) -> None:
    """Print where the project is and the commands that make it verified."""
    print(f"created {destination} ({changed} files adapted; .env created with mode 600)")
    print("next:")
    print(f"  cd {destination}")
    print("  ./scripts/check.sh            # offline gate, about a minute")
    print("  ./scripts/check.sh --docker   # plus the Compose stack")
    if not options.purpose:
        print("  edit the PURPOSE line at the top of README.md")
    print("  replace the example record and tool when the first real CSV is described")
    print("  record the observed results in README.md under Verification")


if __name__ == "__main__":
    raise SystemExit(run_new_project())
