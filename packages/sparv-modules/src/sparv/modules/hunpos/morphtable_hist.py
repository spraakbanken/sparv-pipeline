"""Make morphtable for Swedish historical resources."""

import re
from pathlib import Path

from sparv.api import Model, ModelOutput, modelbuilder
from sparv.api.util.tagsets import tagmappings


@modelbuilder("Hunpos morphtable for Swedish historical resources", language=["swe-1800"])
def hist_morphtable(
    out: ModelOutput = ModelOutput("hunpos/hist/dalinm-swedberg_saldo_suc-tags.morphtable"),
    swedberg: Model = Model("hunpos/hist/swedberg-gender.hunpos"),
    dalin: Model = Model("hunpos/hist/dalinm.hunpos"),
    saldosuc_morphtable: Model = Model("hunpos/saldo_suc-tags.morphtable"),
) -> None:
    """Read files and make a morphtable together with the information from SALDO (saldosuc_morphtable).

    Args:
        out: Resulting morphtable file to be written.
        swedberg: Word list from Swedberg and corresponding SALDO MSD-tags.
        dalin: Word list from Dalin and corresponding SALDO MSD-tags.
        saldosuc_morphtable: SALDO Hunpos morphtable.
    """
    saldo_to_suc = tagmappings.mappings.saldo_to_suc
    saldo_to_suc["pm"] = {"PM.NOM"}
    saldo_to_suc["nl invar"] = {"NL.NOM"}

    def _read_saldosuc(words: dict, saldosuc_morphtable: Path) -> None:
        with saldosuc_morphtable.open(encoding="utf-8") as f:
            for line in f:
                xs = line.strip().split("\t")
                words.setdefault(xs[0], set()).update(set(xs[1:]))

    def _force_parse(msd: str) -> set:
        # This is a modification of _make_saldo_to_suc in utils.tagsets.py
        params = msd.split()

        # try ignoring gender, m/f => u
        for i, param in enumerate(params):
            if param.strip() in {"m", "f"}:
                params[i] = "u"
        new_suc = saldo_to_suc.get(" ".join(params), "")

        if new_suc:
            # print "Add translation", msd,new_suc
            saldo_to_suc[msd] = new_suc
            return new_suc

        # try changing place: nn sg n indef nom => nn n sg indef nom
        if params[0] == "nn":
            new_suc = saldo_to_suc.get(" ".join([params[0], params[2], params[1], params[3], params[4]]), "")

        if new_suc:
            # print "Add translation", msd,new_suc
            saldo_to_suc[msd] = new_suc
            return new_suc

        # try adding case info: av pos def pl => av pos def pl nom/gen
        if params[0] == "av":
            new_suc = saldo_to_suc.get(" ".join([*params, "nom"]), set())
            new_suc.update(saldo_to_suc.get(" ".join([*params, "gen"]), set()))

        if new_suc:
            # print "Add translation", msd,new_suc
            saldo_to_suc[msd] = new_suc
            return new_suc

        paramstr = " ".join(tagmappings.mappings["saldo_params_to_suc"].get(prm, prm.upper()) for prm in params)
        for pre, post in tagmappings._suc_tag_replacements:  # noqa: B007
            m = re.match(pre, paramstr)
            if m:
                break
        if m is None:
            return set()
        sucfilter = m.expand(post).replace(" ", r"\.").replace("+", r"\+")
        new_suc = {suctag for suctag in tagmappings.tags["suc_tags"] if re.match(sucfilter, suctag)}
        saldo_to_suc[msd] = new_suc
        return new_suc

    words = {}
    _read_saldosuc(words, saldosuc_morphtable.path)
    for fil in [dalin, swedberg]:
        with fil.path.open(encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                xs = line.split("\t")
                word, msd = xs[0].strip(), xs[1].strip()
                if " " in word:
                    if msd.startswith("nn"):  # We assume that the head of a noun mwe is the last word
                        word = word.split()[-1]
                    if msd.startswith("vb"):  # We assume that the head of a verbal mwe is the first word
                        word = word.split()[0]

                # If the tag is not present, we try to translate it anyway
                suc = saldo_to_suc.get(msd, "")
                if not suc:
                    suc = _force_parse(msd)
                if suc:
                    words.setdefault(word.lower(), set()).update(suc)
                    words.setdefault(word.title(), set()).update(suc)
    with out.path.open(encoding="UTF-8", mode="w") as out_file:
        for w, ts in words.items():
            line = "\t".join([w, *list(ts)]) + "\n"
            out_file.write(line)


@modelbuilder("Swedberg word list", language=["swe-1800"])
def download_swedberg_wordlist(out: ModelOutput = ModelOutput("hunpos/hist/swedberg-gender.hunpos")) -> None:
    """Download Swedberg word list.

    Args:
        out: Output model file.
    """
    out.download("https://github.com/spraakbanken/sparv-models/raw/master/hunpos/hist/swedberg-gender.hunpos")


@modelbuilder("Dalin word list", language=["swe-1800"])
def download_dalin_wordlist(out: ModelOutput = ModelOutput("hunpos/hist/dalinm.hunpos")) -> None:
    """Download Dalin word list.

    Args:
        out: Output model file.
    """
    out.download("https://github.com/spraakbanken/sparv-models/raw/master/hunpos/hist/dalinm.hunpos")
