# SPDX-License-Identifier: GPL-2.0+
# Copyright 2026 Simon Glass <sjg@chromium.org>

"""Tests for the xpl module"""

import os
import tempfile
import unittest

from buildman import xpl


class TestXpl(unittest.TestCase):
    """Tests for reading the xPL phases"""

    def test_parse(self):
        """The primary phase, comments and unknown flags are handled"""
        self.assertEqual(
            ('tpl', 'vpl', 'spl', 'mon'),
            xpl.parse_phases('# comment\n\ntpl\tbootph-pre-sram\n'
                             'vpl  bootph-verify # inline\n'
                             'spl\tbootph-pre-ram\tnew-flag\n'
                             'mon\t-\t\tresident\n'
                             'ppl\t-\t\tprimary\n'))
        self.assertEqual((), xpl.parse_phases(''))

    def test_read(self):
        """The phases are read from the source tree"""
        with tempfile.TemporaryDirectory() as srcdir:
            self.assertEqual(xpl.DEFAULT_PHASES, xpl.read_phases(srcdir))
            os.mkdir(os.path.join(srcdir, 'scripts'))
            with open(os.path.join(srcdir, 'scripts', 'xpl_phases'), 'w',
                      encoding='utf-8') as outf:
                outf.write('spl a\nmon -\tresident\nppl -\tprimary\n')
            self.assertEqual(('spl', 'mon'), xpl.read_phases(srcdir))
        self.assertEqual(xpl.DEFAULT_PHASES, xpl.read_phases(None))

    def test_elf_filenames(self):
        """Each phase has an ELF file in its own directory"""
        self.assertEqual(['u-boot', 'spl/u-boot-spl', 'mon/u-boot-mon'],
                         xpl.elf_filenames(('spl', 'mon')))


if __name__ == '__main__':
    unittest.main()
