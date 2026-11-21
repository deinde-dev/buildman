# SPDX-License-Identifier: GPL-2.0+
# Copyright 2026 Simon Glass <sjg@chromium.org>

"""Tests for the U-Boot additions to kconfiglib

U-Boot's Kconfig lets an option be defined once for several phases, with a
'phases' line. The C tool in U-Boot (scripts/kconfig) creates a symbol for each
phase and kconfiglib has to do the same, so that the board scan and qconfig
see the same options and values.
"""

import os
import tempfile
import unittest

from buildman import kconfiglib

# Phases used by most of the tests
PHASES = '''# Phases used by the test
tpl	bootph-pre-sram
spl	bootph-pre-ram
ppl	-		primary
'''

# These are from U-Boot's scripts/kconfig/tests/phases: the Kconfig file, the
# configuration to start from and the CONFIG lines which the C tool writes
PHASES_KCONFIG = '''config SPL
	bool "Enable SPL"

config TPL
	bool "Enable TPL"

config ARCH_X
	bool "Architecture X"

config DM
	bool "Driver model"
	phases all

config PRINTF
	bool "printf()"
	phases ppl spl

config SERIAL
	bool "Serial"
	phases all
	depends on DM
	select PRINTF

config SERIAL
	phases !ppl
	depends on PPL_SERIAL
	default y

config MAX_SIZE
	hex "Maximum size"
	phases spl tpl
	default 0x1000

config GLOBAL
	bool "Same in every phase, except for a twin"

config SPL_GLOBAL
	bool "Twin written out by hand"

config USES_GLOBAL
	bool "Depends on an option with no phases"
	phases all
	depends on GLOBAL

config PRIMARY_ONLY
	bool "Only in the primary phase"
	phases ppl
	default y

menu "Menu"
	depends on DM

config IN_MENU
	bool "In a menu"
	phases all

endmenu

if SERIAL

config IN_IF
	bool "In an if block"
	phases all
	default y

endif

config BY_ARCH
	bool "Default set by the architecture"
	phases all

if ARCH_X

config BY_ARCH
	phases all
	default y

endif
'''

PHASES_CONFIG = '''CONFIG_SPL=y
CONFIG_TPL=y
CONFIG_ARCH_X=y
CONFIG_DM=y
CONFIG_SPL_DM=y
CONFIG_SERIAL=y
CONFIG_SPL_MAX_SIZE=0x2000
CONFIG_GLOBAL=y
CONFIG_USES_GLOBAL=y
CONFIG_SPL_USES_GLOBAL=y
CONFIG_TPL_USES_GLOBAL=y
CONFIG_SPL_IN_MENU=y
CONFIG_TPL_IN_MENU=y
'''

PHASES_EXPECTED = '''CONFIG_SPL=y
CONFIG_TPL=y
CONFIG_ARCH_X=y
CONFIG_DM=y
CONFIG_PRINTF=y
CONFIG_SERIAL=y
CONFIG_GLOBAL=y
# CONFIG_SPL_GLOBAL is not set
CONFIG_USES_GLOBAL=y
CONFIG_PRIMARY_ONLY=y
# CONFIG_IN_MENU is not set
CONFIG_IN_IF=y
CONFIG_BY_ARCH=y
# CONFIG_TPL_DM is not set
CONFIG_TPL_MAX_SIZE=0x1000
CONFIG_TPL_BY_ARCH=y
CONFIG_SPL_DM=y
CONFIG_SPL_PRINTF=y
CONFIG_SPL_SERIAL=y
CONFIG_SPL_MAX_SIZE=0x2000
CONFIG_SPL_IN_MENU=y
CONFIG_SPL_IN_IF=y
CONFIG_SPL_BY_ARCH=y
'''

# Start of each test Kconfig, which enables the phases
HEAD = '''config SPL
	bool "Enable SPL"

config TPL
	bool "Enable TPL"

'''


def config_lines(text):
    """Get the lines of a .config file which set or clear an option

    Args:
        text (str): Contents of the file

    Returns:
        list of str: Lines such as 'CONFIG_FOO=y' or '# CONFIG_FOO is not set'
    """
    return [line for line in text.splitlines()
            if line.startswith(('CONFIG_', '# CONFIG_'))]


class TestPhases(unittest.TestCase):
    """Tests for options which are defined once for several phases"""

    def setUp(self):
        # pylint: disable-next=consider-using-with
        self._tmpdir = tempfile.TemporaryDirectory()
        self.srctree = self._tmpdir.name
        self._old_srctree = os.environ.get('srctree')
        os.environ['srctree'] = self.srctree

    def tearDown(self):
        if self._old_srctree is None:
            del os.environ['srctree']
        else:
            os.environ['srctree'] = self._old_srctree
        self._tmpdir.cleanup()

    def write(self, fname, data):
        """Write a file into the source tree

        Args:
            fname (str): Filename relative to the tree
            data (str): Contents to write
        """
        path = os.path.join(self.srctree, fname)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as outf:
            outf.write(data)

    def parse(self, kconfig, phases=PHASES):
        """Parse a Kconfig file

        Args:
            kconfig (str): Contents of the Kconfig file
            phases (str): Contents of scripts/xpl_phases, None to leave it out

        Returns:
            kconfiglib.Kconfig: Parsed Kconfig
        """
        self.write('Kconfig', kconfig)
        if phases is not None:
            self.write('scripts/xpl_phases', phases)
        return kconfiglib.Kconfig(warn=True, warn_to_stderr=False)

    def check_error(self, kconfig, expect, phases=PHASES):
        """Check that a Kconfig file is rejected

        Args:
            kconfig (str): Contents of the Kconfig file
            expect (str): Text which the error message must contain
            phases (str): Contents of scripts/xpl_phases, None to leave it out
        """
        with self.assertRaises(kconfiglib.KconfigError) as exc:
            self.parse(kconfig, phases)
        self.assertIn(expect, str(exc.exception))

    def write_config(self, kconf):
        """Write the configuration and get the lines which matter

        Args:
            kconf (kconfiglib.Kconfig): Kconfig to write

        Returns:
            list of str: Lines which set or clear an option
        """
        fname = os.path.join(self.srctree, 'out.config')
        kconf.write_config(fname)
        with open(fname, encoding='utf-8') as inf:
            return config_lines(inf.read())

    def test_config(self):
        """The configuration matches what the C tool writes"""
        kconf = self.parse(PHASES_KCONFIG)
        self.assertEqual([], kconf.warnings)
        self.write('config', PHASES_CONFIG)
        kconf.load_config(os.path.join(self.srctree, 'config'))
        self.assertEqual(config_lines(PHASES_EXPECTED),
                         self.write_config(kconf))

    def test_symbols(self):
        """A symbol is created for each phase, with its own dependencies"""
        kconf = self.parse(HEAD + '''config DM
	bool "Driver model"
	phases all

config SERIAL
	bool "Serial"
	phases ppl spl
	depends on DM

config MAX_SIZE
	hex "Maximum size"
	phases !ppl
	default 0x1000
''')
        syms = kconf.syms
        self.assertEqual(kconfiglib.BOOL, syms['SPL_SERIAL'].orig_type)
        self.assertNotIn('TPL_SERIAL', syms)
        self.assertEqual('DM', kconfiglib.expr_str(syms['SERIAL'].direct_dep))
        self.assertEqual('SPL_DM && SPL',
                         kconfiglib.expr_str(syms['SPL_SERIAL'].direct_dep))

        # An option which leaves out the primary phase has no symbol there
        self.assertEqual(kconfiglib.UNKNOWN, syms['MAX_SIZE'].orig_type)
        self.assertEqual([], syms['MAX_SIZE'].nodes)
        self.assertEqual(kconfiglib.HEX, syms['TPL_MAX_SIZE'].orig_type)

        # The options of each phase are in a menu of their own
        prompts = [node.prompt[0] for node in kconf.menus]
        self.assertEqual(['TPL phase options', 'SPL phase options'], prompts)

    def test_combine(self):
        """Entries are combined, keeping the 'if' around a later one"""
        kconf = self.parse(HEAD + '''config ARCH_X
	bool "Architecture X"

if ARCH_X

config FOO
	phases all
	default y

endif

config FOO
	bool "Foo"
	phases all
''')
        for name, cond in (('FOO', 'ARCH_X'), ('SPL_FOO', 'ARCH_X && SPL')):
            sym = kconf.syms[name]
            self.assertEqual(1, len(sym.nodes))
            self.assertEqual('Foo', sym.nodes[0].prompt[0])
            self.assertEqual(
                [('y', cond)],
                [(kconfiglib.expr_str(val), kconfiglib.expr_str(expr))
                 for val, expr in sym.defaults])

        # The option is not limited to that architecture
        self.assertEqual('y', kconfiglib.expr_str(kconf.syms['FOO'].direct_dep))

    def test_twin(self):
        """An option with a twin for another phase only is off in this one"""
        kconf = self.parse(HEAD + '''config GLOBAL
	bool "Same in every phase, except for a twin"

config SPL_GLOBAL
	bool "Twin written out by hand"

config USES
	bool "Depends on an option with no phases"
	phases all
	depends on GLOBAL
''')
        deps = {name: kconfiglib.expr_str(kconf.syms[name].direct_dep)
                for name in ('USES', 'SPL_USES', 'TPL_USES')}
        self.assertEqual({'USES': 'GLOBAL', 'SPL_USES': 'SPL_GLOBAL && SPL',
                          'TPL_USES': 'n'}, deps)

    def test_primary_only(self):
        """A list of phases with only the primary phase works"""
        kconf = self.parse('''config FOO
	bool "In every phase"
	phases all

config BAR
	bool "Only in the primary phase"
	phases ppl
''', 'ppl - primary\n')
        self.assertEqual(['# CONFIG_FOO is not set', '# CONFIG_BAR is not set'],
                         self.write_config(kconf))
        self.assertEqual([], kconf.menus)

    def test_flags(self):
        """Other flags in the list of phases are ignored"""
        kconf = self.parse('''config FOO
	bool "In every phase"
	phases all
''', 'rpl - resident\nspl bootph-pre-ram # runs before primary\n'
                       'ppl - primary\n')
        self.assertIn('RPL_FOO', kconf.syms)
        self.assertIn('SPL_FOO', kconf.syms)
        self.assertNotIn('PPL_FOO', kconf.syms)

    def test_no_phases(self):
        """The list of phases is not needed if nothing uses 'phases'"""
        kconf = self.parse('''config FOO
	bool "Foo"
	default y
''', None)
        self.assertEqual(['CONFIG_FOO=y'], self.write_config(kconf))

    def test_select_warning(self):
        """Selecting an option with a single symbol gives a warning"""
        kconf = self.parse(HEAD + '''config PLAIN
	bool "Same in every phase"

config ALSO_PLAIN
	bool "Also the same in every phase"

config HAS_TWIN
	bool "Has a twin written out by hand"

config SPL_HAS_TWIN
	bool "Twin for SPL"

config NET
	bool "Networking"
	phases all
	select PLAIN
	imply PLAIN
	select PPL_ALSO_PLAIN
	select HAS_TWIN

config PRIMARY_NET
	bool "Networking in the primary phase"
	phases ppl
	select PLAIN
''')
        msg = ("Kconfig:19: warning: 'NET' {} 'PLAIN', which is the same in "
               "every phase: use 'PPL_PLAIN' if this is intended")
        self.assertEqual([msg.format('selects'), msg.format('implies')],
                         kconf.warnings)

    def test_errors(self):
        """Uses of 'phases' which are not supported are reported"""
        self.check_error(HEAD + '''config SERIAL
	bool "Serial"
	phases all

config SERIAL
	default y
''', "Kconfig:11: error: 'SERIAL' has phases, so each of its entries needs "
                         "a 'phases' line")
        self.check_error(HEAD + '''choice
	prompt "Console"

config CONSOLE_UART
	bool "UART"
	phases all

endchoice
''', "Kconfig:10: error: 'phases' is not supported in a choice")
        self.check_error(HEAD + '''config DM
	bool "Driver model"
	phases all

config SPL_DM
	bool "Driver model in SPL"
''', "Kconfig:11: error: 'SPL_DM' comes from the phases of 'DM', so cannot "
                         "have an entry")
        self.check_error(HEAD + '''config FOO
	bool "Foo"
	phases rpl
''', "unknown phase 'rpl'")
        self.check_error(HEAD + '''config FOO
	bool "Foo"
	phases spl !spl
''', "'phases' leaves the option with no phases")
        self.check_error(HEAD + '''menu "Menu"
	phases all
endmenu
''', "'phases' is only supported in a config entry")

    def test_value_errors(self):
        """The value of an option which is not in the phase cannot be used"""
        head = HEAD + '''config SIZE
	int "Size"
	phases ppl
	default 8

'''
        msg = ("error: 'SIZE' is not in the TPL phase, so its value cannot be "
               "used")
        self.check_error(head + '''config RANGED
	int "Has a range"
	phases all
	range 1 SIZE
''', msg)
        self.check_error(head + '''config USES_SIZE
	int "Default from another option"
	phases all
	default SIZE
''', msg)
        self.check_error(head + '''config COMPARES
	bool "Compares another option"
	phases all
	depends on SIZE > 4
''', msg)

    def test_table_errors(self):
        """A missing list of phases, or one with no primary phase, is rejected"""
        kconfig = '''config FOO
	bool "Foo"
	phases all
'''
        self.check_error(kconfig, 'cannot be read', None)
        self.check_error(kconfig, 'has no primary phase',
                         'spl bootph-pre-ram\n')

    def test_uboot(self):
        """The test in a U-Boot tree gives the same result, if there is one"""
        uboot = os.environ.get('UBOOT_SRC')
        tdir = uboot and os.path.join(uboot, 'scripts/kconfig/tests/phases')
        if not tdir or not os.path.exists(tdir):
            self.skipTest('No U-Boot tree with a test for phases')
        os.environ['srctree'] = tdir
        kconf = kconfiglib.Kconfig(warn=True, warn_to_stderr=False)
        self.assertEqual([], kconf.warnings)
        kconf.load_config(os.path.join(tdir, 'config'))
        with open(os.path.join(tdir, 'expected_config'),
                  encoding='utf-8') as inf:
            self.assertEqual(config_lines(inf.read()),
                             self.write_config(kconf))
