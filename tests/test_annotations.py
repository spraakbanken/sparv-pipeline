"""Tests for corpus annotations with Sparv."""

from pathlib import Path

import pytest
from sparv.api.util.system import find_binary

from . import utils


@pytest.mark.swe
# @pytest.mark.noexternal  TODO: this test fails in CI, enable when fixed
def test_mini_swe(tmp_path: Path) -> None:
    """Run corpus mini-swe and compare the annotations and exports to gold standard."""
    gold_corpus_dir = Path("tests/test_corpora/mini-swe")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path)
    utils.cmp_workdir(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir, ignore=["version_info"])


@pytest.mark.swe
@pytest.mark.noexternal
def test_special_swe(tmp_path: Path) -> None:
    """Run corpus special-swe and compare the annotations and exports to gold standard."""
    gold_corpus_dir = Path("tests/test_corpora/special-swe")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path)
    utils.cmp_workdir(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.swe
@pytest.mark.noexternal
def test_txt_swe(tmp_path: Path) -> None:
    """Run corpus txt-swe and compare the annotations and exports to gold standard."""
    gold_corpus_dir = Path("tests/test_corpora/txt-swe")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path)
    utils.cmp_workdir(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.swe
@pytest.mark.slow
def test_standard_swe(tmp_path: Path) -> None:
    """Run corpus standard-swe and compare the annotations and exports to gold standard."""
    gold_corpus_dir = Path("tests/test_corpora/standard-swe")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path)
    utils.cmp_workdir(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.swe
@pytest.mark.swehist
@pytest.mark.slow
def test_swe_1800(tmp_path: Path) -> None:
    """Run corpus swe-1800 and compare the annotations and exports to gold standard."""
    gold_corpus_dir = Path("tests/test_corpora/swe-1800")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path)
    utils.cmp_workdir(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.swe
@pytest.mark.swehist
@pytest.mark.noexternal
def test_swe_fsv(tmp_path: Path) -> None:
    """Run corpus swe-fsv and compare the annotations and exports to gold standard."""
    gold_corpus_dir = Path("tests/test_corpora/swe-fsv")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path)
    utils.cmp_workdir(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.freeling
@pytest.mark.skipif(not find_binary("analyze"), reason="FreeLing is not installed")
def test_freeling_eng_slevel(tmp_path: Path) -> None:
    """Run corpus freeling-eng-slevel and compare the annotations and exports to gold standard."""
    gold_corpus_dir = Path("tests/test_corpora/freeling-eng-slevel")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path)
    utils.cmp_workdir(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.freeling
@pytest.mark.skipif(not find_binary("analyze"), reason="FreeLing is not installed")
def test_freeling_fra_txt(tmp_path: Path) -> None:
    """Run corpus freeling-fra-txt and compare the annotations and exports to gold standard."""
    gold_corpus_dir = Path("tests/test_corpora/freeling-fra-txt")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path)
    utils.cmp_workdir(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.treetagger
@pytest.mark.skipif(not find_binary("tree-tagger"), reason="Treetagger is not available")
def test_treetagger_nld(tmp_path: Path) -> None:
    """Run corpus treetagger-nld and compare the annotations and exports to gold standard."""
    gold_corpus_dir = Path("tests/test_corpora/treetagger-nld")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path)
    utils.cmp_workdir(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.stanford
@pytest.mark.slow
@pytest.mark.skipif(not find_binary("stanford_parser", allow_dir=True), reason="Stanford Parser is not available")
def test_stanford_eng(tmp_path: Path) -> None:
    """Run corpus stanford-eng and compare the annotations and exports to gold standard."""
    gold_corpus_dir = Path("tests/test_corpora/stanford-eng")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path)
    utils.cmp_workdir(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)
