import argparse
import os
from pastel import Pastel
import sys
from typing import IO, Iterable, List, Optional, Sequence, Union
from .exceptions import PoeException
from .__version__ import __version__


def guess_ansi_support(file):
    return (
        (sys.platform != "win32" or "ANSICON" in os.environ)
        and hasattr(file, "isatty")
        and file.isatty()
    )


STDOUT_ANSI_SUPPORT = guess_ansi_support(sys.stdout)


class PoeUi:
    args: argparse.Namespace
    _color: Pastel

    def __init__(self, output: IO):  # TODO: make IO wrapper
        self.output = output
        self._init_colors()

    def _init_colors(self):
        self._color = Pastel(guess_ansi_support(self.output))
        self._color.add_style("u", "default", options="underline")
        self._color.add_style("hl", "light_gray")
        self._color.add_style("em", "cyan")
        self._color.add_style("em2", "cyan", options="italic")
        self._color.add_style("dem", "black", options="dark")
        self._color.add_style("h2", "default", options="bold")
        self._color.add_style("h2-dim", "default", options="dark")
        self._color.add_style("stripe", bg="blue")
        self._color.add_style("error", "light_red", options="bold")

    def __getitem__(self, key: str):
        """Provide easy access to arguments"""
        return getattr(self.args, key, None)

    def parse_args(self, cli_args: Sequence[str]):
        self.parser = argparse.ArgumentParser(
            prog="poe",
            description="Poe the Poet: A task runner that works well with poetry.",
            add_help=False,
            allow_abbrev=False,
        )

        self.parser.add_argument(
            "-h",
            "--help",
            dest="help",
            action="store_true",
            default=False,
            help="Show this help page and exit",
        )

        self.parser.add_argument(
            "--version",
            dest="version",
            action="store_true",
            default=False,
            help="Print the version and exit",
        )

        verbosity_group = self.parser.add_mutually_exclusive_group()
        verbosity_group.add_argument(
            "-v",
            "--verbose",
            dest="verbosity",
            action="store_const",
            metavar="verbose_mode",
            default=0,
            const=1,
            help="More console spam",
        )
        verbosity_group.add_argument(
            "-q",
            "--quiet",
            dest="verbosity",
            action="store_const",
            metavar="quiet_mode",
            const=-1,
            help="Less console spam",
        )

        self.parser.add_argument(
            "-d",
            "--dry-run",
            dest="dry_run",
            action="store_true",
            default=False,
            help="Print the task contents but don't actaully run it",
        )

        self.parser.add_argument(
            "--root",
            dest="project_root",
            metavar="PATH",
            type=str,
            default=None,
            help="Specify where to find the pyproject.toml",
        )

        ansi_group = self.parser.add_mutually_exclusive_group()
        ansi_group.add_argument(
            "--ansi",
            dest="ansi",
            action="store_true",
            default=STDOUT_ANSI_SUPPORT,
            help="Force enable ANSI output",
        )
        ansi_group.add_argument(
            "--no-ansi",
            dest="ansi",
            action="store_false",
            default=STDOUT_ANSI_SUPPORT,
            help="Force disable ANSI output",
        )

        self.parser.add_argument("task", default=tuple(), nargs=argparse.REMAINDER)
        self.args = self.parser.parse_args(cli_args)
        self._color.with_colors(self.args.ansi)

    def print_help(
        self,
        tasks: Iterable[str] = tuple(),
        info: Optional[str] = None,
        error: Optional[PoeException] = None,
    ):
        # TODO: See if this can be done nicely with a custom HelpFormatter

        # Ignore verbosity mode if help flag is set
        verbosity = 0 if self["help"] else self["verbosity"]

        result: List[Union[str, Sequence[str]]] = []
        if verbosity >= 0:
            result.append(
                (
                    "Poe the Poet - A task runner that works well with poetry.",
                    f"version <em>{__version__}</em>",
                )
            )

        if info:
            result.append(f"{f'<em2>Result: {info}</em2>'}")

        if error:
            # TODO: send this to stderr instead?
            result.append([f"<error>Error: {error.msg} </error>"])
            if error.cause:
                result[-1].append(f"<error> From: {error.cause} </error>")  # type: ignore

        if verbosity >= 0:
            # Use argparse for usage summary
            result.append(
                (
                    "<h2>USAGE</h2>",
                    "  <u>poe</u> [-h] [-v | -q] [--root PATH] [--ansi | --no-ansi] task [task arguments]",
                )
            )

            # Use argparse for optional args
            formatter = self.parser.formatter_class(prog=self.parser.prog)
            action_group = self.parser._action_groups[1]
            formatter.start_section(action_group.title)
            formatter.add_arguments(action_group._group_actions)
            formatter.end_section()
            result.append(
                ("<h2>GLOBAL OPTIONS</h2>", *formatter.format_help().split("\n")[1:])
            )

            if tasks:
                tasks_section = ["<h2>CONFIGURED TASKS</h2>"]
                for task in tasks:
                    if task.startswith("_"):
                        continue
                    tasks_section.append(f"  <em>{task}</em>")
                result.append(tasks_section)
            else:
                result.append("<h2-dim>NO TASKS CONFIGURED</h2-dim>")

        self.output.write(
            self._color.colorize(
                "\n\n".join(
                    section
                    if isinstance(section, str)
                    else "\n".join(section).strip("\n")
                    for section in result
                )
                + f"\n"
                + ("\n" if verbosity >= 0 else "")
            )
        )

    def print_msg(self, message: str, verbosity=0, end="\n"):
        if verbosity <= self["verbosity"]:
            self.output.write(self._color.colorize(message) + end)
            self.output.flush()

    def print_version(self):
        if self["verbosity"] >= 0:
            result = f"Poe the poet - version: <em>{__version__}</em>\n"
        else:
            result = f"{__version__}\n"
        self.output.write(self._color.colorize(result))
