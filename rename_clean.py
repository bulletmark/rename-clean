"""
Utility to replace undesirable characters with underscores in Linux file names.
Undesirable characters are any that are not ASCII alphanumeric (`0-9`, `a-z`,
`A-Z`), underscore (`_`), hyphen (`-`), or dot (`.`). If characters are
replaced by underscores, then repeated underscores are also reduced to a single
underscore and trimmed from the name stem and suffix. A unique name is always
created by appending a number on the name stem if necessary.
"""

# Author: Mark Blakeney, Jul 2025.
from __future__ import annotations

import itertools
import re
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

from argparse_from_file import ArgumentParser, Namespace

PROG = Path(sys.argv[0]).stem


def run(cmd: Sequence[str]) -> tuple[str, str]:
    "Run given command and return (stdout, stderr) strings"
    import subprocess

    stdout = ''
    stderr = ''
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
    except Exception as e:
        stderr = str(e)
    else:
        if res.stdout:
            stdout = res.stdout.strip()
        if res.stderr:
            stderr = res.stderr.strip()

    return stdout, stderr


def make_new_name(args: Namespace, path: Path) -> Path | None:
    "Make a new path name by replacing characters"
    if not (pname := path.name):
        return None

    # Replace undesirable characters with an underscore.
    name = args._map.sub(args.character, pname)
    if name == pname and not args.more_aggressive:
        return None

    # Remove multiple underscores
    name = args._reduce.sub(args.character, name)

    # Remove leading and trailing underscores on stem and suffix
    newpath = Path(name)
    stem = newpath.stem.strip(args.character) or args.character
    if (suffix := newpath.suffix.strip(args.character)) == '.':
        suffix = ''

    # If the name is unchanged, return None
    if (name := (stem + suffix)) == pname:
        return None

    # Ensure a new name that does not already exist
    for n in itertools.count(2):
        newpath = path.with_name(name)
        if not newpath.exists():
            return newpath

        name = f'{stem}{args.character}{n}{suffix}'

    return None


def rename_paths(args: Namespace, paths: Iterable[Path], top: bool = True) -> None:
    "Rename files and directories for the given paths"
    for path in paths:
        if args.ignore_hidden and path.name.startswith('.'):
            continue

        if not (is_dir := path.is_dir()) and top and not path.exists():
            print(f'Path does not exist: {path}', file=sys.stderr)
            continue

        if newpath := make_new_name(args, path):
            if not args.quiet:
                add = '/' if is_dir else ''
                print(f'Renaming "{path}{add}" -> "{newpath}{add}"')

            if not args.dryrun:
                path.rename(newpath)
                path = newpath

        if is_dir and (
            top or (args.recurse and (not path.is_symlink() or args.recurse_symlinks))
        ):
            rename_paths(args, path.iterdir(), False)


def main() -> None:
    "Main code"
    # Process command line options
    opt = ArgumentParser(description=__doc__)
    opt.add_argument(
        '-r',
        '--recurse',
        action='store_true',
        help='recurse through all sub directories',
    )
    opt.add_argument(
        '-d',
        '--dryrun',
        action='store_true',
        help='do not rename, just show what would be done',
    )
    opt.add_argument('-q', '--quiet', action='store_true', help='do not report changes')
    opt.add_argument(
        '-i',
        '--ignore-hidden',
        action='store_true',
        help='ignore hidden files and directories (those starting with ".")',
    )
    opt.add_argument(
        '-s',
        '--recurse-symlinks',
        action='store_true',
        help='recurse into symbolic directory links, default is to rename a link but not recurse into it',
    )
    opt.add_argument(
        '-m',
        '--more-aggressive',
        action='store_true',
        help='replace repeated underscores even if there are no other replacements',
    )
    opt.add_argument(
        '-c',
        '--character',
        default='_',
        help='character to replace undesirable characters with, default = "%(default)s"',
    )
    opt.add_argument(
        '-a',
        '--add',
        default='',
        help='additional characters to allow in names, e.g. "+%%" '
        '(default: only alphanumeric, "_", "-", and ".")',
    )
    opt.add_argument(
        'path',
        nargs='*',
        default=['.'],
        help='one or more file or directory names to rename, or "-" to read names from stdin. '
        'Default is all files in current directory if no path given.',
    )

    args = opt.parse_args()

    if args.dryrun:
        args.quiet = False

    if len(args.character) != 1:
        opt.error('Error: -c/--character must be a single character.')

    # Read stdin if single dash is given as path
    if len(paths := args.path) == 1 and paths[0] == '-':
        if args.recurse:
            opt.error('Error: -r/--recurse cannot be used with stdin input.')

        paths = (ln.rstrip('\r\n') for ln in sys.stdin)

    args._map = re.compile(r'[^-.\w' + args.character + args.add + ']+', re.ASCII)
    args._reduce = re.compile('\\' + args.character + '+')

    rename_paths(args, (Path(a) for a in paths))


if __name__ == '__main__':
    main()
