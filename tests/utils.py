"""Utility functions for testing Sparv with pytest."""
# ruff: noqa: T201

from __future__ import annotations

import difflib
import filecmp
import pickle
import re
import shutil
import subprocess
import xml.etree.ElementTree as etree  # noqa: N813
from pathlib import Path

from sparv.core.console import console
from sparv.core.paths import paths

GOLD_PREFIX = "gold_"
MAX_DIFF_LINES = 25


def run_sparv(gold_corpus_dir: Path, tmp_path: Path, rules: list | None = None) -> Path:
    """Run Sparv on corpus in gold_corpus_dir and return the directory of the test corpus.

    Args:
        gold_corpus_dir: Path to the directory of the gold corpus.
        tmp_path: Path to the temporary directory to use for the test corpus.
        rules: List of rules to run. If None, default rules will be used.

    Returns:
        Path to the directory of the test corpus.
    """
    if rules is None:
        rules = []
    corpus_name = gold_corpus_dir.name
    new_corpus_dir = tmp_path / Path(corpus_name)

    # Copy everything but the output
    shutil.copytree(
        str(gold_corpus_dir),
        str(new_corpus_dir),
        ignore=shutil.ignore_patterns(
            str(paths.work_dir),
            GOLD_PREFIX + str(paths.work_dir),
            str(paths.export_dir),
            GOLD_PREFIX + str(paths.export_dir),
        ),
    )

    args = ["sparv", "-d", str(new_corpus_dir), "run", *rules]
    process = subprocess.run(args, capture_output=True, check=False)
    stdout = _remove_progress_info(process.stdout.strip().decode())
    if stdout and process.returncode != 0:
        print_error(f"The following warnings/errors occurred:\n{stdout}")
    elif process.stderr.strip():
        print_error(process.stderr.strip().decode())
    assert process.returncode == 0, "corpus could not be annotated"
    return new_corpus_dir


def cmp_workdir(gold_corpus_dir: Path, test_corpus_dir: Path, ignore: list | None = None) -> None:
    """Recursively compare the workdir directories of gold_corpus and test_corpus.

    Args:
        gold_corpus_dir: Path to the directory of the gold corpus.
        test_corpus_dir: Path to the directory of the test corpus.
        ignore: List of files/directories to ignore when comparing.
    """
    if ignore is None:
        ignore = []
    ignore.append(".log")
    assert _cmp_dirs(
        gold_corpus_dir / Path(GOLD_PREFIX + str(paths.work_dir)), test_corpus_dir / paths.work_dir, ignore=ignore
    ), "work dir did not match the gold standard"


def cmp_export(gold_corpus_dir: Path, test_corpus_dir: Path, ignore: list | None = None) -> None:
    """Recursively compare the export directories of gold_corpus and test_corpus.

    Args:
        gold_corpus_dir: Path to the directory of the gold corpus.
        test_corpus_dir: Path to the directory of the test corpus.
        ignore: List of files/directories to ignore when comparing.
    """
    if ignore is None:
        ignore = []
    ignore.append(".log")
    assert _cmp_dirs(
        gold_corpus_dir / Path(GOLD_PREFIX + str(paths.export_dir)), test_corpus_dir / paths.export_dir, ignore=ignore
    ), "export dir did not match the gold standard"


def print_error(msg: str) -> None:
    """Format msg into an error message and print it to the console."""
    console.print(f"[red]\n{msg}[/red]", highlight=False)


################################################################################
# Auxiliaries
################################################################################


def _cmp_dirs(a: Path, b: Path, ignore: list | None = None, ok: bool = True) -> bool:
    """Recursively compare directories a and b.

    Args:
        a: Path to the first directory.
        b: Path to the second directory.
        ignore: List of files/directories to ignore when comparing.
        ok: Boolean indicating if the directories are equal so far (used for recursion).

    Returns:
        Boolean indicating if the directories are equal.
    """
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
        new_a = a / Path(common_dir)
        new_b = b / Path(common_dir)
        if not _cmp_dirs(new_a, new_b, ignore=ignore, ok=ok):
            ok = False

    return ok


def _filediff(a: Path, b: Path) -> None:
    """Print a unified diff of files a and b.

    Args:
        a: Path to the first file.
        b: Path to the second file.
    """
    try:
        # Try opening as pickle files first
        a_contents = pickle.load(a.open("rb"))
        a_contents = a_contents.splitlines() if isinstance(a_contents, str) else map(str, a_contents)

        b_contents = pickle.load(b.open("rb"))
        b_contents = b_contents.splitlines() if isinstance(b_contents, str) else map(str, b_contents)
    except pickle.UnpicklingError:
        # Compare as text files
        a_contents = a.read_text(encoding="utf-8").splitlines()
        b_contents = b.read_text(encoding="utf-8").splitlines()

    diff = difflib.unified_diff(a_contents, b_contents, fromfile=str(a), tofile=str(b))
    for i, line in enumerate(diff):
        if i > MAX_DIFF_LINES - 1:
            print("...")
            break
        print(line.strip())


def _xml_filediff(a: Path, b: Path) -> bool:
    """Print a unified diff of canonicalize XML files a and b and return True if they differ.

    Args:
        a: Path to the first XML file.
        b: Path to the second XML file.

    Returns:
        Boolean indicating if the files differ.
    """
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


def _remove_progress_info(output: str) -> str:
    """Remove progress updates from output.

    Args:
        output: The output string to process.

    Returns:
        The output string with progress updates removed.
    """
    lines = output.split("\n")
    out = []
    for line in lines:
        matchobj = re.match(r"(?:\d\d:\d\d:\d\d|\s{8}) (PROGRESS)\s+(.+)$", line)
        if not matchobj:
            out.append(line)
    return "\n".join(out)
