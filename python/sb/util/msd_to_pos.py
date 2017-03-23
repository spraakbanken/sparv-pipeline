# -*- coding: utf-8 -*-

# maps MSD tags to simple Universal Depenendy POS tags
# http://universaldependencies.org/u/pos/all.html

CONVERTERS = {
    "as": "as_convert_fl",
    "ca": "ca_convert_fl",
    "cy": "cy_convert_fl",  # Not used yet, FreeLing dict is not working.
    "de": "de_convert_fl",
    "es": "es_convert_fl",
    "en": "en_convert_fl",
    "fr": "fr_convert_fl",
    "gl": "gl_convert_fl",
    "it": "it_convert_fl",
    "no": "no_convert_fl",
    "pt": "pt_convert_fl",
    "ru": "ru_convert_fl",
    "sl": "sl_convert_fl",
    "bg": "bg_convert_tt",
    "et": "et_convert_tt",
    "fi": "fi_convert_tt",
    "nl": "nl_convert_tt",
    "la": "la_convert_tt",
    "pl": "pl_convert_tt",
    "ro": "ro_convert_tt",
    "sk": "sk_convert_tt",
}

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

#####################################################################
# FreeLing
#####################################################################

COMMON_FL_DICT = {
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


def convert(msd, lang):
    if lang in CONVERTERS:
        lang_convert = eval(CONVERTERS[lang])
        return lang_convert(msd)
    else:
        return msd


def common_fl_convert(msd):
    if msd[0] in "NVC":
        return COMMON_FL_DICT.get(msd[0:2], FALLBACK)
    else:
        return COMMON_FL_DICT.get(msd[0], FALLBACK)


def as_convert_fl(msd):
    return common_fl_convert(msd)


def ca_convert_fl(msd):
    return common_fl_convert(msd)


def cy_convert_fl(msd):
    return common_fl_convert(msd)


def de_convert_fl(msd):
    return common_fl_convert(msd)


def es_convert_fl(msd):
    return common_fl_convert(msd)


def fr_convert_fl(msd):
    return common_fl_convert(msd)


def gl_convert_fl(msd):
    return common_fl_convert(msd)


def it_convert_fl(msd):
    return common_fl_convert(msd)


def no_convert_fl(msd):
    return common_fl_convert(msd)


def pt_convert_fl(msd):
    return common_fl_convert(msd)


def sl_convert_fl(msd):
    return common_fl_convert(msd)


def ru_convert_fl(msd):
    return ru_dict.get(msd[0], FALLBACK)

ru_dict = {
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


def en_convert_fl(msd):
    if msd in ["NN", "NNS"]:
        return "NOUN"
    elif msd.startswith("N"):
        return "PROPN"
    if msd.startswith("F"):
        return "PUNCT"
    if msd.startswith("Z"):
        return "NUM"
    return en_dict.get(msd, FALLBACK)

en_dict = {
    # https://talp-upc.gitbooks.io/freeling-user-manual/content/tagsets/tagset-en.html  # FreeLing
    "CC": "CONJ",
    "DT": "DET",
    "WDT": "DET",
    "PDT": "DET",
    "EX": "PRON",
    "I": "INTJ",
    "IN": "ADP",
    "JJ": "ADJ",
    "JJR": "ADJ",
    "JJS": "ADJ",
    "MD": "VERB",
    "POS": "ADP",
    "PRP": "PRON",
    "PRP$": "PRON",
    "RB": "ADV",
    "RBR": "ADV",
    "RBS": "ADV",
    "WRB": "ADV",
    "RP": "PART",
    "TO": "PART",
    "UH": "INTJ",
    "VB": "VERB",
    "VBD": "VERB",
    "VBG": "VERB",
    "VBN": "VERB",
    "VBP": "VERB",
    "VBZ": "VERB",
    "WP": "PRON",
    "WP$": "PRON",
    "W": "NUM",
}

#####################################################################
# TreeTagger
#####################################################################


def bg_convert_tt(msd):
    if msd[0] in ["N", "V", "C"]:
        return bg_dict.get(msd[0:2], FALLBACK)
    if msd.startswith("PT"):
        return "PUNCT"
    else:
        return bg_dict.get(msd[0], FALLBACK)

bg_dict = {
    # http://www.bultreebank.org/TechRep/BTB-TR03.pdf
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


def et_convert_tt(msd):
    if "." in msd:
        pos = msd.split(".")[0]
        if pos == "J":
            return et_dict.get(msd, FALLBACK)
        return et_dict.get(msd.split(".")[0])
    else:
        return et_dict.get(msd, FALLBACK)

et_dict = {
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


def fi_convert_tt(msd):
    if msd in fi_dict:
        return fi_dict[msd]
    else:
        return fi_dict.get(msd.split("_")[0], FALLBACK)

fi_dict = {
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


def nl_convert_tt(msd):
    if len(msd) == 2 and msd.startswith("$."):
        return "PUNCT"
    elif msd == "pronadv":
        return "ADV"  # pronomial adverb
    elif msd == "det__art":
        return "DET"
    else:
        return nl_dict.get(msd[0:3], FALLBACK)

nl_dict = {
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


def la_convert_tt(msd):
    if ":" in msd:
        return la_dict.get(msd.split(":")[0], FALLBACK)
    else:
        return la_dict.get(msd, FALLBACK)

la_dict = {
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


def pl_convert_tt(msd):
    if ":" in msd:
        return pl_dict.get(msd.split(":")[0], FALLBACK)
    else:
        return pl_dict.get(msd, FALLBACK)

pl_dict = {
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


def ro_convert_tt(msd):
    if msd[0] in ["N", "V", "C", "S"]:
        return ro_dict.get(msd[0:2], FALLBACK)
    else:
        return ro_dict.get(msd[0], FALLBACK)

ro_dict = {
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


def sk_convert_tt(msd):
    if len(msd) == 1 and not msd.isalpha():
        return "PUNCT"
    elif msd.startswith(":"):
        return sk_dict.get(msd, FALLBACK)
    else:
        return sk_dict.get(msd[0], FALLBACK)

sk_dict = {
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


def de_convert_tt(msd):
    return de_dict[msd]

de_dict = {
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
