# xtb for Molion

This branch (`molion`) is [grimme-lab/xtb](https://github.com/grimme-lab/xtb) at the 6.8.0
release, upstream commit `4b8c987066c7e9bd0c2b727ce026fb9a581c273a` (2026-11-05), built for
[Molion](https://github.com/tankaynar/molion), which ships it.

**The xtb sources are upstream's, unchanged.** This branch adds only:

- `.github/workflows/molion-build.yml`: builds xtb for macOS arm64, Linux x64 and Windows x64,
  each into a folder that runs on its own, checks it, and publishes it as a release;
- `molion/`: this file and the scripts that workflow runs (`bundle.py` gathers the shared
  libraries on macOS and Linux, `licences.sh` the licence files, `check.sh` the checks).

Why not upstream's own release binaries: their Linux x64 build is Intel's compilers and MKL
(proprietary runtimes), and Molion's Linux package needs glibc 2.17; building all three here
the same way also runs the checks below on each. (Molion first built upstream main past 6.7.1,
whose `--esp` aborts at random on some geometries, IF5 and XeF6; 6.8.0 has that fix, and
`check.sh` still runs them.)

## Releases

Each `molion-<commit>` release holds `xtb-<platform>.zip` (with its SHA-256) and
`xtb-source.tar.xz`, the source of those builds: this tree with every subproject it was built
from, at the revisions `subprojects/*.wrap` pin. xtb and the libraries linked into it are
LGPL-3.0-or-later or more permissive; each zip carries every licence under `xtb/licenses/`.

The program reports upstream's version with the commit of this branch it was built from
(`xtb version 6.8.0 (<commit>)`); `xtb/COMMIT.txt` in each zip names that commit in full.
macOS and Linux builds use conda-forge's gfortran and OpenBLAS (Linux: glibc 2.17 or newer),
Windows MSYS2's UCRT64 gfortran.
