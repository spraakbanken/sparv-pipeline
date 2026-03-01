"""Conversion from SUC MSD tags to UCoNNL feature lists.

This tag conversion was taken from this ruby script: https://github.com/spraakbanken/parsing/blob/master/msd_to_feats.rb
It might be worth improving this in the future, but it's good enough for now.
"""

MSD_TO_FEATS = {
    "UTR": "Gender=Com",
    "NEU": "Gender=Neut",
    "MAS": "Gender=Masc",
    "UTR+NEU": "Gender=Com,Neut",
    "SIN": "Number=Sing",
    "PLU": "Number=Plur",
    "SIN+PLU": "Number=Plur,Sing",
    "IND": "Definite=Ind",
    "DEF": "Definite=Def",
    "IND+DEF": "Definite=Def,Ind",
    "NOM": "Case=Nom",
    "GEN": "Case=Gen",
    "POS": "Degree=Pos",
    "KOM": "Degree=Cmp",
    "SUV": "Degree=Sup",
    "PRS": "Tense=Pres",
    "PRT": "Tense=Past",
    "INF": "VerbForm=Inf",
    "SUP": "VerbForm=Sup",
    "IMP": "Mood=Imp",
    "AKT": "Voice=Act",
    "SFO": "Voice=Pass",
    "KON": "Mood=Sub",
    "PRF": "Tense=Past",
    "AN": "Abbr=Yes",
    "SMS": "Compound=Yes",
    "SUB": "Case=Nom",
    "OBJ": "Case=Acc",
    "SUB+OBJ": "Case=Acc,Nom",
}


def suc_to_feats(pos: str, msd: str, delim: str = ".") -> list[str]:
    """Convert SUC MSD tags into UCoNNL feature list.

    Args:
        pos: The part-of-speech tag.
        msd: The MSD tag.
        delim: The delimiter used in the MSD tag.

    Returns:
        A list of UCoNNL features.
    """
    non_mapping_msds_for_debug = []
    feats = []
    msd = [i for i in msd.split(delim) if i != "-"]

    # If it's not punctuation and if there are MSDs apart from POS
    if pos not in {"MAD", "MID", "PAD"} and len(msd) > 1:
        feats = []
        for i in msd:
            if MSD_TO_FEATS.get(i):
                feats.append(MSD_TO_FEATS[i])
            elif i not in non_mapping_msds_for_debug:
                non_mapping_msds_for_debug.append(i)
        if pos == "PC":
            feats.append("VerbForm=Part")
        if pos == "VB" and "Abbr=Yes" not in feats and "Compound=Yes" not in feats and not _findfeat(feats, "VerbForm"):
            feats.append("VerbForm=Fin")
            if not _findfeat(feats, "Mood"):
                feats.append("Mood=Ind")

    return sorted(feats)


def _findfeat(feats: list[str], to_find: str) -> bool:
    """Check if 'to_find' is a feature (key) in 'feats'.

    Args:
        feats: List of features.
        to_find: Feature to find.

    Returns:
        True if 'to_find' is a feature in 'feats'.
    """
    return any(f"{to_find}=" in feat for feat in feats)
