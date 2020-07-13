"""Utility functions for testing Sparv with pytest."""

import difflib
import filecmp
import pathlib
import shutil
import subprocess

import snakemake

from sparv.core import paths
from sparv.util import Color

GOLD_PREFIX = "gold_"


def run_sparv(gold_corpus_dir: pathlib.Path,
              tmp_path: pathlib.Path,
              targets: list = ["xml_export:pretty"]):
    """Run Sparv on corpus in gold_corpus_dir and return the directory of the test corpus."""
    corpus_name = gold_corpus_dir.name
    new_corpus_dir = tmp_path / pathlib.Path(corpus_name)

    # Copy everything but the output
    shutil.copytree(str(gold_corpus_dir), str(new_corpus_dir), ignore=shutil.ignore_patterns(
        str(paths.annotation_dir), GOLD_PREFIX + str(paths.annotation_dir),
        str(paths.export_dir), GOLD_PREFIX + str(paths.export_dir)))

    args = ["sparv", "-d", str(new_corpus_dir), "run", "-o", *targets]
    process = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert process.returncode == 0, "corpus could not be annotated"
    return new_corpus_dir


def cmp_annotations(gold_corpus_dir: pathlib.Path,
                    test_corpus_dir: pathlib.Path,
                    ignore: list = []):
    """Recursively compare the annotation directories of gold_corpus and test_corpus."""
    ignore.append(".log")
    assert _cmp_dirs(gold_corpus_dir / pathlib.Path(GOLD_PREFIX + str(paths.annotation_dir)),
                     test_corpus_dir / paths.annotation_dir,
                     ignore=ignore
                     ), "annotations dir did not match the gold standard"


def cmp_export(gold_corpus_dir: pathlib.Path,
               test_corpus_dir: pathlib.Path,
               ignore: list = []):
    """Recursively compare the export directories of gold_corpus and test_corpus."""
    ignore.append(".log")
    assert _cmp_dirs(gold_corpus_dir / pathlib.Path(GOLD_PREFIX + str(paths.export_dir)),
                     test_corpus_dir / paths.export_dir,
                     ignore=ignore
                     ), "export dir did not match the gold standard"


def is_program(program: str):
    """Return True if program is an executable."""
    if shutil.which(program):
        return True
    return False


def format_error(msg: str):
    """Format msg into an error message."""
    return f"{Color.RED}\n{msg}{Color.RESET}"


################################################################################
# Auxiliaries
################################################################################


def _cmp_dirs(a: pathlib.Path,
              b: pathlib.Path,
              ignore: list = [".log"],
              ok: bool = True):
    """Recursively compare directories a and b."""
    dirs_cmp = filecmp.dircmp(str(a), str(b), ignore=ignore)

    if len(dirs_cmp.left_only) > 0:
        print(format_error(f"Missing contents in {b}: {', '.join(dirs_cmp.left_only)}"))
        ok = False
    if len(dirs_cmp.right_only) > 0:
        print(format_error(f"Missing contents in {a}: {', '.join(dirs_cmp.right_only)}"))
        ok = False
    if len(dirs_cmp.funny_files) > 0:
        print(format_error(f"Some files could not be compared: {', '.join(dirs_cmp.funny_files)}"))
        ok = False

    _match, mismatch, errors = filecmp.cmpfiles(a, b, dirs_cmp.common_files, shallow=False)
    if len(mismatch) > 0:
        print(format_error(f"Some files did not match in {a}: {', '.join(mismatch)}"))
        for filename in mismatch:
            print("\n" + filename)
            _filediff(a / filename, b / filename)
        ok = False
    if len(errors) > 0:
        print(format_error(f"Some files could not be compared: {', '.join(errors)}"))
        ok = False

    for common_dir in dirs_cmp.common_dirs:
        new_a = a / pathlib.Path(common_dir)
        new_b = b / pathlib.Path(common_dir)
        if not _cmp_dirs(new_a, new_b, ignore=ignore, ok=ok):
            ok = False

    if ok:
        return True
    return False


def _filediff(a: pathlib.Path, b: pathlib.Path):
    """Print a unified diff of files a and b."""
    with a.open() as a_contents:
        with b.open() as b_contents:
            diff = difflib.unified_diff(a_contents.readlines(), b_contents.readlines(), fromfile=str(a), tofile=str(b))
            for line in diff:
                print(line.strip())
