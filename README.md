## RENAME-CLEAN - Replace Undesirable Characters in Linux File Names
[![PyPi](https://img.shields.io/pypi/v/rename-clean)](https://pypi.org/project/rename-clean/)

The [`rename-clean`][rename-clean] command line utility replaces undesirable
characters with underscores in Linux file names. Undesirable characters are any
that are not ASCII alphanumeric (`0-9`, `a-z`, `A-Z`), underscore (`_`), hyphen
(`-`), or dot (`.`). If characters are replaced, then repeated underscores are
also reduced to a single underscore and trimmed from the name stem and suffix.
A unique name is always created by appending a number on the name stem if
necessary.

I use it after downloading an archive of files from the internet such as a
torrent to remove spaces, emojis, and other odd characters from the file names.

Example usage follows:

Clean up all file and directory names in the current directory:

```sh
$ rename-clean (or rename-clean .)
```

Clean up all file and directory names in the current directory and recursively
under any child directories:

```sh
$ rename-clean -r
```

Clean up all all jpeg file names in current directory:

```sh
$ rename-clean *.jpg
```

Read a list of names to be cleaned up from a file:

```sh
$ rename-clean - <list-of-bad-file-names.txt
```

Clean up all file and directory names, but also allow `+` and `%` characters in
names. Note you can allow extra characters by default using the `-a/--add`
option as described in the [Command Default Options](#command-default-options)
section below:

```sh
$ rename-clean -a '+%'
```

You can run with the `-d/--dryrun` option to see what would be changed without
actually renaming anything.

The latest version and documentation is available at
https://github.com/bulletmark/rename-clean.

## Command Default Options

You can add default options to a personal configuration file
`~/.config/rename-clean-flags.conf`. If that file exists then each line of
options will be concatenated and automatically prepended to your `rename-clean`
command line arguments. Comments in the file (i.e. starting with a `#`) are
ignored. Type `rename-clean -h` to see all [supported
options](#command-line-options).

## Installation or Upgrade

Python 3.8 or later is required. Note [`rename-clean` is on
PyPI](https://pypi.org/project/rename-clean/) so the easiest way to install it is to
use [`uv tool`][uvtool].

```sh
$ uv tool install rename-clean
```

To upgrade:

```sh
$ uv tool upgrade rename-clean
```

To uninstall:

```sh
$ uv tool uninstall rename-clean
```

Alternatively, run it immediately using [`uvx`][uvx] without explicit
installation by typing `uvx rename-clean`.

## Command Line Options

Type `rename-clean -h` to view the usage summary:

```
usage: rename-clean [-h] [-r] [-d] [-q] [-i] [-s] [-m] [-c CHARACTER]
                       [-a ADD]
                       [path ...]

Utility to replace undesirable characters with underscores in Linux file
names. Undesirable characters are any that are not ASCII alphanumeric (`0-9`,
`a-z`, `A-Z`), underscore (`_`), hyphen (`-`), or dot (`.`). If characters are
replaced, then repeated underscores are also reduced to a single underscore
and trimmed from the name stem and suffix. A unique name is always created by
appending a number on the name stem if necessary.

positional arguments:
  path                  one or more file or directory names to rename, or "-"
                        to read names from stdin. Default is all files in
                        current directory if no path given.

options:
  -h, --help            show this help message and exit
  -r, --recurse         recurse through all sub directories
  -d, --dryrun          do not rename, just show what would be done
  -q, --quiet           do not report changes
  -i, --ignore-hidden   ignore hidden files and directories (those starting
                        with ".")
  -s, --recurse-symlinks
                        recurse into symbolic directory links, default is to
                        rename a link but not recurse into it
  -m, --more-aggressive
                        Replace underscores even if deletions have not been
                        done
  -c, --character CHARACTER
                        character to replace undesirable characters with,
                        default = "_"
  -a, --add ADD         additional characters to allow in names, e.g. "+%"
                        (default: only alphanumeric, "_", "-", and ".")

Note you can set default options in $HOME/.config/rename_clean-flags.conf
```

## License

Copyright (C) 2025 Mark Blakeney. This program is distributed under the
terms of the GNU General Public License. This program is free software:
you can redistribute it and/or modify it under the terms of the GNU
General Public License as published by the Free Software Foundation,
either version 3 of the License, or any later version. This program is
distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License at
<https://en.wikipedia.org/wiki/GNU_General_Public_License> for more details.

[rename-clean]: https://github.com/bulletmark/rename-clean
[uvtool]: https://docs.astral.sh/uv/guides/tools/#installing-tools
[uvx]: https://docs.astral.sh/uv/guides/tools/#running-tools

<!-- vim: se ai syn=markdown: -->
