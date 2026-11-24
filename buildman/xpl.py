# SPDX-License-Identifier: GPL-2.0+
# Copyright 2026 Simon Glass <sjg@chromium.org>

"""Information about U-Boot's xPL phases, such as TPL and SPL

The phases are listed in scripts/xpl_phases in the U-Boot source tree. Each
commit being built may have a different list, so this is read from the tree
being built, not cached
"""

import os

# Phases for a source tree which does not have scripts/xpl_phases
DEFAULT_PHASES = ('tpl', 'vpl', 'spl')


def parse_phases(text):
    """Parse the names of the xPL phases from scripts/xpl_phases

    Each line has the name of a phase, its devicetree tag and optional flags.
    The phase with the 'primary' flag is U-Boot proper, which is not an xPL
    phase, so is left out. Other flags are ignored

    Args:
        text (str): Contents of the file

    Returns:
        tuple of str: Lower-case name of each phase, in the order in which
            they run, e.g. ('tpl', 'vpl', 'spl')
    """
    phases = []
    for line in text.splitlines():
        fields = line.split('#')[0].split()
        if not fields or 'primary' in fields[2:]:
            continue
        phases.append(fields[0])
    return tuple(phases)


def read_phases(srcdir):
    """Read the names of the xPL phases from a U-Boot source tree

    Args:
        srcdir (str): Path to the source tree, or None to use the defaults

    Returns:
        tuple of str: Lower-case name of each phase, in the order in which
            they run, e.g. ('tpl', 'vpl', 'spl')
    """
    if not srcdir:
        return DEFAULT_PHASES
    fname = os.path.join(srcdir, 'scripts', 'xpl_phases')
    try:
        with open(fname, encoding='utf-8') as inf:
            return parse_phases(inf.read())
    except FileNotFoundError:
        return DEFAULT_PHASES


def elf_filenames(phases):
    """Get the ELF files which a build may produce

    Args:
        phases (tuple of str): xPL phases, e.g. from read_phases()

    Returns:
        list of str: ELF filenames relative to the output directory, with
            U-Boot proper first, e.g. ['u-boot', 'spl/u-boot-spl']
    """
    return ['u-boot'] + [f'{phase}/u-boot-{phase}' for phase in phases]
