#!/bin/env python3

import argparse
import fileinput
import itertools
import sys

from argparse import ArgumentParser, Namespace
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Iterator, NamedTuple, Optional, Sequence
from typing_extensions import Never, TypeAlias

HELP = """
split_patch.py - split a git diff into multiple parts

TODO:

* tests!

(Supposedly done)
* git rm
* git mv, matching
* git mv, non-matching

"""

Chunk: TypeAlias = list[str]


def run(argv=None):
    args = _parse_args(argv)
    _check(args)
    _setup_directory(args.directory, args.clear)

    lines = fileinput.input(args.files)
    for file_deltas in FileDeltas.read(lines, args.parts, args.chunks):
        file_deltas.write(args.join_character)

    if args.remove:
        for f in args.files:
            f.unlink()


def _check(args: Namespace) -> None:
    if args.chunks and args.parts:
        sys.exit("Only one of --chunks and --parts may be set")

    if args.remove and not args.files:
        sys.exit("--remove requires some file arguments")

    if sys.stdin.isatty() and not args.files:
        sys.exit("No input")


class FileDelta:
    def __init__(self, head: Chunk, *deltas: Chunk) -> None:
        assert all(deltas)
        assert all(isinstance(i, list) for i in deltas)
        assert len(head) in (4, 5), head
        diff, command, *_ = head
        diff, git, a, b = diff.split()
        assert diff == "diff" and git == "--git", head

        command = command.split()[0]
        assert command in ("new", "deleted", "index", "similarity")

        none, _a, self.filename = a.partition("a/")
        none_b, _b, filename_b = b.partition("b/")
        assert _a and _b and not none and not none_b and self.filename and filename_b
        assert (not deltas) == (command == 'similarity')

        self.is_splittable = command == "index"
        self.head, self.deltas = head, deltas

    def split(self, parts: int, chunks: int) -> "FileDeltas":
        cut = chunks or parts or round(len(self.deltas) ** 0.5) or 1

        div, mod = divmod(len(self.deltas), cut)
        div += bool(mod)
        count, step = (div, cut) if chunks else (cut, div)

        pieces = [self.deltas[step * i: step * (i + 1)] for i in range(count)]
        # print(pieces)
        return FileDeltas([self.head, *p] for p in pieces)


class FileDeltas(list[FileDelta]):
    def __init__(self, chunks: Iterable[Sequence[Chunk]]) -> None:
        return super().__init__(FileDelta(*c) for c in chunks)

    @staticmethod
    def chunk(lines: Iterable[str]) -> "FileDeltas":
        def chunk(it: Iterable[str], prefix: str) -> list[list[str]]:
            """Split a iteration of lines every time a line starts with `prefix`.

            The result is a list of Chunks, where in each Chunk except perhaps the first
            one, the first line starts with `prefix`.
            """
            result: list[list[str]] = []
            for line in it:
                if not result or result[-1] and line.startswith(prefix):
                    result.append([])
                result[-1].append(line)
            return result

        return FileDeltas(chunk(fl, "@@") for fl in chunk(lines, "diff"))

    @staticmethod
    def read(lines: Iterable[str], parts: int, chunks: int) -> list["FileDeltas"]:
        return [c.split(parts, chunks) for c in FileDeltas.chunk(lines)]

    def write(self, join_character: str) -> None:
        filename = self[0].filename
        for c in "/:~":
            filename = filename.replace(c, join_character)

        for i, p in enumerate(self):
            index = f"-{i + 1}" if len(self) > 1 else ""
            file = directory / f"{filename}{index}.patch"
            print("Writing", file, file=sys.stderr)
            file.write_text("".join(j for i in p for j in i))


def _parse_args(argv) -> Namespace:
    parser = _ArgumentParser()

    help = "A list of files to split (none means split stdin)"
    parser.add_argument("files", nargs="*", help=help)

    help = "Split, containing this many deltas"
    parser.add_argument("--chunks", "-c", default=0, type=int, help=help)

    help = "Clean --directory of patch files"
    parser.add_argument("--clean", action="store_true", help=help)

    help = "Output to this directory (create if necessary)"
    parser.add_argument("--directory", "-d", type=Path, default=Path(), help=help)

    help = "The character to replace / in filenames"
    parser.add_argument("--join-character", "-j", type=str, default="-", help=help)

    help = "Split into this many parts"
    parser.add_argument("--parts", "-p", default=0, type=int, help=help)

    help = "Remove original patch files at the end"
    parser.add_argument("--remove", action="store_true", help=help)

    return parser.parse_args(argv)


def _setup_directory(directory: Path, clear: bool) -> None:
    if not directory.exists():
        print(f"Creating {directory}/")
        directory.mkdir(parents=True, exist_ok=True)

    elif clear:
        for i in directory.iterdir():
            if i.suffix == ".patch":
                i.unlink()


class _ArgumentParser(ArgumentParser):
    def __init__(
        self,
        prog: Optional[str] = None,
        usage: Optional[str] = None,
        description: Optional[str] = None,
        epilog: Optional[str] = None,
        is_fixer: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(prog, usage, description, None, **kwargs)
        self._epilog = epilog

    def exit(self, status: int = 0, message: Optional[str] = None) -> Never:
        argv = sys.argv[1:]
        if self._epilog and not status and "-h" in argv or "--help" in argv:
            print(self._epilog)
        super().exit(status, message)


if __name__ == "__main__":
    run()
