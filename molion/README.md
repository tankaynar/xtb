# xtb for Molion

This branch (`molion`) is [grimme-lab/xtb](https://github.com/grimme-lab/xtb) at upstream
commit `130708f060e95588db4cd7f7fe4c61325a9cb577` (2026-10-27), built for
[Molion](https://github.com/tankaynar/molion), which ships it.

**The xtb sources are upstream's, unchanged.** This branch adds only:

- `.github/workflows/molion-build.yml`: builds xtb for macOS arm64, Linux x64 and Windows x64,
  each into a folder that runs on its own, checks it, and publishes it as a release;
- `molion/`: this file and the scripts that workflow runs (`bundle.py` gathers the shared
  libraries on macOS and Linux, `licences.sh` the licence files, `check.sh` the checks).

Why not a release: upstream's latest, 6.7.1 (July 2024), aborts at random in `--esp` on some
geometries (IF5, XeF6), which upstream main fixes; no release since has it.

## Releases

Each `molion-<commit>` release holds `xtb-<platform>.zip` (with its SHA-256) and
`xtb-source.tar.xz`, the source of those builds: this tree with every subproject it was built
from, at the revisions `subprojects/*.wrap` pin. xtb and the libraries linked into it are
LGPL-3.0-or-later or more permissive; each zip carries every licence under `xtb/licenses/`.

The program still reports itself as `xtb version 6.7.1 (130708f)`, upstream's version with the
commit; `xtb/COMMIT.txt` in each zip names the commit too.
