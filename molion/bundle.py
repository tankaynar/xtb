#!/usr/bin/env python3
"""Turns a conda-forge environment with xtb installed in it into a folder that runs on its own.

    python molion/bundle.py --prefix <conda env> --out <dir>

xtb built with conda-forge's gfortran links to shared libraries in the environment (OpenBLAS,
libgfortran, the OpenMP runtime...). This copies xtb, its parameter files and every library it
loads from the environment into <out>/xtb/{bin,share,lib}, so the folder runs with no conda
installed:

- macOS: each load path is rewritten to @rpath with the rpath pointing at xtb/lib, and each
  file is signed ad hoc again (install_name_tool breaks the signature, and arm64 refuses to
  run unsigned code).
- Linux: RUNPATH is set to $ORIGIN-relative xtb/lib with patchelf. glibc and the other system
  libraries stay the system's.

It also copies the licence files of every conda package a copied file came from. The libraries
kept in xtb/lib (not a lib/ shared with other programs) mean this xtb never replaces another
program's copy of libgfortran or OpenBLAS. Run by .github/workflows/molion-build.yml (Windows
is bundled there, from MSYS2). Standard library only, plus patchelf on Linux.
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys


def run(*command):
    return subprocess.run(command, check=True, capture_output=True, text=True).stdout


# ---- macOS ---------------------------------------------------------------------------------

def macho_needed(path):
    """The libraries a Mach-O file loads, as written in it (its own id excluded)."""
    lines = run('otool', '-L', path).splitlines()[1:]
    names = [line.strip().split(' (')[0] for line in lines]
    own_id = run('otool', '-D', path).splitlines()[1:]
    return [name for name in names if name not in own_id and not name.startswith(('/usr/lib/', '/System/'))]


def macho_rpaths(path):
    found, lines = [], run('otool', '-l', path).splitlines()
    for index, line in enumerate(lines):
        if line.strip() == 'cmd LC_RPATH':
            found.append(lines[index + 2].strip().split(' ')[1])
    return found


def macho_relink(target, is_library):
    for name in macho_needed(target):
        run('install_name_tool', '-change', name, '@rpath/' + os.path.basename(name), target)
    if is_library:
        run('install_name_tool', '-id', '@rpath/' + os.path.basename(target), target)
    for old in macho_rpaths(target):
        run('install_name_tool', '-delete_rpath', old, target)
    run('install_name_tool', '-add_rpath', '@loader_path' if is_library else '@loader_path/../lib', target)
    run('codesign', '--force', '--sign', '-', '--timestamp=none', target)


# ---- Linux ---------------------------------------------------------------------------------

# Provided by every glibc system; bundling them breaks programs instead of helping
LINUX_SYSTEM = ('libc.so', 'libm.so', 'libmvec.so', 'libdl.so', 'libpthread.so', 'librt.so',
                'ld-linux', 'libutil.so', 'libresolv.so')


def elf_needed(path):
    names = run('patchelf', '--print-needed', path).split()
    return [name for name in names if not name.startswith(LINUX_SYSTEM)]


def elf_relink(target, is_library):
    run('patchelf', '--set-rpath', '$ORIGIN' if is_library else '$ORIGIN/../lib', target)


# ---- all platforms -------------------------------------------------------------------------

def library_dirs(prefix):
    return [os.path.join(prefix, 'lib')]


def program_path(prefix, program):
    return os.path.join(prefix, 'bin', program)


def resolve(name, prefix):
    """The environment's copy of a library, or None for one the system provides."""
    for folder in library_dirs(prefix):
        for candidate in (os.path.join(folder, os.path.basename(name)),
                          os.path.join(folder, os.path.basename(name).lower())):
            if os.path.exists(candidate):
                return os.path.realpath(candidate)
    sys.exit(f'cannot find {name} in {prefix}')


def needed(path):
    if sys.platform == 'darwin':
        return macho_needed(path)
    return elf_needed(path)


def owners(prefix):
    """Real path of an installed file → (conda package name, folder it was unpacked into)."""
    table = {}
    package_cache = os.path.join(os.environ.get('MAMBA_ROOT_PREFIX', ''), 'pkgs')
    for record_path in glob.glob(os.path.join(prefix, 'conda-meta', '*.json')):
        with open(record_path, encoding='utf-8') as stream:
            record = json.load(stream)
        # conda records where it unpacked the package; micromamba may not, so fall back to
        # its package cache, named after the archive
        unpacked = record.get('extracted_package_dir') or os.path.join(
            package_cache, record.get('fn', '').removesuffix('.conda').removesuffix('.tar.bz2'))
        for relative in record.get('files', []):
            table[os.path.normcase(os.path.realpath(os.path.join(prefix, relative)))] = (record['name'], unpacked)
    return table


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--prefix', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    prefix, out = os.path.realpath(args.prefix), os.path.abspath(args.out)
    root = os.path.join(out, 'xtb')
    lib_dir = os.path.join(root, 'lib')
    shutil.rmtree(root, ignore_errors=True)

    program = os.path.join(root, 'bin', 'xtb')
    os.makedirs(os.path.dirname(program))
    shutil.copy2(program_path(prefix, 'xtb'), program)
    copied = {program: program_path(prefix, 'xtb')}   # destination → source
    shutil.copytree(os.path.join(prefix, 'share', 'xtb'), os.path.join(root, 'share', 'xtb'))

    # The closure of libraries, followed through the libraries' own imports
    pending = [program]
    while pending:
        for name in needed(pending.pop()):
            source = resolve(name, prefix)
            target = os.path.join(lib_dir, os.path.basename(name))
            if target not in copied:
                os.makedirs(lib_dir, exist_ok=True)
                shutil.copy2(source, target)
                os.chmod(target, 0o755)
                copied[target] = source
                pending.append(target)

    relink = macho_relink if sys.platform == 'darwin' else elf_relink
    for target in copied:
        relink(target, os.path.dirname(target) == lib_dir)

    # Licence files of every package a copied file came from
    table = owners(prefix)
    packages = {}
    for source in copied.values():
        key = os.path.normcase(os.path.realpath(source))
        if key in table:
            packages[table[key][0]] = table[key][1]
    for name, unpacked in sorted(packages.items()):
        licences = os.path.join(unpacked, 'info', 'licenses')
        target = os.path.join(root, 'licenses', name)
        if os.path.isdir(licences):
            shutil.copytree(licences, target)
        else:
            print(f'warning: no licence files found for {name}')
    print('packages bundled:', ', '.join(sorted(packages)))
    print('libraries:', ', '.join(sorted(os.path.basename(t) for t in copied if t != program)))


if __name__ == '__main__':
    main()
