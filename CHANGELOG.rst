Changelog
=========

All notable changes to this project are documented here. The format is
based on `Keep a Changelog <https://keepachangelog.com/en/1.1.0/>`_ and
the project follows `Semantic Versioning <https://semver.org/>`_.

Unreleased
----------

Changed
~~~~~~~
- When the output is not a terminal, e.g. in a CI log, a line of progress is
  shown at most once a minute and when the build finishes, instead of one for
  each build. The line cannot be overwritten there, so each update took up two
  lines of the log.

Fixed
~~~~~
- With ``-Y``, a board whose output is all filtered out is no longer shown as
  having warnings.
- ``-Y`` filters out the migration warnings which U-Boot produces now. It
  only matched the older form, which has a line of ``=`` above and below.

0.4.0 - 2026-11-21
------------------

Added
~~~~~
- kconfiglib understands the ``phases`` attribute of U-Boot's Kconfig, which
  defines an option once for several phases. As the C tool does, it reads the
  phases from ``scripts/xpl_phases`` in the source tree and creates a symbol
  for each phase of an option, so that the board scan and qconfig work with a
  tree which uses it. A tree without ``phases`` lines is handled as before.

0.3.1 - 2026-11-18
------------------

Fixed
~~~~~
- The board scan stops with an error if a scanner process fails, or a
  board is missing from the result, instead of carrying on without the
  boards which that process was scanning.
- The board scan uses at most 32 processes. With about 250 or more, as on
  a machine with that many CPUs, the last ones ran out of file
  descriptors which ``select()`` can handle and failed, so that some
  boards were left out.

0.3.0 - 2026-11-18
------------------

Added
~~~~~
- ``--shard K/N`` builds one of N shards of the selected boards: the boards
  are sorted by target name and every Nth one is kept, starting with the Kth.
  This allows a large build to be split evenly across several CI jobs.

Fixed
~~~~~
- 32-bit and 64-bit LoongArch boards are told apart by
  ``CONFIG_ARCH_LA64``, so each is built with the right toolchain, as for
  RISC-V and ARM.

0.2.0 - 2026-10-23
------------------

Changed
~~~~~~~
- Commits which cannot affect a board are skipped by default, as
  ``--skip-unaffected`` did. Use ``--no-skip-unaffected`` to build every
  commit.
- The U-Boot Python library is now a dependency, from the ``u-boot-pylib``
  package, rather than a copy vendored into buildman. A distributed build
  sends it to the workers along with buildman.

Fixed
~~~~~
- With adjusted configs (``-a`` or ``-r``), a board is reconfigured only when
  needed, as without them, rather than for every commit, and applying the
  adjustments runs make once fewer.
- ``buildman --coverage`` runs the tests even when the path to buildman
  contains 'binman', 'patman' or 'pickman', instead of passing them the wrong
  argument and reporting low coverage.
- A distributed build (``--dist``) records the same sizes as a local one:
  U-Boot proper, SPL and TPL, each with its ``.rodata`` size and named
  relative to the build directory, so that ``-S`` compares them correctly
  across commits built on different machines.

0.1.0 - 2026-10-05
------------------

Changed
~~~~~~~
- Buildman is now developed in its own repository at
  https://github.com/deinde-dev/buildman, with its history carried over from
  the U-Boot tree.
- Buildman is distributed as the self-contained ``buildman`` package, with
  ``u_boot_pylib``, the patman modules it uses and U-Boot's ``qconfig`` tool
  vendored in, installable from PyPI with ``pip install buildman``. It no
  longer depends on the ``u_boot_pylib`` and ``patch-manager`` packages.
- For distributed builds, the boss copies just the buildman package to each
  worker, since this now includes everything the worker needs.
- Documentation is now published at https://buildman.readthedocs.io/.

Earlier releases
----------------

Releases 0.0.7 and earlier were published from the U-Boot tree and predate
this changelog.
