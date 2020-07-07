"""Tests for corpus annotations with Sparv."""

import pathlib

import pytest

import utils


def test_swestandard(tmp_path):
    """Run corpus swestandard and compare the annotations and exports to gold standard."""
    gold_corpus_dir = pathlib.Path("tests/swestandard")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path, targets=["xml_export:pretty"])
    utils.cmp_annotations(gold_corpus_dir, test_corpus_dir, ignore=["wsd.sense"])
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.skipif(not utils.is_program("analyze"), reason="FreeLing is not installed")
def test_freeling1(tmp_path):
    """Run corpus freeling1 and compare the annotations and exports to gold standard."""
    gold_corpus_dir = pathlib.Path("tests/freeling1")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path, targets=["xml_export:pretty"])
    utils.cmp_annotations(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)
