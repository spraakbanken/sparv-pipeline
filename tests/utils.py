"""Utility functions for testing Sparv with pytest."""

import difflib
import filecmp
import pathlib
import re
import shutil
import subprocess
import xml.etree.ElementTree as etree
from typing import Optional

from sparv.core import paths
from sparv.core.console import console

GOLD_PREFIX = "gold_"


def run_sparv(gold_corpus_dir: pathlib.Path,
              tmp_path: pathlib.Path,
              targets: Optional[list] = None):
    """Run Sparv on corpus in gold_corpus_dir and return the directory of the test corpus."""
    if targets is None:
        targets = []
    corpus_name = gold_corpus_dir.name
    new_corpus_dir = tmp_path / pathlib.Path(corpus_name)

    # Copy everything but the output
    shutil.copytree(str(gold_corpus_dir), str(new_corpus_dir), ignore=shutil.ignore_patterns(
        str(paths.work_dir), GOLD_PREFIX + str(paths.work_dir),
        str(paths.export_dir), GOLD_PREFIX + str(paths.export_dir)))

    args = ["sparv", "-d", str(new_corpus_dir), "run", *targets]
    process = subprocess.run(args, capture_output=True)
    stdout = _remove_progress_info(process.stdout.strip().decode())
    if stdout and process.returncode != 0:
        print_error(f"The following warnings/errors occurred:\n{stdout}")
    elif process.stderr.strip():
        print_error(process.stderr.strip().decode())
    assert process.returncode == 0, "corpus could not be annotated"
    return new_corpus_dir


def cmp_workdir(gold_corpus_dir: pathlib.Path,
                test_corpus_dir: pathlib.Path,
                ignore: list = None):
    """Recursively compare the workdir directories of gold_corpus and test_corpus."""
    if ignore is None:
        ignore = []
    ignore.append(".log")
    assert _cmp_dirs(gold_corpus_dir / pathlib.Path(GOLD_PREFIX + str(paths.work_dir)),
                     test_corpus_dir / paths.work_dir,
                     ignore=ignore
                     ), "work dir did not match the gold standard"


def cmp_export(gold_corpus_dir: pathlib.Path,
               test_corpus_dir: pathlib.Path,
               ignore: list = None):
    """Recursively compare the export directories of gold_corpus and test_corpus."""
    if ignore is None:
        ignore = []
    ignore.append(".log")
    assert _cmp_dirs(gold_corpus_dir / pathlib.Path(GOLD_PREFIX + str(paths.export_dir)),
                     test_corpus_dir / paths.export_dir,
                     ignore=ignore
                     ), "export dir did not match the gold standard"


def print_error(msg: str):
    """Format msg into an error message."""
    console.print(f"[red]\n{msg}[/red]", highlight=False)


################################################################################
# Auxiliaries
################################################################################


def _cmp_dirs(a: pathlib.Path,
              b: pathlib.Path,
              ignore: list = None,
              ok: bool = True):
    """Recursively compare directories a and b."""
    if ignore is None:
        ignore = [".log"]
    dirs_cmp = filecmp.dircmp(str(a), str(b), ignore=ignore)

    if len(dirs_cmp.left_only) > 0:
        print_error(f"Missing contents in {b}: {', '.join(dirs_cmp.left_only)}")
        ok = False
    if len(dirs_cmp.right_only) > 0:
        print_error(f"Missing contents in {a}: {', '.join(dirs_cmp.right_only)}")
        ok = False
    if len(dirs_cmp.funny_files) > 0:
        print_error(f"Some files could not be compared: {', '.join(dirs_cmp.funny_files)}")
        ok = False

    # Compare non XML files
    common_no_xml = [f for f in dirs_cmp.common_files if not f.endswith(".xml")]
    _match, mismatch, errors = filecmp.cmpfiles(a, b, common_no_xml, shallow=False)
    if len(mismatch) > 0:
        print_error(f"Some files did not match in {a}: {', '.join(mismatch)}")
        for filename in mismatch:
            print("\n" + filename)
            _filediff(a / filename, b / filename)
        ok = False
    if len(errors) > 0:
        print_error(f"Some files could not be compared: {', '.join(errors)}")
        ok = False

    # Compare XML files
    common_xml = [f for f in dirs_cmp.common_files if f.endswith(".xml")]
    for filename in common_xml:
        if _xml_filediff(a / filename, b / filename):
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
    a_contents = a.read_text(encoding="utf-8").splitlines()
    b_contents = b.read_text(encoding="utf-8").splitlines()

    diff = difflib.unified_diff(a_contents, b_contents, fromfile=str(a), tofile=str(b))
    for line in diff:
        print(line.strip())


def _xml_filediff(a: pathlib.Path, b: pathlib.Path):
    """Print a unified diff of canonicalize XML files a and b."""
    try:
        a_contents = etree.canonicalize(a.read_text(encoding="utf-8")).splitlines()
    except etree.ParseError:
        print_error(f"File {a} could not be parsed.")
        return True
    try:
        b_contents = etree.canonicalize(b.read_text(encoding="utf-8")).splitlines()
    except etree.ParseError:
        print_error(f"File {a} could not be parsed.")
        return True

    diff = list(difflib.unified_diff(a_contents, b_contents, fromfile=str(a), tofile=str(b)))

    if diff:
        print_error(f"Files {a} did not match:")
        for line in diff:
            print(line.strip())
        return True
    return False


def _remove_progress_info(output):
    """Exclude progress updates from output."""
    lines = output.split("\n")
    out = []
    for line in lines:
        matchobj = re.match(r"(?:\d\d:\d\d:\d\d|\s{8}) (PROGRESS)\s+(.+)$", line)
        if not matchobj:
            out.append(line)
    return "\n".join(out)
