"""Map different POS (or MSD) tags to simple Universal Depenendy POS (UPOS) tags.

http://universaldependencies.org/u/pos/all.html
"""

# Fallback POS
FALLBACK = "X"

# UD = {
#     "ADJ": "adjective",
#     "ADV": "adverb",
#     "INTJ": "interjection",
#     "NOUN": "noun",
#     "PROPN": "proper noun",
#     "VERB": "verb",
#     "ADP": "adposition",
#     "AUX": "auxiliary verb",
#     "CONJ": "coordinating conjunction",
#     "DET": "determiner",
#     "NUM": "numeral",
#     "PART": "particle",
#     "PRON": "pronoun",
#     "SCONJ": "subordinating conjunction",
#     "PUNCT": "punctuation",
#     "SYM": "symbol",
#     "X": "other"}


def convert_to_upos(pos, lang, tagset):
    """Map POS tags to Universal Depenendy POS tags."""
    if (lang, tagset) in CONVERTERS:
        lang_convert = CONVERTERS[(lang, tagset)]
        return lang_convert(pos)
    else:
        return ""


################################################################################
# EAGLES/FreeLing
################################################################################

EAGLES_DICT = {
    "A": "ADJ",
    "CC": "CONJ",
    "CS": "SCONJ",
    "D": "DET",
    "F": "PUNCT",
    "I": "INTJ",
    "NC": "NOUN",
    "NP": "PROPN",
    "P": "PRON",
    "R": "ADV",
    "S": "ADP",
    "VM": "VERB",
    "VA": "AUX",
    "VS": "VERB",
    "VV": "VERB",
    "W": "NUM",
    "Z": "NUM",
    "Y": "X",
    "X": "X"
}


def _EAGLES_convert(pos):
    """Convert EAGLES tags to UPOS."""
    if pos[0] in "NVC":
        return EAGLES_DICT.get(pos[0:2], FALLBACK)
    else:
        return EAGLES_DICT.get(pos[0], FALLBACK)


def _rus_FreeLing_convert(pos):
    """Convert Russian FreeLing tags to UPOS."""
    pos_dict = {
        "A": "ADJ",
        "B": "ADP",
        "C": "CONJ",
        "D": "ADV",
        "E": "PRON",
        "J": "INTJ",
        "M": "X",
        "NC": "NOUN",
        "NP": "PROPN",
        "P": "ADV",
        "Y": "NUM",
        "R": "ADV",
        "T": "PART",
        "Q": "VERB",
        "Z": "NUM",
        "V": "VERB",
        "F": "PUNCT",
        "W": "NUM",
    }
    return pos_dict.get(pos[0], FALLBACK)


def _eng_Penn_convert(pos):
    """Convert from Penn Treebank tagset (with FreeLing modifications)."""
    # https://freeling-user-manual.readthedocs.io/en/latest/tagsets/tagset-en/
    # https://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html
    pos_dict = {
        "CC": "CONJ",
        "DT": "DET",
        "EX": "PRON",
        "I": "INTJ",
        "IN": "ADP",
        "JJ": "ADJ",
        "JJR": "ADJ",
        "JJS": "ADJ",
        "MD": "VERB",
        "PDT": "DET",
        "POS": "ADP",
        "PRP": "PRON",
        "PRP$": "PRON",
        "RB": "ADV",
        "RBR": "ADV",
        "RBS": "ADV",
        "RP": "PART",
        "TO": "PART",
        "UH": "INTJ",
        "VB": "VERB",
        "VBD": "VERB",
        "VBG": "VERB",
        "VBN": "VERB",
        "VBP": "VERB",
        "VBZ": "VERB",
        "W": "NUM",
        "WDT": "DET",
        "WP": "PRON",
        "WP$": "PRON",
        "WRB": "ADV",
        "CD": "NUM",
        "FW": "X",
        "LS": "X",
        "SYM": "SYM"
    }
    if pos in ["NN", "NNS"]:
        return "NOUN"
    if pos.startswith("N"):
        return "PROPN"
    if pos == "FW":  # Foreign word in Penn Treebank tagset
        return "X"
    if pos.startswith("F"):
        return "PUNCT"
    if pos.startswith("Z"):
        return "NUM"
    return pos_dict.get(pos, FALLBACK)


################################################################################
# TreeTagger
################################################################################


def _bul_BulTreeBank_convert(pos):
    pos_dict = {
        # http://bultreebank.org/wp-content/uploads/2017/06/BTB-TR03.pdf
        "Nc": "NOUN",
        "Np": "PROPN",
        "A": "ADJ",
        "H": "PROPN",
        "P": "PRON",
        "M": "NUM",
        "Vp": "VERB",
        "Vn": "VERB",
        "Vx": "AUX",
        "Vy": "AUX",
        "Vi": "AUX",
        "D": "ADV",
        "Cc": "CONJ",
        "Cs": "SCONJ",
        "T": "PART",
        "R": "ADP",
        "I": "INTJ"
    }
    if pos[0] in ["N", "V", "C"]:
        return pos_dict.get(pos[0:2], FALLBACK)
    if pos.startswith("PT"):
        return "PUNCT"
    else:
        return pos_dict.get(pos[0], FALLBACK)


def _est_TreeTagger_convert(pos):
    pos_dict = {
        # http://www.cl.ut.ee/korpused/morfliides/seletus
        "S": "NOUN",
        "V": "VERB",
        "A": "ADJ",
        "G": "ADJ",
        "P": "PRON",
        "D": "ADV",
        "K": "ADP",
        "J. crd": "CONJ",
        "J. sub": "SCONJ",
        "N": "NUM",
        "I": "INTJ",
        "Y": "X",  # abbreviation
        "X": "ADV",
        "Z": "PUNCT",
        "T": "X"  # foreign
    }
    if "." in pos:
        pos = pos.split(".")[0]
        if pos == "J":
            return pos_dict.get(pos, FALLBACK)
        return pos_dict.get(pos.split(".")[0])
    else:
        return pos_dict.get(pos, FALLBACK)


def _fin_FinnTreeBank_convert(pos):
    pos_dict = {
        # http://www.ling.helsinki.fi/kieliteknologia/tutkimus/treebank/sources/FinnTreeBankManual.pdf
        # http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/finnish-tags.txt
        "Abbr": "X",  # abbreviation
        "Adp": "ADP",
        "Adv": "ADV",
        "Interj": "INTJ",
        "N": "NOUN",
        "Num": "NUM",
        "PrfPrc": "VERB",  # participle
        "Pron": "PRON",
        "PrsPrc": "VERB",  # participle
        "Punct": "PUNCT",
        "SENT": "PUNCT",
        "V": "VERB",
        "AgPcp": "VERB",  # participle
        "A": "ADJ",
        "CC": "CONJ",
        "CS": "SCONJ",
        "NON-TWOL": "X"  # unknown
    }
    if pos in pos_dict:
        return pos_dict[pos]
    else:
        return pos_dict.get(pos.split("_")[0], FALLBACK)


def _nld_TreeTagger_convert(pos):
    pos_dict = {
        # http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/dutch-tagset.txt
        "adj": "ADJ",
        "adv": "ADV",
        "con": "CONJ",
        "det": "DET",
        "int": "INTJ",
        "nou": "NOUN",
        "num": "NUM",
        "par": "PART",  # particle "te"
        "pre": "ADP",
        "pro": "PRON",
        "pun": "PUNCT",
        "ver": "VERB"
    }
    if len(pos) == 2 and pos.startswith("$."):
        return "PUNCT"
    elif pos == "pronadv":
        return "ADV"  # pronomial adverb
    elif pos == "det__art":
        return "DET"
    else:
        return pos_dict.get(pos[0:3], FALLBACK)


def _lat_TreeTagger_convert(pos):
    pos_dict = {
        # http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/Lamap-Tagset.pdf
        "ESSE": "AUX",
        "V": "VERB",
        "PRON": "PRON",
        "REL": "PRON",
        "POSS": "PRON",
        "DIMOS": "PRON",
        "INDEF": "PRON",
        "N": "NOUN",
        "NPR": "PROPN",
        "CC": "CONJ",
        "CS": "SCONJ",
        "ADJ": "ADJ",
        "ADV": "ADV",
        "PREP": "ADP",
        "INT": "INTJ",
        "ABBR": "X",  # abbreviation
        "EXCL": "INTJ",  # exclamations
        "FW": "X",  # foreign
        "SENT": "PUNCT",
        "PUN": "PUNCT",
        "SYM": "SYM",
        "CLI": "X"  # enclitics
    }
    if ":" in pos:
        return pos_dict.get(pos.split(":")[0], FALLBACK)
    else:
        return pos_dict.get(pos, FALLBACK)


def _pol_NationalCorpusofPolish_convert(pos):
    pos_dict = {
        # http://nkjp.pl/poliqarp/help/ense2.html
        "subst": "NOUN",
        "depr": "NOUN",  # depreciative form
        "num": "NUM",
        "numcol": "NUM",
        "adj": "ADJ",
        "adja": "ADJ",
        "adjp": "ADJ",
        "adjc": "ADJ",
        "adv": "ADV",
        "qub": "ADV",
        "ppron12": "PRON",
        "ppron3": "PRON",
        "siebie": "PRON",
        "fin": "VERB",
        "bedzie": "VERB",
        "inf": "VERB",
        "ger": "VERB",
        "aglt": "VERB",
        "praet": "PART",
        "pcon": "PART",
        "pant": "PART",
        "pact": "PART",
        "ppas": "PART",
        "impt": "VERB",  # imperative
        "imps": "VERB",  # impersonal
        "winien": "AUX",  # winien
        "pred": "ADJ",  # predicative
        "prep": "ADP",
        "conj": "CONJ",
        "comp": "SCONJ",
        "brev": "X",  # abbreviation
        "burk": "X",  # bound word
        "interj": "INTJ",
        "interp": "PUNCT",
        "SENT": "PUNCT",
        "xxx": "X",  # alien
        "ign": "X"  # unknown form
    }
    if ":" in pos:
        return pos_dict.get(pos.split(":")[0], FALLBACK)
    else:
        return pos_dict.get(pos, FALLBACK)


def _ron_MULTEXT_convert(pos):
    # http://nl.ijs.si/ME/V4/msd/tables/msd-human-ro.tbl
    pos_dict = {
        "Nc": "NOUN",
        "Np": "PROPN",
        "Vm": "VERB",
        "Va": "AUX",
        "A": "ADJ",
        "P": "PRON",
        "D": "DET",
        "T": "DET",
        "R": "ADV",
        "Sp": "ADP",
        "SE": "PUNCT",
        "Cc": "CONJ",
        "Cr": "CONJ",
        "Cs": "SCONJ",
        "CO": "PUNCT",
        "M": "NUM",
        "Q": "PART",
        "I": "INTJ",
        "Y": "X",  # abbreviation
        "X": "X"
    }
    if pos[0] in ["N", "V", "C", "S"]:
        return pos_dict.get(pos[0:2], FALLBACK)
    else:
        return pos_dict.get(pos[0], FALLBACK)


def _slk_SlovakNationalCorpus_convert(pos):
    pos_dict = {
        # http://korpus.juls.savba.sk/morpho_en.html
        "S": "NOUN",
        "A": "ADJ",
        "P": "PRON",
        "N": "NUM",
        "V": "VERB",
        "G": "PART",
        "D": "ADV",
        "E": "ADP",
        "O": "CONJ",  # conjunction
        "T": "PART",
        "J": "INTJ",
        "R": "X",  # reflexive morpheme
        "Y": "X",  # conditional morpheme
        "W": "SYM",  # abbreviation, symbol
        "Z": "PUNCT",
        "Q": "X",
        "#": "X",  # non-verbal element
        "%": "X",  # foreign language citation
        "0": "NUM",
        ":r": "PROPN",
        ":q": "X"  # incorrect spelling
    }
    if len(pos) == 1 and not pos.isalpha():
        return "PUNCT"
    elif pos.startswith(":"):
        return pos_dict.get(pos, FALLBACK)
    else:
        return pos_dict.get(pos[0], FALLBACK)


def _deu_STTS_convert(pos):
    pos_dict = {
        # http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/data/stts_guide.pdf
        "ADJA": "adjective",
        "ADJD": "adjective",
        "ADV": "adverb",
        "APPR": "preposition",
        "APPRART": "preposition",
        "APPO": "postposition",
        "APZR": "right circumposition",
        "ART": "article",
        "CARD": "cardinal number",
        "FM": "foreign word",
        "ITJ": "interjection",
        "ORD": "ordinal number",
        "KOUI": "subjunction",
        "KOUS": "subjunction",
        "KON": "conjunction",
        "KOKOM": "conjunction",
        "NN": "noun",
        "NE": "proper name",
        "PDS": "pronoun",
        "PDAT": "pronoun",
        "PIS": "pronoun",
        "PIAT": "pronoun",
        "PIDAT": "pronoun",
        "PPER": "pronoun",
        "PPOSS": "pronoun",
        "PPOSAT": "pronoun",
        "PRELS": "pronoun",
        "PRELAT": "pronoun",
        "PRF": "pronoun",
        "PWS": "pronoun",
        "PWAT": "pronoun",
        "PWAV": "pronoun",
        "PAV": "adverb",
        "PTKZU": "infinitive marker 'zu'",
        "PTKNEG": "negation particle",
        "PTKVZ": "particle",
        "PTKANT": "particle",
        "PTKA": "particle",
        "SGML": "SGML markup",
        "SPELL": "spelling",
        "TRUNC": "truncated word (first part)",
        "VVFIN": "verb",
        "VVIMP": "verb",
        "VVINF": "verb",
        "VVIZU": "verb",
        "VVPP": "verb",
        "VAFIN": "verb",
        "VAIMP": "verb",
        "VAINF": "verb",
        "VAPP": "verb",
        "VMFIN": "verb",
        "VMINF": "verb",
        "VMPP": "verb",
        "XY": "non-word",
        "$,": "punctuation",
        "$.": "punctuation",
        "$(": "punctuation"
    }
    return pos_dict[pos]


################################################################################
# Converter mapping
################################################################################


CONVERTERS = {
    # FreeLing:
    ("ast", "EAGLES"): _EAGLES_convert,
    ("cat", "EAGLES"): _EAGLES_convert,
    # ("cy", "EAGLES"): _EAGLES_convert,  # Welsh, Not used yet, FreeLing dict is not working.
    ("deu", "EAGLES"): _EAGLES_convert,
    ("spa", "EAGLES"): _EAGLES_convert,
    ("eng", "Penn"): _eng_Penn_convert,
    ("fra", "EAGLES"): _EAGLES_convert,
    ("glg", "EAGLES"): _EAGLES_convert,
    ("ita", "EAGLES"): _EAGLES_convert,
    ("nob", "EAGLES"): _EAGLES_convert,
    ("por", "EAGLES"): _EAGLES_convert,
    ("rus", "EAGLES"): _rus_FreeLing_convert,
    ("slv", "EAGLES"): _EAGLES_convert,
    # TreeTagger:
    ("bul", "BulTreeBank"): _bul_BulTreeBank_convert,
    ("est", "TreeTagger"): _est_TreeTagger_convert,
    ("fin", "FinnTreeBank"): _fin_FinnTreeBank_convert,
    ("nld", "TreeTagger"): _nld_TreeTagger_convert,
    ("lat", "TreeTagger"): _lat_TreeTagger_convert,
    ("pol", "NationalCorpusofPolish"): _pol_NationalCorpusofPolish_convert,
    ("ron", "MULTEXT"): _ron_MULTEXT_convert,
    ("slk", "SlovakNationalCorpus"): _slk_SlovakNationalCorpus_convert,
    ("deu", "STTS"): _deu_STTS_convert,
}
