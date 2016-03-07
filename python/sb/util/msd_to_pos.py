# -*- coding: utf-8 -*-

# maps MSD tags to simple POS tags


def convert(msd, lang):
    lang_convert = eval(lang + "_convert")
    return lang_convert(msd)


def es_convert(msd):
    return common_fl_dict[msd[0]]


def it_convert(msd):
    return common_fl_dict[msd[0]]


def pt_convert(msd):
    return common_fl_dict[msd[0]]


def fr_convert(msd):
    return common_fl_dict[msd[0]]

common_fl_dict = {
    "A": "adjective",
    "R": "adverb",
    "D": "determiner",
    "N": "noun",
    "V": "verb",
    "P": "pronoun",
    "C": "conjunction",
    "I": "interjection",
    "S": "preposition",
    "F": "punctuation",
    "Z": "numeral"
}


def ru_convert(msd):
    return ru_dict[msd[0]]

ru_dict = {
    "A": "adjective",
    "D": "adverb",
    "P": "pronominal adverb",
    "Y": "ordinal number",
    "R": "pronominal adjective",
    "M": "part of a composite",
    "C": "conjunction",
    "J": "interjection",
    "Z": "numeral",
    "T": "particle",
    "B": "preposition",
    "N": "noun",
    "E": "pronoun",
    "V": "verb",
    "Q": "participle",
    "F": "punctuation"
}


def sk_convert(msd):
    if len(msd) == 1 and not msd.isalpha():
        return "punctuation"
    elif msd.startswith(":"):
        return sk_dict[msd]
    else:
        return sk_dict[msd[0]]

sk_dict = {
    "S": "noun",
    "A": "adjective",
    "P": "pronoun",
    "N": "numeral",
    "V": "verb",
    "G": "participle",
    "D": "adverb",
    "E": "preposition",
    "O": "conjunction",
    "T": "particle",
    "J": "interjection",
    "R": "reflexive morpheme",
    "Y": "conditional morpheme",
    "W": "abbreviation, symbol",
    "Z": "punctuation",
    "Q": "undefinable part of speech",
    "#": "non-verbal element",
    "%": "foreign language citation",
    "0": "number",
    ":r": "proper name",
    ":q": "incorrect spelling"
    }


def nl_convert(msd):
    if len(msd) == 2 and msd.startswith("$."):
        return "punctuation"
    elif msd == "pronadv":
        return "pronomial adverb"
    elif msd == "det__art":
        return "article"
    else:
        return nl_dict[msd[0:3]]

nl_dict = {
    "adj": "adjective",
    "adv": "adverb",
    "con": "conjunction",
    "det": "article",
    "det": "pronoun",
    "int": "interjection",
    "nou": "noun",
    "num": "number",
    "par": 'particle "te"',
    "pre": "preposition",
    "pro": "pronoun",
    "pun": "punctuation",
    "ver": "verb"
}

def de_convert(msd):
    return de_dict[msd]

de_dict = {
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
    "SGML":  "SGML markup",
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


def en_convert(msd):
    if msd.startswith("F"):
        return "punctuation"
    if msd.startswith("Z"):
        return "numeral"
    return en_dict[msd]

en_dict = {
    "CC": "coordinating conjunction",
    "CD": "cardinal number",
    "DT": "determiner",
    "EX": "existential there",
    "FW": "foreign material",
    "IN": "preposition / subordinating conjunction",
    "JJ": "adjective",
    "JJR": "adjective",
    "JJS": "adjective",
    "LS": "list item marker",
    "MD": "modal",
    "NN": "noun",
    "NNS": "noun",
    "NNP": "proper name",
    "NNPS": "proper name",
    "PDT": "predeterminer",
    "POS": "possessive ending",
    "PRP": "pronoun",
    "PRP$": "pronoun",
    "RB": "adverb",
    "RBR": "adverb",
    "RBS": "adverb",
    "RP": "particle",
    "TO": "to",
    "UH": "interjection",
    "VB": "verb",
    "VBD": "verb",
    "VBG": "verb",
    "VBN": "verb",
    "VBP": "verb",
    "VBZ": "verb",
    "WDT": "wh-determiner",
    "WP": "pronoun",
    "WP$": "pronoun",
    "WRB": "adverb",
    "I": "interjection"
    }


def pl_convert(msd):
    if ":" in msd:
        return pl_dict[msd.split(":")[0]]
    else:
        return pl_dict[msd]

pl_dict = {
    "subst" : "noun",
    "depr" : "depreciative form",
    "num" : "numeral",
    "numcol" : "numeral",
    "adj" : "adjective",
    "adja" : "adjective",
    "adjp" : "adjective",
    "adjc" : "adjective",
    "adv" : "adverb",
    "qub" : "adverb",
    "ppron12" : "pronoun",
    "ppron3" : "pronoun",
    "siebie" : "pronoun",
    "fin" : "verb",
    "bedzie" : "verb",
    "inf" : "verb",
    "ger" : "verb",
    "aglt" : "verb",
    "praet" : "participle",
    "pcon" : "participle",
    "pant" : "participle",
    "pact" : "participle",
    "ppas" : "participle",
    "impt" : "imperative",
    "imps" : "impersonal",
    "winien" : "winien",
    "pred" : "predicative",
    "prep" : "preposition",
    "conj" : "conjunction",
    "comp" : "conjunction",
    "brev" : "abbreviation",
    "burk" : "bound word",
    "interj" : "interjection",
    "interp" : "punctuation",
    "SENT" : "punctuation",
    "xxx" : "alien",
    "ign": "unknown form"
}

def la_convert(msd):
    if ":" in msd:
        return la_dict[msd.split(":")[0]]
    else:
        return la_dict[msd]

la_dict = {
    "ESSE" : "verb",
    "V" : "verb",
    "PRON" : "pronoun",
    "REL" : "pronoun",
    "POSS" : "pronoun",
    "DIMOS" : "pronoun",
    "INDEF" : "pronoun",
    "N" : "noun",
    "NPR" : "proper noun",
    "CC" : "conjunction",
    "CS" : "conjunction",
    "ADJ" : "adjective",
    "ADV" : "adverb",
    "PREP" : "preposition",
    "INT" : "interjection",
    "ABBR" : "abbreviation",
    "EXCL" : "exclamations",
    "FW" : "foreign",
    "SENT" : "punctuation",
    "PUN" : "punctuation",
    "SYM" : "symbol",
    "CLI" : "enclitics"
}

def et_convert(msd):
    if "." in msd:
        return et_dict[msd.split(".")[0]]
    else:
        return et_dict[msd]

et_dict = {
    "S" : "noun",
    "V" : "verb",
    "A" : "adjective",
    "G" : "adjective",
    "P" : "pronoun",
    "D" : "adverb",
    "K" : "adposition",
    "J" : "conjunction",
    "N" : "numeral",
    "I" : "interjection",
    "Y" : "abbreviation",
    "X" : "adverb",
    "Z" : "punctuation",
    "T" : "foreign"
}

def bg_convert(msd):
    if msd.startswith("PT"):
        return "punctuation"
    else:
        return bg_dict[msd[0]]

bg_dict = {
    "N" : "noun",
    "A" : "adjective",
    "H" : "family name",
    "P" : "pronoun",
    "M" : "numeral",
    "V" : "verb",
    "D" : "adverb",
    "C" : "conjunction",
    "T" : "particle",
    "R" : "preposition",
    "I" : "interjection"
}

def fi_convert(msd):
    if msd in fi_dict:
        return fi_dict[msd]
    else:
        return fi_dict[msd.split("_")[0]]

fi_dict = {
    "Abbr" : "abbreviation",
    "Adp" : "adposition",
    "Adp" : "adposition",
    "Adv" : "adverb",
    "Interj" : "interjection",
    "N" : "noun",
    "Num" : "numeral",
    "PrfPrc" : "participle",
    "Pron" : "pronoun",
    "PrsPrc" : "participle",
    "Punct" : "punctuation",
    "SENT" : "punctuation",
    "V" : "verb",
    "AgPcp" : "participle",
    "A" : "adjective",
    "CC" : "conjunction",
    "CS" : "conjunction",
    "NON-TWOL" : "unknown"
}
