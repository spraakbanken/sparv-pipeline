"""Tests for corpus annotations with Sparv."""

import pathlib

import pytest

import utils


def test_standard_swe(tmp_path):
    """Run corpus standard-swe and compare the annotations and exports to gold standard."""
    gold_corpus_dir = pathlib.Path("tests/test_corpora/standard-swe")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path, targets=[
        "xml_export:pretty",
        "csv_export:csv",
        "cwb:info",
        "cwb:vrt",
        "cwb:vrt_scrambled",
        "korp:relations_sql",
        "korp:timespan_sql",
        "stats_export:freq_list",
        "xml_export:pretty",
        "xml_export:preserved_format",
        "xml_export:scrambled",
    ])
    utils.cmp_annotations(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)


@pytest.mark.skipif(not utils.is_program("analyze"), reason="FreeLing is not installed")
def test_freeling1(tmp_path):
    """Run corpus freeling-deu-txt and compare the annotations and exports to gold standard."""
    gold_corpus_dir = pathlib.Path("tests/test_corpora/freeling-deu-txt")
    test_corpus_dir = utils.run_sparv(gold_corpus_dir, tmp_path, targets=["xml_export:pretty"])
    utils.cmp_annotations(gold_corpus_dir, test_corpus_dir)
    utils.cmp_export(gold_corpus_dir, test_corpus_dir)
