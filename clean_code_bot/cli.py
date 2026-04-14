"""Click CLI entrypoint."""

from __future__ import annotations

import sys
from pathlib import Path

import click

from clean_code_bot import __version__
from clean_code_bot.pipeline import refactor_source


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="clean-code-bot")
def main() -> None:
    """Automated refactorer: SOLID-oriented cleanup + documentation via an LLM."""


@main.command("refactor")
@click.argument(
    "input_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=False,
)
@click.option(
    "-o",
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write result to this file instead of stdout.",
)
@click.option(
    "--temperature",
    type=float,
    default=0.2,
    show_default=True,
    help="Sampling temperature for the model.",
)
@click.option(
    "--stdin",
    "from_stdin",
    is_flag=True,
    help="Read source from stdin (ignore INPUT_PATH).",
)
def refactor_command(
    input_path: Path | None,
    output_path: Path | None,
    temperature: float,
    from_stdin: bool,
) -> None:
    """Refactor a source file and print or save the optimized version."""
    if from_stdin:
        source = sys.stdin.read()
        path_for_hint: Path | None = None
    else:
        if input_path is None:
            raise click.UsageError("Provide INPUT_PATH or use --stdin.")
        source = input_path.read_text(encoding="utf-8")
        path_for_hint = input_path

    try:
        result = refactor_source(source, path=path_for_hint, temperature=temperature)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001 — surface provider errors clearly
        raise click.ClickException(str(exc)) from exc

    if output_path is not None:
        output_path.write_text(result + ("\n" if not result.endswith("\n") else ""), encoding="utf-8")
        click.echo(f"Wrote {output_path}", err=True)
    else:
        click.echo(result)


if __name__ == "__main__":
    main()
