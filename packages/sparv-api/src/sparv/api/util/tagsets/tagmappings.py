"""This module contains translations between Saldo, SUC, Parole and Granska-ish tagsets.

The Parole and SUC tags are described here:
  https://spraakbanken.gu.se/parole/tags.html

* Constants:

TAGSEP = ".": a non-space separator between parts of POS/MSD attributes

* Functions:

split_tag: splits a SUC or Saldo tag into a pair (pos/part-of-speech, msd/morphology)
join_tag: joins a SUC or Saldo {pos:.., msd:..} record into a tag

* Tagsets:

simple_tags: the pos part of SUC tags
suc_tags: all SUC tags
parole_tags: all Parole tags
granska_tags: all Granska-ish tags
saldo_tags: all Saldo tags

* Dictionaries with descriptions:

suc_descriptions: 1-1 mapping between SUC tags and a Swedish description

* Dictionaries for tag conversion:

suc_to_simple: manu-1 mapping between SUC (msd) and SUC (pos)

suc_to_parole: 1-1 mapping between SUC and Parole
parole_to_suc: 1-1 mapping between Parole and SUC

granska_to_parole: many-1 mapping between Granska-ish and Parole
granska_to_suc: many-1 mapping between Granska-ish and SUC
parole_to_granska: 1-many mapping between Parole and Granska-ish
suc_to_granska: 1-many mapping between SUC and Granska-ish

saldo_to_suc: 1-many mapping between Saldo and SUC
saldo_to_granska: 1-many mapping between Saldo and Granska-ish
saldo_to_parole: 1-many mapping between Saldo and Parole
saldo_to_saldo: 1-many identity mapping of Saldo tags
"""

# ruff: noqa: E241, E501
from __future__ import annotations

import re

TAGSEP = "."


def split_tag(tag: str, sep: str = TAGSEP) -> tuple:
    """Split a tag "X.Y.Z" into a tuple ("X", "Y.Z").

    Args:
        tag: A tag to split.
        sep: A separator between parts of the tag.

    Returns:
        A tuple (pos, msd).
    """
    pos_msd = tuple(tag.split(sep, 1))
    if len(pos_msd) == 1:
        return pos_msd[0], ""
    return pos_msd


def join_tag(tag: dict | tuple, sep: str = TAGSEP) -> str:
    """Join a complex tag into a string.

    The tag can be a dict {"pos": pos, "msd": msd} or a tuple (pos, msd).

    Args:
        tag: A tag to join.
        sep: A separator between parts of the tag in the result.

    Returns:
        The joined tag.
    """
    if isinstance(tag, dict):
        pos, msd = tag["pos"], tag["msd"]
    else:
        pos, msd = tag
    return pos + sep + msd if msd else pos


_suc_descriptions = {
    "AB": "adverb",
    "AB.AN": "adverb förkortning",
    "AB.KOM": "adverb komparativ",
    "AB.POS": "adverb positiv",
    "AB.SMS": "adverb sammansättningsform",
    "AB.SUV": "adverb superlativ",
    "MAD": "meningsskiljande interpunktion",
    "MID": "interpunktion",
    "PAD": "interpunktion",
    "DT.AN": "determinerare förkortning",
    "DT.MAS.SIN.DEF": "determinerare maskulinum singularis bestämd",
    "DT.MAS.SIN.IND": "determinerare maskulinum singularis obestämd",
    "DT.NEU.SIN.DEF": "determinerare neutrum singularis bestämd",
    "DT.NEU.SIN.IND": "determinerare neutrum singularis obestämd",
    "DT.NEU.SIN.IND+DEF": "determinerare neutrum singularis obestämd/bestämd",
    "DT.UTR.SIN.DEF": "determinerare utrum singularis bestämd",
    "DT.UTR.SIN.IND": "determinerare utrum singularis obestämd",
    "DT.UTR.SIN.IND+DEF": "determinerare utrum singularis obestämd/bestämd",
    "DT.UTR+NEU.PLU.DEF": "determinerare utrum/neutrum pluralis bestämd",
    "DT.UTR+NEU.PLU.IND": "determinerare utrum/neutrum pluralis obestämd",
    "DT.UTR+NEU.PLU.IND+DEF": "determinerare utrum/neutrum pluralis obestämd/bestämd",
    "DT.UTR+NEU.SIN.DEF": "determinerare utrum/neutrum singularis bestämd",
    "DT.UTR+NEU.SIN.IND": "determinerare utrum/neutrum singularis obestämd",
    "DT.UTR+NEU.SIN+PLU.IND": "determinerare utrum/neutrum singularis/pluralis obestämd",
    "HA": "frågande/relativt adverb",
    "HD.NEU.SIN.IND": "frågande/relativ determinerare neutrum singularis obestämd",
    "HD.UTR.SIN.IND": "frågande/relativ determinerare utrum singularis obestämd",
    "HD.UTR+NEU.PLU.IND": "frågande/relativ determinerare utrum/neutrum pluralis obestämd",
    "HP.-.-.-": "frågande/relativt pronomen",
    "HP.NEU.SIN.IND": "frågande/relativt pronomen neutrum singularis obestämd",
    "HP.NEU.SIN.IND.SMS": "frågande/relativt pronomen neutrum singularis obestämd sammansättningsform",
    "HP.UTR.SIN.IND": "frågande/relativt pronomen utrum singularis obestämd",
    "HP.UTR+NEU.PLU.IND": "frågande/relativt pronomen utrum/neutrum pluralis obestämd",
    "HS.DEF": "frågande/relativt possesivt pronomen bestämd",
    "IE": "infinitivmärke",
    "IN": "interjektion",
    "JJ.AN": "adjektiv förkortning",
    "JJ.KOM.UTR+NEU.SIN+PLU.IND+DEF.GEN": "adjektiv komparativ utrum/neutrum singularis/pluralis obestämd/bestämd genitiv",
    "JJ.KOM.UTR+NEU.SIN+PLU.IND+DEF.NOM": "adjektiv komparativ utrum/neutrum singularis/pluralis obestämd/bestämd nominativ",
    "JJ.KOM.UTR+NEU.SIN+PLU.IND+DEF.SMS": "adjektiv komparativ utrum/neutrum singularis/pluralis obestämd/bestämd sammansättningsform",
    "JJ.POS.MAS.SIN.DEF.GEN": "adjektiv positiv maskulinum singularis bestämd genitiv",
    "JJ.POS.MAS.SIN.DEF.NOM": "adjektiv positiv maskulinum singularis bestämd nominativ",
    "JJ.POS.NEU.SIN.IND.GEN": "adjektiv positiv neutrum singularis obestämd genitiv",
    "JJ.POS.NEU.SIN.IND.NOM": "adjektiv positiv neutrum singularis obestämd nominativ",
    "JJ.POS.NEU.SIN.IND+DEF.NOM": "adjektiv positiv neutrum singularis obestämd/bestämd nominativ",
    "JJ.POS.UTR.-.-.SMS": "adjektiv positiv utrum sammansättningsform",
    "JJ.POS.UTR.SIN.IND.GEN": "adjektiv positiv utrum singularis obestämd genitiv",
    "JJ.POS.UTR.SIN.IND.NOM": "adjektiv positiv utrum singularis obestämd nominativ",
    "JJ.POS.UTR.SIN.IND+DEF.NOM": "adjektiv positiv utrum singularis obestämd/bestämd nominativ",
    "JJ.POS.UTR+NEU.-.-.SMS": "adjektiv positiv utrum/neutrum sammansättningsform",
    "JJ.POS.UTR+NEU.PLU.IND.NOM": "adjektiv positiv utrum/neutrum pluralis obestämd nominativ",
    "JJ.POS.UTR+NEU.PLU.IND+DEF.GEN": "adjektiv positiv utrum/neutrum pluralis obestämd/bestämd genitiv",
    "JJ.POS.UTR+NEU.PLU.IND+DEF.NOM": "adjektiv positiv utrum/neutrum pluralis obestämd/bestämd nominativ",
    "JJ.POS.UTR+NEU.SIN.DEF.GEN": "adjektiv positiv utrum/neutrum singularis bestämd genitiv",
    "JJ.POS.UTR+NEU.SIN.DEF.NOM": "adjektiv positiv utrum/neutrum singularis bestämd nominativ",
    "JJ.POS.UTR+NEU.SIN+PLU.IND.NOM": "adjektiv positiv utrum/neutrum singularis/pluralis obestämd nominativ",
    "JJ.POS.UTR+NEU.SIN+PLU.IND+DEF.NOM": "adjektiv positiv utrum/neutrum singularis/pluralis obestämd/bestämd nominativ",
    "JJ.SUV.MAS.SIN.DEF.GEN": "adjektiv superlativ maskulinum singularis bestämd genitiv",
    "JJ.SUV.MAS.SIN.DEF.NOM": "adjektiv superlativ maskulinum singularis bestämd nominativ",
    "JJ.SUV.UTR+NEU.PLU.DEF.NOM": "adjektiv superlativ utrum/neutrum pluralis bestämd nominativ",
    "JJ.SUV.UTR+NEU.PLU.IND.NOM": "adjektiv superlativ utrum/neutrum pluralis obestämd nominativ",
    "JJ.SUV.UTR+NEU.SIN+PLU.DEF.NOM": "adjektiv superlativ utrum/neutrum singularis/pluralis bestämd nominativ",
    "JJ.SUV.UTR+NEU.SIN+PLU.IND.NOM": "adjektiv superlativ utrum/neutrum singularis/pluralis obestämd nominativ",
    "KN": "konjunktion",
    "KN.AN": "konjunktion förkortning",
    "NN.-.-.-.-": "substantiv",
    "NN.-.-.-.SMS": "substantiv sammansättningsform",
    "NN.AN": "substantiv förkortning",
    "NN.NEU.-.-.-": "substantiv neutrum",
    "NN.NEU.-.-.SMS": "substantiv neutrum sammansättningsform",
    "NN.NEU.PLU.DEF.GEN": "substantiv neutrum pluralis bestämd genitiv",
    "NN.NEU.PLU.DEF.NOM": "substantiv neutrum pluralis bestämd nominativ",
    "NN.NEU.PLU.IND.GEN": "substantiv neutrum pluralis obestämd genitiv",
    "NN.NEU.PLU.IND.NOM": "substantiv neutrum pluralis obestämd nominativ",
    "NN.NEU.SIN.DEF.GEN": "substantiv neutrum singularis bestämd genitiv",
    "NN.NEU.SIN.DEF.NOM": "substantiv neutrum singularis bestämd nominativ",
    "NN.NEU.SIN.IND.GEN": "substantiv neutrum singularis obestämd genitiv",
    "NN.NEU.SIN.IND.NOM": "substantiv neutrum singularis obestämd nominativ",
    "NN.UTR.-.-.-": "substantiv utrum",
    "NN.UTR.-.-.SMS": "substantiv utrum sammansättningsform",
    "NN.UTR.PLU.DEF.GEN": "substantiv utrum pluralis bestämd genitiv",
    "NN.UTR.PLU.DEF.NOM": "substantiv utrum pluralis bestämd nominativ",
    "NN.UTR.PLU.IND.GEN": "substantiv utrum pluralis obestämd genitiv",
    "NN.UTR.PLU.IND.NOM": "substantiv utrum pluralis obestämd nominativ",
    "NN.UTR.SIN.DEF.GEN": "substantiv utrum singularis bestämd genitiv",
    "NN.UTR.SIN.DEF.NOM": "substantiv utrum singularis bestämd nominativ",
    "NN.UTR.SIN.IND.GEN": "substantiv utrum singularis obestämd genitiv",
    "NN.UTR.SIN.IND.NOM": "substantiv utrum singularis obestämd nominativ",
    "PC.AN": "particip förkortning",
    "PC.PRF.MAS.SIN.DEF.GEN": "particip perfekt maskulinum singularis bestämd genitiv",
    "PC.PRF.MAS.SIN.DEF.NOM": "particip perfekt maskulinum singularis bestämd nominativ",
    "PC.PRF.NEU.SIN.IND.NOM": "particip perfekt neutrum singularis obestämd nominativ",
    "PC.PRF.UTR.SIN.IND.GEN": "particip perfekt utrum singularis obestämd genitiv",
    "PC.PRF.UTR.SIN.IND.NOM": "particip perfekt utrum singularis obestämd nominativ",
    "PC.PRF.UTR+NEU.PLU.IND+DEF.GEN": "particip perfekt utrum/neutrum pluralis obestämd/bestämd genitiv",
    "PC.PRF.UTR+NEU.PLU.IND+DEF.NOM": "particip perfekt utrum/neutrum pluralis obestämd/bestämd nominativ",
    "PC.PRF.UTR+NEU.SIN.DEF.GEN": "particip perfekt utrum/neutrum singularis bestämd genitiv",
    "PC.PRF.UTR+NEU.SIN.DEF.NOM": "particip perfekt utrum/neutrum singularis bestämd nominativ",
    "PC.PRS.UTR+NEU.SIN+PLU.IND+DEF.GEN": "particip presens utrum/neutrum singularis/pluralis obestämd/bestämd genitiv",
    "PC.PRS.UTR+NEU.SIN+PLU.IND+DEF.NOM": "particip presens utrum/neutrum singularis/pluralis obestämd/bestämd nominativ",
    "PL": "partikel",
    "PL.SMS": "partikel sammansättningsform",
    "PM.GEN": "egennamn genitiv",
    "PM.NOM": "egennamn nominativ",
    "PM.SMS": "egennamn sammansättningsform",
    "PN.MAS.SIN.DEF.SUB+OBJ": "pronomen maskulinum singularis bestämd subjektsform/objektsform",
    "PN.NEU.SIN.DEF.SUB+OBJ": "pronomen neutrum singularis bestämd subjektsform/objektsform",
    "PN.NEU.SIN.IND.SUB+OBJ": "pronomen neutrum singularis obestämd subjektsform/objektsform",
    "PN.UTR.PLU.DEF.OBJ": "pronomen utrum pluralis bestämd objektsform",
    "PN.UTR.PLU.DEF.SUB": "pronomen utrum pluralis bestämd subjektsform",
    "PN.UTR.SIN.DEF.OBJ": "pronomen utrum singularis bestämd objektsform",
    "PN.UTR.SIN.DEF.SUB": "pronomen utrum singularis bestämd subjektsform",
    "PN.UTR.SIN.DEF.SUB+OBJ": "pronomen utrum singularis bestämd subjektsform/objektsform",
    "PN.UTR.SIN.IND.SUB": "pronomen utrum singularis obestämd subjektsform",
    "PN.UTR.SIN.IND.SUB+OBJ": "pronomen utrum singularis obestämd subjektsform/objektsform",
    "PN.UTR+NEU.PLU.DEF.OBJ": "pronomen utrum/neutrum pluralis bestämd objektsform",
    "PN.UTR+NEU.PLU.DEF.SUB": "pronomen utrum/neutrum pluralis bestämd subjektsform",
    "PN.UTR+NEU.PLU.DEF.SUB+OBJ": "pronomen utrum/neutrum pluralis bestämd subjektsform/objektsform",
    "PN.UTR+NEU.PLU.IND.SUB+OBJ": "pronomen utrum/neutrum pluralis obestämd subjektsform/objektsform",
    "PN.UTR+NEU.SIN+PLU.DEF.OBJ": "pronomen utrum/neutrum singularis/pluralis bestämd objektsform",
    "PP": "preposition",
    "PP.AN": "preposition förkortning",
    "PP.SMS": "preposition sammansättningsforms",
    "PS.AN": "possesivt pronomen förkortning",
    "PS.NEU.SIN.DEF": "possesivt pronomen neutrum singularis bestämd",
    "PS.UTR.SIN.DEF": "possesivt pronomen utrum singularis bestämd",
    "PS.UTR+NEU.PLU.DEF": "possesivt pronomen utrum/neutrum pluralis bestämd",
    "PS.UTR+NEU.SIN+PLU.DEF": "possesivt pronomen utrum/neutrum singularis/pluralis bestämd",
    "RG.GEN": "grundtal genitiv",
    "RG.MAS.SIN.DEF.NOM": "grundtal singularis bestämd nominativ",
    "RG.NEU.SIN.IND.NOM": "grundtal neutrum singularis obestämd nominativ",
    "RG.NOM": "grundtal nominativ",
    "RG.SMS": "grundtal sammansättningsform",
    "RG.UTR.SIN.IND.NOM": "grundtal utrum singularis obestämd nominativ",
    "RG.UTR+NEU.SIN.DEF.NOM": "grundtal utrum/neutrum singularis bestämd nominativ",
    "RO.GEN": "ordningstal genitiv",
    "RO.MAS.SIN.IND+DEF.GEN": "ordningstal maskulinum singularis obestämd/bestämd genitiv",
    "RO.MAS.SIN.IND+DEF.NOM": "ordningstal maskulinum singularis obestämd/bestämd nominativ",
    "RO.NOM": "ordningstal nominativ",
    "RO.UTR+NEU.SIN+PLU.IND+DEF.SMS": "ordningstal utrum/neutrum singularis/pluralis obestämd/bestämd sammansättningsform",
    "SN": "subjunktion",
    "UO": "utländskt ord",
    "VB.AN": "verb förkortning",
    "VB.IMP.AKT": "verb imperativ aktiv",
    "VB.IMP.SFO": "verb imperativ s-form",
    "VB.INF.AKT": "verb infinitiv aktiv",
    "VB.INF.SFO": "verb infinitiv s-form",
    "VB.KON.PRS.AKT": "verb konjunktiv presens aktiv",
    "VB.KON.PRT.AKT": "verb konjunktiv preteritum aktiv",
    "VB.KON.PRT.SFO": "verb konjunktiv preteritum s-form",
    "VB.PRS.AKT": "verb presens aktiv",
    "VB.PRS.SFO": "verb presens s-form",
    "VB.PRT.AKT": "verb preteritum aktiv",
    "VB.PRT.SFO": "verb preteritum s-form",
    "VB.SMS": "verb sammansättningsform",
    "VB.SUP.AKT": "verb supinum aktiv",
    "VB.SUP.SFO": "verb supinum s-form",
}

# This is automatically created from Saldo by saldo.saldo_model.extract_tags()
_saldo_tags = {
    "ab c",
    "ab invar",
    "ab komp",
    "ab pos",
    "ab sms",
    "ab super",
    "aba invar",
    "abh c",
    "abh invar",
    "abh sms",
    "abm invar",
    "al pl def",
    "al pl indef",
    "al sg n def",
    "al sg n indef",
    "al sg u def",
    "al sg u indef",
    "av c",
    "av invar",
    "av komp gen",
    "av komp nom",
    "av pos def pl gen",
    "av pos def pl nom",
    "av pos def sg masc gen",
    "av pos def sg masc nom",
    "av pos def sg no_masc gen",
    "av pos def sg no_masc nom",
    "av pos indef pl gen",
    "av pos indef pl nom",
    "av pos indef sg n gen",
    "av pos indef sg n nom",
    "av pos indef sg u gen",
    "av pos indef sg u nom",
    "av sms",
    "av super def masc gen",
    "av super def masc nom",
    "av super def no_masc gen",
    "av super def no_masc nom",
    "av super indef gen",
    "av super indef nom",
    "ava c",
    "ava invar",
    "ava sms",
    "avh c",
    "avh komp gen",
    "avh komp nom",
    "avh pos def pl gen",
    "avh pos def pl nom",
    "avh pos def sg masc gen",
    "avh pos def sg masc nom",
    "avh pos def sg no_masc gen",
    "avh pos def sg no_masc nom",
    "avh pos indef pl gen",
    "avh pos indef pl nom",
    "avh pos indef sg n gen",
    "avh pos indef sg n nom",
    "avh pos indef sg u gen",
    "avh pos indef sg u nom",
    "avh sms",
    "avh super def masc gen",
    "avh super def masc nom",
    "avh super def no_masc gen",
    "avh super def no_masc nom",
    "avh super indef gen",
    "avh super indef nom",
    "avm c",
    "avm invar",
    "avm komp nom",
    "avm pos def pl gen",
    "avm pos def pl nom",
    "avm pos def sg masc gen",
    "avm pos def sg masc nom",
    "avm pos def sg no_masc gen",
    "avm pos def sg no_masc nom",
    "avm pos indef pl gen",
    "avm pos indef pl nom",
    "avm pos indef sg n gen",
    "avm pos indef sg n nom",
    "avm pos indef sg u gen",
    "avm pos indef sg u nom",
    "avm sms",
    "avm super def masc nom",
    "avm super def no_masc nom",
    "avm super indef nom",
    "in invar",
    "inm invar",
    "kn invar",
    "kna c",
    "kna invar",
    "kna sms",
    "mxc c",
    "mxc sms",
    "nl c",
    "nl gen num n",
    "nl gen num u",
    "nl gen ord masc",
    "nl gen ord no_masc",
    "nl nom num n",
    "nl nom num u",
    "nl nom ord masc",
    "nl nom ord no_masc",
    "nlm c",
    "nlm invar",
    "nlm sms",
    "nn n ci",
    "nn n cm",
    "nn n pl def gen",
    "nn n pl def nom",
    "nn n pl indef gen",
    "nn n pl indef nom",
    "nn n sg def gen",
    "nn n sg def nom",
    "nn n sg indef gen",
    "nn n sg indef nom",
    "nn n sms",
    "nn p ci",
    "nn p cm",
    "nn p pl def gen",
    "nn p pl def nom",
    "nn p pl indef gen",
    "nn p pl indef nom",
    "nn p sms",
    "nn u ci",
    "nn u cm",
    "nn u pl def gen",
    "nn u pl def nom",
    "nn u pl indef gen",
    "nn u pl indef nom",
    "nn u sg def gen",
    "nn u sg def nom",
    "nn u sg indef gen",
    "nn u sg indef nom",
    "nn u sms",
    "nn v ci",
    "nn v cm",
    "nn v pl def gen",
    "nn v pl def nom",
    "nn v pl indef gen",
    "nn v pl indef nom",
    "nn v sg def gen",
    "nn v sg def nom",
    "nn v sg indef gen",
    "nn v sg indef nom",
    "nn v sms",
    "nna n ci",
    "nna n cm",
    "nna n pl def gen",
    "nna n pl def nom",
    "nna n pl indef gen",
    "nna n pl indef nom",
    "nna n sg def gen",
    "nna n sg def nom",
    "nna n sg indef gen",
    "nna n sg indef nom",
    "nna n sms",
    "nna u ci",
    "nna u cm",
    "nna u pl def gen",
    "nna u pl def nom",
    "nna u pl indef gen",
    "nna u pl indef nom",
    "nna u sg def gen",
    "nna u sg def nom",
    "nna u sg indef gen",
    "nna u sg indef nom",
    "nna u sms",
    "nna v ci",
    "nna v cm",
    "nna v pl def gen",
    "nna v pl def nom",
    "nna v pl indef gen",
    "nna v pl indef nom",
    "nna v sg def gen",
    "nna v sg def nom",
    "nna v sg indef gen",
    "nna v sg indef nom",
    "nna v sms",
    "nnh n sg def gen",
    "nnh n sg def nom",
    "nnh u ci",
    "nnh u cm",
    "nnh u pl def gen",
    "nnh u pl def nom",
    "nnh u pl indef gen",
    "nnh u pl indef nom",
    "nnh u sg def gen",
    "nnh u sg def nom",
    "nnh u sg indef gen",
    "nnh u sg indef nom",
    "nnh u sms",
    "nnm n ci",
    "nnm n cm",
    "nnm n pl def gen",
    "nnm n pl def nom",
    "nnm n pl indef gen",
    "nnm n pl indef nom",
    "nnm n sg def gen",
    "nnm n sg def nom",
    "nnm n sg indef gen",
    "nnm n sg indef nom",
    "nnm n sms",
    "nnm p pl def gen",
    "nnm p pl def nom",
    "nnm p pl indef gen",
    "nnm p pl indef nom",
    "nnm u ci",
    "nnm u cm",
    "nnm u pl def gen",
    "nnm u pl def nom",
    "nnm u pl indef gen",
    "nnm u pl indef nom",
    "nnm u sg def gen",
    "nnm u sg def nom",
    "nnm u sg indef gen",
    "nnm u sg indef nom",
    "nnm u sms",
    "nnm v ci",
    "nnm v cm",
    "nnm v pl def gen",
    "nnm v pl def nom",
    "nnm v pl indef gen",
    "nnm v pl indef nom",
    "nnm v sg def gen",
    "nnm v sg def nom",
    "nnm v sg indef gen",
    "nnm v sg indef nom",
    "nnm v sms",
    "pm f ph ci",
    "pm f ph cm",
    "pm f ph gen",
    "pm f ph nom",
    "pm f ph pl def gen",
    "pm f ph pl def nom",
    "pm f ph pl indef gen",
    "pm f ph pl indef nom",
    "pm f ph sg def gen",
    "pm f ph sg def nom",
    "pm f ph sg indef gen",
    "pm f ph sg indef nom",
    "pm f ph sms",
    "pm f pm ci",
    "pm f pm cm",
    "pm f pm gen",
    "pm f pm nom",
    "pm f pm pl def gen",
    "pm f pm pl def nom",
    "pm f pm pl indef gen",
    "pm f pm pl indef nom",
    "pm f pm sg def gen",
    "pm f pm sg def nom",
    "pm f pm sg indef gen",
    "pm f pm sg indef nom",
    "pm f pm sms",
    "pm h ph ci",
    "pm h ph cm",
    "pm h ph gen",
    "pm h ph nom",
    "pm h ph pl def gen",
    "pm h ph pl def nom",
    "pm h ph pl indef gen",
    "pm h ph pl indef nom",
    "pm h ph sg def gen",
    "pm h ph sg def nom",
    "pm h ph sg indef gen",
    "pm h ph sg indef nom",
    "pm h ph sms",
    "pm m ph ci",
    "pm m ph cm",
    "pm m ph gen",
    "pm m ph nom",
    "pm m ph pl def gen",
    "pm m ph pl def nom",
    "pm m ph pl indef gen",
    "pm m ph pl indef nom",
    "pm m ph sg def gen",
    "pm m ph sg def nom",
    "pm m ph sg indef gen",
    "pm m ph sg indef nom",
    "pm m ph sms",
    "pm m pm gen",
    "pm m pm nom",
    "pm n aa gen",
    "pm n aa nom",
    "pm n ac gen",
    "pm n ac nom",
    "pm n ap gen",
    "pm n ap nom",
    "pm n aw gen",
    "pm n aw nom",
    "pm n es gen",
    "pm n es nom",
    "pm n la gen",
    "pm n la nom",
    "pm n lf gen",
    "pm n lf nom",
    "pm n lg gen",
    "pm n lg nom",
    "pm n lp gen",
    "pm n lp nom",
    "pm n oa gen",
    "pm n oa nom",
    "pm n oc gen",
    "pm n oc nom",
    "pm n oe gen",
    "pm n oe nom",
    "pm n og gen",
    "pm n og nom",
    "pm n op gen",
    "pm n op nom",
    "pm n os gen",
    "pm n os nom",
    "pm n wm gen",
    "pm n wm nom",
    "pm n wp gen",
    "pm n wp nom",
    "pm p lg gen",
    "pm p lg nom",
    "pm p oc gen",
    "pm p oc nom",
    "pm u aa gen",
    "pm u aa nom",
    "pm u ae gen",
    "pm u ae nom",
    "pm u ag gen",
    "pm u ag nom",
    "pm u ap gen",
    "pm u ap nom",
    "pm u eh gen",
    "pm u eh nom",
    "pm u la gen",
    "pm u la nom",
    "pm u lf gen",
    "pm u lf nom",
    "pm u lg gen",
    "pm u lg nom",
    "pm u ls gen",
    "pm u ls nom",
    "pm u oc gen",
    "pm u oc nom",
    "pm u oe gen",
    "pm u oe nom",
    "pm u og gen",
    "pm u og nom",
    "pm u op gen",
    "pm u op nom",
    "pm u pa gen",
    "pm u pa nom",
    "pm u pc gen",
    "pm u pc nom",
    "pm u pm gen",
    "pm u pm nom",
    "pm u tz gen",
    "pm u tz nom",
    "pm u wa gen",
    "pm u wa nom",
    "pm u wb gen",
    "pm u wb nom",
    "pm u wc gen",
    "pm u wc nom",
    "pm u wn gen",
    "pm u wn nom",
    "pm v lf gen",
    "pm v lf nom",
    "pm v lg gen",
    "pm v lg nom",
    "pma h ph gen",
    "pma h ph nom",
    "pma n aa gen",
    "pma n aa nom",
    "pma n af gen",
    "pma n af nom",
    "pma n am gen",
    "pma n am nom",
    "pma n lp gen",
    "pma n lp nom",
    "pma n oa gen",
    "pma n oa nom",
    "pma n oe gen",
    "pma n oe nom",
    "pma n og gen",
    "pma n og nom",
    "pma n om gen",
    "pma n om nom",
    "pma n op gen",
    "pma n op nom",
    "pma n os gen",
    "pma n os nom",
    "pma n tm gen",
    "pma n tm nom",
    "pma n wb gen",
    "pma n wb nom",
    "pma u wn gen",
    "pma u wn nom",
    "pma w oc gen",
    "pma w oc nom",
    "pma w ph gen",
    "pma w ph nom",
    "pma w pm gen",
    "pma w pm nom",
    "pmm f ph gen",
    "pmm f ph nom",
    "pmm f pm gen",
    "pmm f pm nom",
    "pmm h ph gen",
    "pmm h ph nom",
    "pmm m pa gen",
    "pmm m pa nom",
    "pmm m ph gen",
    "pmm m ph nom",
    "pmm m pm gen",
    "pmm m pm nom",
    "pmm n eh gen",
    "pmm n eh nom",
    "pmm n lf gen",
    "pmm n lf nom",
    "pmm n lg gen",
    "pmm n lg nom",
    "pmm n lp gen",
    "pmm n lp nom",
    "pmm n oc gen",
    "pmm n oc nom",
    "pmm n oe gen",
    "pmm n oe nom",
    "pmm n og gen",
    "pmm n og nom",
    "pmm n op gen",
    "pmm n op nom",
    "pmm n wm gen",
    "pmm n wm nom",
    "pmm n wn gen",
    "pmm n wn nom",
    "pmm p ph gen",
    "pmm p ph nom",
    "pmm p pm gen",
    "pmm p pm nom",
    "pmm u aa gen",
    "pmm u aa nom",
    "pmm u ag gen",
    "pmm u ag nom",
    "pmm u aw gen",
    "pmm u aw nom",
    "pmm u ec gen",
    "pmm u ec nom",
    "pmm u eh gen",
    "pmm u eh nom",
    "pmm u en gen",
    "pmm u en nom",
    "pmm u er gen",
    "pmm u er nom",
    "pmm u es gen",
    "pmm u es nom",
    "pmm u la gen",
    "pmm u la nom",
    "pmm u lg gen",
    "pmm u lg nom",
    "pmm u ls gen",
    "pmm u ls nom",
    "pmm u oe gen",
    "pmm u oe nom",
    "pmm u og gen",
    "pmm u og nom",
    "pmm u op gen",
    "pmm u op nom",
    "pmm u tb gen",
    "pmm u tb nom",
    "pmm u tm gen",
    "pmm u tm nom",
    "pmm u wb gen",
    "pmm u wb nom",
    "pmm u wc gen",
    "pmm u wc nom",
    "pmm u wn gen",
    "pmm u wn nom",
    "pmm v lf gen",
    "pmm v lf nom",
    "pn ack",
    "pn c",
    "pn invar",
    "pn komp gen",
    "pn komp nom",
    "pn nom",
    "pn p1 pl ack",
    "pn p1 pl nom",
    "pn p1 pl poss pl",
    "pn p1 pl poss sg n",
    "pn p1 pl poss sg u",
    "pn p1 sg ack",
    "pn p1 sg nom",
    "pn p1 sg poss pl",
    "pn p1 sg poss sg n",
    "pn p1 sg poss sg u",
    "pn p2 pl ack",
    "pn p2 pl nom",
    "pn p2 pl poss pl",
    "pn p2 pl poss sg n",
    "pn p2 pl poss sg u",
    "pn p2 sg ack",
    "pn p2 sg nom",
    "pn p2 sg poss pl",
    "pn p2 sg poss sg n",
    "pn p2 sg poss sg u",
    "pn p3 pl ack",
    "pn p3 pl nom",
    "pn p3 pl poss pl",
    "pn p3 pl poss sg n",
    "pn p3 pl poss sg u",
    "pn p3 sg ack",
    "pn p3 sg nom",
    "pn p3 sg poss pl",
    "pn p3 sg poss sg n",
    "pn p3 sg poss sg u",
    "pn pl gen",
    "pn pl nom",
    "pn pos def pl gen",
    "pn pos def pl nom",
    "pn pos def sg masc gen",
    "pn pos def sg masc nom",
    "pn pos def sg no_masc gen",
    "pn pos def sg no_masc nom",
    "pn pos indef pl gen",
    "pn pos indef pl nom",
    "pn pos indef sg n gen",
    "pn pos indef sg n nom",
    "pn pos indef sg u gen",
    "pn pos indef sg u nom",
    "pn poss pl",
    "pn poss sg n",
    "pn poss sg u",
    "pn sg n gen",
    "pn sg n nom",
    "pn sg u gen",
    "pn sg u nom",
    "pn sms",
    "pn super def masc gen",
    "pn super def masc nom",
    "pn super def no_masc gen",
    "pn super def no_masc nom",
    "pn super indef gen",
    "pn super indef nom",
    "pnm gen",
    "pnm invar",
    "pnm nom",
    "pp invar",
    "ppa c",
    "ppa invar",
    "ppa sms",
    "ppm c",
    "ppm invar",
    "ppm sms",
    "sn invar",
    "snm c",
    "snm invar",
    "snm sms",
    "ssm c",
    "ssm invar",
    "ssm sms",
    "sxc c",
    "sxc sms",
    "vb c",
    "vb imper",
    "vb inf aktiv",
    "vb inf s-form",
    "vb pres ind aktiv",
    "vb pres ind s-form",
    "vb pres konj aktiv",
    "vb pres konj s-form",
    "vb pres_part gen",
    "vb pres_part nom",
    "vb pret ind aktiv",
    "vb pret ind s-form",
    "vb pret konj aktiv",
    "vb pret konj s-form",
    "vb pret_part def pl gen",
    "vb pret_part def pl nom",
    "vb pret_part def sg masc gen",
    "vb pret_part def sg masc nom",
    "vb pret_part def sg no_masc gen",
    "vb pret_part def sg no_masc nom",
    "vb pret_part indef pl gen",
    "vb pret_part indef pl nom",
    "vb pret_part indef sg n gen",
    "vb pret_part indef sg n nom",
    "vb pret_part indef sg u gen",
    "vb pret_part indef sg u nom",
    "vb sms",
    "vb sup aktiv",
    "vb sup s-form",
    "vba c",
    "vba invar",
    "vba sms",
    "vbm imper",
    "vbm inf aktiv",
    "vbm inf s-form",
    "vbm pres ind aktiv",
    "vbm pres ind s-form",
    "vbm pres konj aktiv",
    "vbm pres konj s-form",
    "vbm pres_part gen",
    "vbm pres_part nom",
    "vbm pret ind aktiv",
    "vbm pret ind s-form",
    "vbm pret konj aktiv",
    "vbm pret konj s-form",
    "vbm pret_part def pl gen",
    "vbm pret_part def pl nom",
    "vbm pret_part def sg masc gen",
    "vbm pret_part def sg masc nom",
    "vbm pret_part def sg no_masc gen",
    "vbm pret_part def sg no_masc nom",
    "vbm pret_part indef pl gen",
    "vbm pret_part indef pl nom",
    "vbm pret_part indef sg n gen",
    "vbm pret_part indef sg n nom",
    "vbm pret_part indef sg u gen",
    "vbm pret_part indef sg u nom",
    "vbm sup aktiv",
    "vbm sup s-form",
}

# Mapping from SALDO POS tags (as found in lemgrams) to SUC POS tags
_saldo_pos_to_suc = {
    "nn": ["NN"],
    "av": ["JJ"],
    "vb": ["VB"],
    "pm": ["PM"],
    "ab": ["AB"],
    "in": ["IN"],
    "pp": ["PP"],
    "pn": ["PN"],
    "sn": ["SN"],
    "kn": ["KN"],
    "ie": ["IE"],
    "abh": ["AB"],
    "nnm": ["NN"],
    "nna": ["NN"],
    "avh": ["JJ"],
    "avm": ["JJ"],
    "ava": ["JJ"],
    "vbm": ["VB"],
    "pmm": ["PM"],
    "abm": ["AB"],
    "aba": ["AB"],
    "pnm": ["PN"],
    "inm": ["IN"],
    "ppm": ["PP"],
    "ppa": ["PP"],
    "knm": ["KN"],
    "kna": ["KN"],
    "snm": ["SN"],
    "nl": ["RG", "RO"],
    "nlm": ["RG", "RO"],
    "al": ["DT"],
    "pma": ["PM"],
}

_suc_to_parole = {
    "AB": "RG0S",
    "AB.AN": "RG0A",
    "AB.KOM": "RGCS",
    "AB.POS": "RGPS",
    "AB.SMS": "RG0C",
    "AB.SUV": "RGSS",
    "MAD": "FE",
    "MID": "FI",
    "PAD": "FP",
    "DT.AN": "D0@00@A",
    "DT.MAS.SIN.DEF": "DF@MS@S",
    "DT.MAS.SIN.IND": "DI@MS@S",
    "DT.NEU.SIN.DEF": "DF@NS@S",
    "DT.NEU.SIN.IND": "DI@NS@S",
    "DT.NEU.SIN.IND+DEF": "D0@NS@S",
    "DT.UTR.SIN.DEF": "DF@US@S",
    "DT.UTR.SIN.IND": "DI@US@S",
    "DT.UTR.SIN.IND+DEF": "D0@US@S",
    "DT.UTR+NEU.PLU.DEF": "DF@0P@S",
    "DT.UTR+NEU.PLU.IND": "DI@0P@S",
    "DT.UTR+NEU.PLU.IND+DEF": "D0@0P@S",
    "DT.UTR+NEU.SIN.DEF": "DF@0S@S",
    "DT.UTR+NEU.SIN.IND": "DI@0S@S",
    "DT.UTR+NEU.SIN+PLU.IND": "DI@00@S",
    "HA": "RH0S",
    "HD.NEU.SIN.IND": "DH@NS@S",
    "HD.UTR.SIN.IND": "DH@US@S",
    "HD.UTR+NEU.PLU.IND": "DH@0P@S",
    "HP.-.-.-": "PH@000@S",
    "HP.NEU.SIN.IND": "PH@NS0@S",
    "HP.NEU.SIN.IND.SMS": "PH@NS0@C",
    "HP.UTR.SIN.IND": "PH@US0@S",
    "HP.UTR+NEU.PLU.IND": "PH@0P0@S",
    "HS.DEF": "PE@000@S",
    "IE": "CIS",
    "IN": "I",
    "JJ.AN": "AQ00000A",
    "JJ.KOM.UTR+NEU.SIN+PLU.IND+DEF.GEN": "AQC00G0S",
    "JJ.KOM.UTR+NEU.SIN+PLU.IND+DEF.NOM": "AQC00N0S",
    "JJ.KOM.UTR+NEU.SIN+PLU.IND+DEF.SMS": "AQC0000C",
    "JJ.POS.MAS.SIN.DEF.GEN": "AQPMSGDS",
    "JJ.POS.MAS.SIN.DEF.NOM": "AQPMSNDS",
    "JJ.POS.NEU.SIN.IND.GEN": "AQPNSGIS",
    "JJ.POS.NEU.SIN.IND.NOM": "AQPNSNIS",
    "JJ.POS.NEU.SIN.IND+DEF.NOM": "AQPNSN0S",
    "JJ.POS.UTR.-.-.SMS": "AQPU000C",
    "JJ.POS.UTR.SIN.IND.GEN": "AQPUSGIS",
    "JJ.POS.UTR.SIN.IND.NOM": "AQPUSNIS",
    "JJ.POS.UTR.SIN.IND+DEF.NOM": "AQPUSN0S",
    "JJ.POS.UTR+NEU.-.-.SMS": "AQP0000C",
    "JJ.POS.UTR+NEU.PLU.IND.NOM": "AQP0PNIS",
    "JJ.POS.UTR+NEU.PLU.IND+DEF.GEN": "AQP0PG0S",
    "JJ.POS.UTR+NEU.PLU.IND+DEF.NOM": "AQP0PN0S",
    "JJ.POS.UTR+NEU.SIN.DEF.GEN": "AQP0SGDS",
    "JJ.POS.UTR+NEU.SIN.DEF.NOM": "AQP0SNDS",
    "JJ.POS.UTR+NEU.SIN+PLU.IND.NOM": "AQP00NIS",
    "JJ.POS.UTR+NEU.SIN+PLU.IND+DEF.NOM": "AQP00N0S",
    "JJ.SUV.MAS.SIN.DEF.GEN": "AQSMSGDS",
    "JJ.SUV.MAS.SIN.DEF.NOM": "AQSMSNDS",
    "JJ.SUV.UTR+NEU.PLU.DEF.NOM": "AQS0PNDS",
    "JJ.SUV.UTR+NEU.PLU.IND.NOM": "AQS0PNIS",
    "JJ.SUV.UTR+NEU.SIN+PLU.DEF.NOM": "AQS00NDS",
    "JJ.SUV.UTR+NEU.SIN+PLU.IND.NOM": "AQS00NIS",
    "KN": "CCS",
    "KN.AN": "CCA",
    "NN.-.-.-.-": "NC000@0S",
    "NN.-.-.-.SMS": "NC000@0C",
    "NN.AN": "NC000@0A",
    "NN.NEU.-.-.-": "NCN00@0S",
    "NN.NEU.-.-.SMS": "NCN00@0C",
    "NN.NEU.PLU.DEF.GEN": "NCNPG@DS",
    "NN.NEU.PLU.DEF.NOM": "NCNPN@DS",
    "NN.NEU.PLU.IND.GEN": "NCNPG@IS",
    "NN.NEU.PLU.IND.NOM": "NCNPN@IS",
    "NN.NEU.SIN.DEF.GEN": "NCNSG@DS",
    "NN.NEU.SIN.DEF.NOM": "NCNSN@DS",
    "NN.NEU.SIN.IND.GEN": "NCNSG@IS",
    "NN.NEU.SIN.IND.NOM": "NCNSN@IS",
    "NN.UTR.-.-.-": "NCU00@0S",
    "NN.UTR.-.-.SMS": "NCU00@0C",
    "NN.UTR.PLU.DEF.GEN": "NCUPG@DS",
    "NN.UTR.PLU.DEF.NOM": "NCUPN@DS",
    "NN.UTR.PLU.IND.GEN": "NCUPG@IS",
    "NN.UTR.PLU.IND.NOM": "NCUPN@IS",
    "NN.UTR.SIN.DEF.GEN": "NCUSG@DS",
    "NN.UTR.SIN.DEF.NOM": "NCUSN@DS",
    "NN.UTR.SIN.IND.GEN": "NCUSG@IS",
    "NN.UTR.SIN.IND.NOM": "NCUSN@IS",
    "PC.AN": "AF00000A",
    "PC.PRF.MAS.SIN.DEF.GEN": "AF0MSGDS",
    "PC.PRF.MAS.SIN.DEF.NOM": "AF0MSNDS",
    "PC.PRF.NEU.SIN.IND.NOM": "AF0NSNIS",
    "PC.PRF.UTR.SIN.IND.GEN": "AF0USGIS",
    "PC.PRF.UTR.SIN.IND.NOM": "AF0USNIS",
    "PC.PRF.UTR+NEU.PLU.IND+DEF.GEN": "AF00PG0S",
    "PC.PRF.UTR+NEU.PLU.IND+DEF.NOM": "AF00PN0S",
    "PC.PRF.UTR+NEU.SIN.DEF.GEN": "AF00SGDS",
    "PC.PRF.UTR+NEU.SIN.DEF.NOM": "AF00SNDS",
    "PC.PRS.UTR+NEU.SIN+PLU.IND+DEF.GEN": "AP000G0S",
    "PC.PRS.UTR+NEU.SIN+PLU.IND+DEF.NOM": "AP000N0S",
    "PL": "QS",
    "PL.SMS": "QC",
    "PM.GEN": "NP00G@0S",
    "PM.NOM": "NP00N@0S",
    "PM.SMS": "NP000@0C",
    "PN.MAS.SIN.DEF.SUB+OBJ": "PF@MS0@S",
    "PN.NEU.SIN.DEF.SUB+OBJ": "PF@NS0@S",
    "PN.NEU.SIN.IND.SUB+OBJ": "PI@NS0@S",
    "PN.UTR.PLU.DEF.OBJ": "PF@UPO@S",
    "PN.UTR.PLU.DEF.SUB": "PF@UPS@S",
    "PN.UTR.SIN.DEF.OBJ": "PF@USO@S",
    "PN.UTR.SIN.DEF.SUB": "PF@USS@S",
    "PN.UTR.SIN.DEF.SUB+OBJ": "PF@US0@S",
    "PN.UTR.SIN.IND.SUB": "PI@USS@S",
    "PN.UTR.SIN.IND.SUB+OBJ": "PI@US0@S",
    "PN.UTR+NEU.PLU.DEF.OBJ": "PF@0PO@S",
    "PN.UTR+NEU.PLU.DEF.SUB": "PF@0PS@S",
    "PN.UTR+NEU.PLU.DEF.SUB+OBJ": "PF@0P0@S",
    "PN.UTR+NEU.PLU.IND.SUB+OBJ": "PI@0P0@S",
    "PN.UTR+NEU.SIN+PLU.DEF.OBJ": "PF@00O@S",
    "PP": "SPS",
    "PP.AN": "SPA",
    "PP.SMS": "SPC",
    "PS.AN": "PS@000@A",
    "PS.NEU.SIN.DEF": "PS@NS0@S",
    "PS.UTR.SIN.DEF": "PS@US0@S",
    "PS.UTR+NEU.PLU.DEF": "PS@0P0@S",
    "PS.UTR+NEU.SIN+PLU.DEF": "PS@000@S",
    "RG.GEN": "MC00G0S",
    "RG.MAS.SIN.DEF.NOM": "MCMSNDS",
    "RG.NEU.SIN.IND.NOM": "MCNSNIS",
    "RG.NOM": "MC00N0S",
    "RG.SMS": "MC0000C",
    "RG.UTR.SIN.IND.NOM": "MCUSNIS",
    "RG.UTR+NEU.SIN.DEF.NOM": "MC0SNDS",
    "RO.GEN": "MO00G0S",
    "RO.MAS.SIN.IND+DEF.GEN": "MOMSG0S",
    "RO.MAS.SIN.IND+DEF.NOM": "MOMSN0S",
    "RO.NOM": "MO00N0S",
    "RO.UTR+NEU.SIN+PLU.IND+DEF.SMS": "MO0000C",
    "SN": "CSS",
    "UO": "XF",
    "VB.AN": "V@000A",
    "VB.IMP.AKT": "V@M0AS",
    "VB.IMP.SFO": "V@M0SS",
    "VB.INF.AKT": "V@N0AS",
    "VB.INF.SFO": "V@N0SS",
    "VB.KON.PRS.AKT": "V@SPAS",
    "VB.KON.PRT.AKT": "V@SIAS",
    "VB.KON.PRT.SFO": "V@SISS",
    "VB.PRS.AKT": "V@IPAS",
    "VB.PRS.SFO": "V@IPSS",
    "VB.PRT.AKT": "V@IIAS",
    "VB.PRT.SFO": "V@IISS",
    "VB.SMS": "V@000C",
    "VB.SUP.AKT": "V@IUAS",
    "VB.SUP.SFO": "V@IUSS",
}

# This mapping, courtesy of Eva Forsbom
_granska_to_parole = {
    "pc.an": "AF00000A",
    "pc.prf.utr+neu.plu.ind+def.gen": "AF00PG0S",
    "pc.prf.utr+neu.plu.ind+def.nom": "AF00PN0S",
    "pc.prf.utr+neu.sin.def.gen": "AF00SGDS",
    "pc.prf.utr+neu.sin.def.nom": "AF00SNDS",
    "pc.prf.mas.sin.def.gen": "AF0MSGDS",
    "pc.prf.mas.sin.def.nom": "AF0MSNDS",
    "pc.prf.neu.sin.ind.nom": "AF0NSNIS",
    "pc.prf.utr.sin.ind.gen": "AF0USGIS",
    "pc.prf.utr.sin.ind.nom": "AF0USNIS",
    "pc.prs.utr+neu.sin+plu.ind+def.gen": "AP000G0S",
    "pc.prs.utr+neu.sin+plu.ind+def.nom": "AP000N0S",
    "jj.an": "AQ00000A",
    "jj.kom.utr+neu.sin+plu.ind+def.sms": "AQC0000C",
    "jj.kom.utr+neu.sin+plu.ind+def.gen": "AQC00G0S",
    "jj.kom.utr+neu.sin+plu.ind+def.nom": "AQC00N0S",
    "jj.pos.utr+neu.-.-.sms": "AQP0000C",
    "jj.pos.utr+neu.sin+plu.ind+def.nom": "AQP00N0S",
    "jj.pos.utr+neu.sin+plu.ind.nom": "AQP00NIS",
    "jj.pos.utr+neu.plu.ind+def.gen": "AQP0PG0S",
    "jj.pos.utr+neu.plu.ind+def.nom": "AQP0PN0S",
    "jj.pos.utr+neu.plu.ind.nom": "AQP0PNIS",
    "jj.pos.utr+neu.sin.def.gen": "AQP0SGDS",
    "jj.pos.utr+neu.sin.def.nom": "AQP0SNDS",
    "jj.pos.mas.sin.def.gen": "AQPMSGDS",
    "jj.pos.mas.sin.def.nom": "AQPMSNDS",
    "jj.pos.neu.sin.ind.gen": "AQPNSGIS",
    "jj.pos.neu.sin.ind+def.nom": "AQPNSN0S",
    "jj.pos.neu.sin.ind.nom": "AQPNSNIS",
    "jj.pos.utr.-.-.sms": "AQPU000C",
    "jj.pos.utr.sin.ind.gen": "AQPUSGIS",
    "jj.pos.utr.sin.ind+def.nom": "AQPUSN0S",
    "jj.pos.utr.sin.ind.nom": "AQPUSNIS",
    "jj.suv.utr+neu.sin+plu.def.nom": "AQS00NDS",
    "jj.suv.utr+neu.sin+plu.ind.nom": "AQS00NIS",
    "jj.suv.utr+neu.plu.def.nom": "AQS0PNDS",
    "jj.suv.utr+neu.plu.ind.nom": "AQS0PNIS",
    "jj.suv.mas.sin.def.gen": "AQSMSGDS",
    "jj.suv.mas.sin.def.nom": "AQSMSNDS",
    "kn.an": "CCA",
    "kn": "CCS",
    "ie": "CIS",
    "sn": "CSS",
    "dt.an": "D0@00@A",
    "dt.utr+neu.plu.ind+def": "D0@0P@S",
    "dt.neu.sin.ind+def": "D0@NS@S",
    "dt.utr.sin.ind+def": "D0@US@S",
    "dt.utr+neu.plu.def": "DF@0P@S",
    "dt.utr+neu.sin.def": "DF@0S@S",
    "dt.mas.sin.def": "DF@MS@S",
    "dt.neu.sin.def": "DF@NS@S",
    "dt.utr.sin.def": "DF@US@S",
    "hd.utr+neu.plu.ind": "DH@0P@S",
    "hd.neu.sin.ind": "DH@NS@S",
    "hd.utr.sin.ind": "DH@US@S",
    "dt.utr+neu.sin+plu.ind": "DI@00@S",
    "dt.utr+neu.plu.ind": "DI@0P@S",
    "dt.utr+neu.sin.ind": "DI@0S@S",
    "dt.mas.sin.ind": "DI@MS@S",
    "dt.neu.sin.ind": "DI@NS@S",
    "dt.utr.sin.ind": "DI@US@S",
    "mad": "FE",
    "mid": "FI",
    "pad": "FP",
    "in": "I",
    "rg.sms": "MC0000C",
    "rg.gen": "MC00G0S",
    "rg.nom": "MC00N0S",
    "rg.sin.nom": "MC00N0S",
    "rg.neu.sin.ind.nom": "MCNSNIS",
    "rg.utr.sin.ind.nom": "MCUSNIS",
    "rg.mas.sin.def.nom": "MCMSNDS",
    "rg utr.neu.sin.def.nom": "MC0SNDS",
    "ro.sms": "MO0000C",
    "ro.gen": "MO00G0S",
    "ro.nom": "MO00N0S",
    "ro.sin.nom": "MO00N0S",
    "ro.mas.sin.ind+def.gen": "MOMSG0S",
    "ro.mas.sin.ind+def.nom": "MOMSN0S",
    "nn.an": "NC000@0A",
    "nn.-.-.-.sms": "NC000@0C",
    "nn.-.-.-.-": "NC000@0S",
    "nn.neu.-.-.sms": "NCN00@0C",
    "nn.neu.-.-.-": "NCN00@0S",
    "nn.neu.plu.def.gen": "NCNPG@DS",
    "nn.neu.plu.ind.gen": "NCNPG@IS",
    "nn.neu.plu.def.nom": "NCNPN@DS",
    "nn.neu.plu.ind.nom": "NCNPN@IS",
    "nn.neu.sin.def.gen": "NCNSG@DS",
    "nn.neu.sin.ind.gen": "NCNSG@IS",
    "nn.neu.sin.def.nom": "NCNSN@DS",
    "nn.neu.sin.ind.nom": "NCNSN@IS",
    "nn.utr.-.-.sms": "NCU00@0C",
    "nn.utr.-.-.-": "NCU00@0S",
    "nn.utr.plu.def.gen": "NCUPG@DS",
    "nn.utr.plu.ind.gen": "NCUPG@IS",
    "nn.utr.plu.def.nom": "NCUPN@DS",
    "nn.utr.plu.ind.nom": "NCUPN@IS",
    "nn.utr.sin.def.gen": "NCUSG@DS",
    "nn.utr.sin.ind.gen": "NCUSG@IS",
    "nn.utr.sin.def.nom": "NCUSN@DS",
    "nn.utr.sin.def.nom.dat": "NCUSN@DS",
    "nn.utr.sin.ind.nom": "NCUSN@IS",
    "nn.utr.sin.ind.nom.dat": "NCUSN@IS",
    "pm.sms": "NP000@0C",
    "pm.gen": "NP00G@0S",
    "pm.nom": "NP00N@0S",
    "pn.utr+neu.sin+plu.def.obj": "PF@00O@S",
    "pn.utr+neu.plu.def.sub+obj": "PF@0P0@S",
    "pn.utr+neu.plu.def.obj": "PF@0PO@S",
    "pn.utr+neu.plu.def.sub": "PF@0PS@S",
    "pn.mas.sin.def.sub+obj": "PF@MS0@S",
    "pn.neu.sin.def.sub+obj": "PF@NS0@S",
    "pn.utr.plu.def.obj": "PF@UPO@S",
    "pn.utr.plu.def.sub": "PF@UPS@S",
    "pn.utr.sin.def.sub+obj": "PF@US0@S",
    "pn.utr.sin.def.obj": "PF@USO@S",
    "pn.utr.sin.def.sub": "PF@USS@S",
    "hs.def": "PE@000@S",
    "hp.-.-.-": "PH@000@S",
    "hp.utr+neu.plu.ind": "PH@0P0@S",
    "hp.neu.sin.ind.sms": "PH@NS0@C",
    "hp.neu.sin.ind": "PH@NS0@S",
    "hp.utr.sin.ind": "PH@US0@S",
    "pn.utr+neu.plu.ind.sub+obj": "PI@0P0@S",
    "pn.neu.sin.ind.sub+obj": "PI@NS0@S",
    "pn.utr.sin.ind.sub+obj": "PI@US0@S",
    "pn.utr.sin.ind.sub": "PI@USS@S",
    "ps.an": "PS@000@A",
    "ps.utr+neu.sin+plu.def": "PS@000@S",
    "ps.utr+neu.plu.def": "PS@0P0@S",
    "ps.neu.sin.def": "PS@NS0@S",
    "ps.utr.sin.def": "PS@US0@S",
    "pl": "QS",
    "pl.sms": "QC",
    "ab.an": "RG0A",
    "ab.sms": "RG0C",
    "ab": "RG0S",
    "ab.kom": "RGCS",
    "ab.pos": "RGPS",
    "ab.suv": "RGSS",
    "ha": "RH0S",
    "pp.an": "SPA",
    "pp.sms": "SPC",
    "pp": "SPS",
    "vb.an": "V@000A",
    "vb.sms": "V@000C",
    "vb.prt.akt": "V@IIAS",
    "vb.prt.akt.aux": "V@IIAS",
    "vb.prt.akt.kop": "V@IIAS",
    "vb.prt.sfo": "V@IISS",
    "vb.prt.sfo.kop": "V@IISS",
    "vb.prs.akt": "V@IPAS",
    "vb.prs.akt.aux": "V@IPAS",
    "vb.prs.akt.kop": "V@IPAS",
    "vb.prs.sfo": "V@IPSS",
    "vb.prs.sfo.kop": "V@IPSS",
    "vb.sup.akt": "V@IUAS",
    "vb.sup.akt.kop": "V@IUAS",
    "vb.sup.sfo": "V@IUSS",
    "vb.imp.akt": "V@M0AS",
    "vb.imp.akt.aux": "V@M0AS",
    "vb.imp.akt.kop": "V@M0AS",
    "vb.imp.sfo": "V@M0SS",
    "vb.inf.akt": "V@N0AS",
    "vb.inf.akt.aux": "V@N0AS",
    "vb.inf.akt.kop": "V@N0AS",
    "vb.inf.sfo": "V@N0SS",
    "vb.kon.prt.akt": "V@SIAS",
    "vb.kon.prt.sfo": "V@SISS",
    "vb.kon.prs.akt": "V@SPAS",
    "uo": "XF",
}

_granska_tags = set(_granska_to_parole)

######################################################################
# Here we automatically create the 1-many dictionaries
# saldo_to_suc and saldo_to_parole

saldo_params_to_suc = {
    "u": "UTR",
    "n": "NEU",
    "masc": "MAS",
    "no_masc": "UTR+NEU",
    "komp": "KOM",
    "super": "SUV",
    "pl": "PLU",
    "sg": "SIN",
    "indef": "IND",
    "pres_part": "PCPRS",
    "pret_part": "PCPRT",
    "imper": "IMP",
    "aktiv": "AKT",
    "s-form": "SFO",
    "ind": "INDIKATIV",
    "konj": "KON",
    "pres": "PRS",
    "pret": "PRT",
}

# fmt: off
# SALDO to SUC mapping
_suc_tag_replacements = [
    (r"(IN|KN|PP)",                   r"\1"),
    (r"SN",                           r"(SN|IE)"),  # ie doesn't exist in SALDO anymore
    (r"(AB|KN|PP|VB)A",               r"\1 AN"),
    (r"[MS]XC",                       r"(NN|JJ|AB) .* SMS"),

    (r"ABH? INVAR",                   r"(AB|PL|HA)"),
    (r"ABH? (KOM|POS|SMS|SUV)",       r"AB \1"),

    (r"AL PLU (DEF|IND)",             r"DT UTR+NEU PLU \1"),
    (r"AL SIN (UTR|NEU) (DEF|IND)",   r"DT \1 SIN \2"),

    (r"AV INVAR",                                                      r"(JJ POS|PC PRS) .* NOM"),
    (r"AVH? POS IND SIN NEU NOM",                                      r"(AB|AB POS|(JJ POS|PC PRF) NEU SIN IND NOM)"),  # snabbt
    (r"AVH? POS (DEF|IND) (SIN|PLU) (MAS|NEU|UTR|UTR\+NEU) (NOM|GEN)", r"(JJ POS|PC PRF) \3 \2 (\1|IND+DEF) \4"),  # ind/def doesn't exist in SALDO
    (r"AVH? POS (DEF|IND) PLU (NOM|GEN)",                              r"(JJ POS|PC PRF) UTR+NEU PLU (\1|IND+DEF) \2"),  # ind/def doesn't exist in SALDO
    # (r"AV POS .* (SIN|PLU) .*(NOM|GEN)",                             r"(JJ POS|PC PRF) .* \1 .* \2"),
    (r"AVH? KOM NOM",                                                  r"(JJ KOM .* NOM|AB KOM)"),
    (r"AVH? SUV IND NOM",                                              r"(JJ SUV .* NOM|AB SUV)"),
    (r"AVH? (KOM|SUV) .*(NOM|GEN)",                                    r"JJ \1 .* \2"),
    (r"AVH? SMS",                                                      r"JJ .* SMS"),
    (r"AVA",                                                           r"AB AN"),

    (r"NL (NOM|GEN)",                                 r"(RG|RO) .*\1"),

    (r"NN (V|P) (SIN|PLU) (IND|DEF) (NOM|GEN)",       r"NN (UTR|NEU|-) (\2|-) (\3|-) (\4|-)"),
    (r"NNH? (UTR|NEU) (SIN|PLU) (IND|DEF) (NOM|GEN)", r"NN (\1|-) (\2|-) (\3|-) (\4|-)"),
    (r"NNH? .* SMS",                                  r"NN .* SMS"),
    (r"NNA .* SMS",                                   r"(NN|PM) .* SMS"),
    (r"NNA .* (SIN|PLU) (IND|DEF) (NOM|GEN)",         r"NN (AN|.* \1 \2 \3)"),

    (r"PMA .* (NOM|GEN)",                           r"PM \1"),
    (r"PM .* (NOM|GEN)",                            r"PM \1"),
    (r"PM .* SMS",                                  r"PM .* SMS"),

    (r"PN .*POSS",                                  r"(PS|HS)"),
    (r"PN KOM GEN",                                 r"PS"),
    (r"PN SUV (IND|DEF)",                           r"JJ SUV .* \1"),
    (r"PN (P1|P2|P3) (SIN|PLU)",                    r"PN .* \2 DEF"),
    (r"PN POS .*(SIN|PLU)",                         r"PN .* \1"),
    (r"PN PLU NOM",                                 r"(PN .* PLU|DT UTR+NEU PLU .*|JJ POS UTR+NEU PLU .* NOM)"),
    (r"PN PLU GEN",                                 r"(PN .* PLU|DT UTR+NEU PLU .*|PS UTR+NEU SIN+PLU DEF)"),
    (r"PN SIN UTR NOM",                             r"(PN (UTR|MAS) SIN|DT UTR SIN .*|JJ POS UTR SIN IND NOM)"),
    (r"PN SIN UTR GEN",                             r"(PN (UTR|MAS) SIN|DT UTR SIN .*|PS UTR+NEU SIN+PLU DEF)"),
    (r"PN SIN NEU NOM",                             r"(PN NEU SIN|DT NEU SIN .*|JJ POS NEU SIN IND NOM)"),
    (r"PN SIN NEU GEN",                             r"(PN NEU SIN|DT NEU SIN .*|PS UTR+NEU SIN+PLU DEF)"),
    (r"PN (ACK|NOM|INVAR|KOM|SMS)",                 r"(PN|HP|HS)"),

    (r"VB (INF|SUP) (AKT|SFO)",                     r"VB \1 \2"),
    (r"VB (PRS|PRT) .* (AKT|SFO)",                  r"VB .*\1 \2"),
    (r"VB PCPRS (NOM|GEN)",                         r"PC PRS .* \1"),
    (r"VB PCPRT .* (PLU|SIN) .*(NOM|GEN)",          r"PC PRF .* \1 .* \2"),
    (r"VB (IMP|SMS)",                               r"VB \1"),

    # Compounds
    (r"ABH? C", r"AB"),
    (r"AVH? C", r"JJ"),
    (r"VB C", r"VB"),
    (r"NNA? (UTR|NEU) (CI|CM)", r"NN (\1|-) - - -"),
    (r"NNA? (V|P) (CI|CM)", r"NN (UTR|NEU|-) - - -"),
    (r"NNH? (UTR|NEU) (CI|CM)", r"NN (\1|-) - - -"),

    (r"PM .* (CI|CM)", r"PM"),
    (r"PN C", r"PN"),
    (r"NL C", r"(RG|RO)"),
]
# fmt: on


def _make_saldo_to_suc(compound: bool = False) -> dict[str, set[str]]:
    """Generate SALDO to SUC tag mapping.

    Args:
        compound: Whether to include compound tags.

    Returns:
        Mapping from SALDO tags to SUC tags.

    Raises:
        Exception: If a SALDO tag cannot be mapped to a SUC tag.
    """
    tagmap = {}
    for saldo_tag in _saldo_tags:
        params = saldo_tag.split()
        if not compound:
            if (
                saldo_tag.endswith((" c", " ci", " cm"))
                or not params
                or (len(params[0]) == 3 and params[0].endswith(("m", "h")))  # noqa: PLR2004
            ):
                # Skip multiword units and compound/end syllables
                continue
        elif not params or (len(params[0]) == 3 and params[0].endswith("m")):  # noqa: PLR2004
            # Skip multiword units
            continue
        paramstr = " ".join(saldo_params_to_suc.get(prm, prm.upper()) for prm in params)
        replacement = None
        m = None
        for pre, post in _suc_tag_replacements:
            if m := re.match(pre, paramstr):
                replacement = post
                break
        if replacement is None:
            raise Exception(paramstr)
        suc_filter = m.expand(replacement).replace(" ", r"\.").replace("+", r"\+")
        tagmap[saldo_tag] = {suc_tag for suc_tag in tags.suc_tags if re.match(suc_filter, suc_tag)}
    return tagmap


class Mappings:
    """Class with methods for accessing tag mappings."""

    def __init__(self) -> None:
        """Initialise Mappings."""
        self.mappings = {}

    def __getitem__(self, item: str) -> dict:
        """Get a tag mapping through subscripting for backward compatibility.

        Args:
            item: The tag mapping to get.

        Returns:
            The tag mapping.
        """
        if item in self.mappings:
            return self.mappings[item]
        return getattr(self, item)

    @property
    def granska_to_parole(self) -> dict[str, str]:
        """Return Granska to Parole tag mapping."""
        return _granska_to_parole

    @property
    def granska_to_suc(self) -> dict[str, str]:
        """Return Granska to SUC tag mapping."""
        if "granska_to_suc" not in self.mappings:
            self.mappings["granska_to_suc"] = {
                granska: self.parole_to_suc[parole] for (granska, parole) in _granska_to_parole.items()
            }
        return self.mappings["granska_to_suc"]

    @property
    def parole_to_granska(self) -> dict[str, str]:
        """Return Parole to Granska tag mapping."""
        if "parole_to_granska" not in self.mappings:
            self.mappings["parole_to_granska"] = {}
            for granska, parole in _granska_to_parole.items():
                self.mappings["parole_to_granska"].setdefault(parole, set()).add(granska)
        return self.mappings["parole_to_granska"]

    @property
    def parole_to_suc(self) -> dict[str, str]:
        """Return Parole to SUC tag mapping."""
        if "parole_to_suc" not in self.mappings:
            self.mappings["parole_to_suc"] = {parole: suc for (suc, parole) in _suc_to_parole.items()}
        return self.mappings["parole_to_suc"]

    @property
    def saldo_to_granska(self) -> dict[str, str]:
        """Return SALDO to Granska tag mapping."""
        if "saldo_to_granska" not in self.mappings:
            self.mappings["saldo_to_granska"] = {
                saldo_tag: set().union(*(self.suc_to_granska[suc_tag] for suc_tag in suc_tags))
                for saldo_tag, suc_tags in self.saldo_to_suc.items()
            }
        return self.mappings["saldo_to_granska"]

    @property
    def saldo_to_parole(self) -> dict[str, str]:
        """Return SALDO to Parole tag mapping."""
        if "saldo_to_parole" not in self.mappings:
            self.mappings["saldo_to_parole"] = {
                saldo_tag: {_suc_to_parole[suc_tag] for suc_tag in suc_tags}
                for saldo_tag, suc_tags in self.saldo_to_suc.items()
            }
        return self.mappings["saldo_to_parole"]

    @property
    def saldo_to_saldo(self) -> dict[str, str]:
        """Return SALDO to SALDO tag mapping."""
        if "saldo_to_saldo" not in self.mappings:
            self.mappings["saldo_to_saldo"] = {saldo_tag: {saldo_tag} for saldo_tag in _saldo_tags}
        return self.mappings["saldo_to_saldo"]

    @property
    def saldo_to_suc_compound(self) -> dict[str, str]:
        """Return SALDO to SUC compund tag mapping."""
        if "saldo_to_suc_compound" not in self.mappings:
            self.mappings["saldo_to_suc_compound"] = _make_saldo_to_suc(compound=True)
        return self.mappings["saldo_to_suc_compound"]

    @property
    def saldo_to_suc(self) -> dict[str, str]:
        """Return SALDO to SUC tag mapping."""
        if "saldo_to_suc" not in self.mappings:
            self.mappings["saldo_to_suc"] = _make_saldo_to_suc()
        return self.mappings["saldo_to_suc"]

    @property
    def saldo_pos_to_suc(self) -> dict[str, str]:
        """Return SALDO pos to SUC tag mapping."""
        return _saldo_pos_to_suc

    @property
    def suc_descriptions(self) -> dict[str, str]:
        """Return SUC descriptions mapping."""
        return _suc_descriptions

    @property
    def suc_to_granska(self) -> dict[str, str]:
        """Return SUC to Granska tag mapping."""
        if "suc_to_granska" not in self.mappings:
            self.mappings["suc_to_granska"] = {
                suc: self.parole_to_granska[parole] for (suc, parole) in _suc_to_parole.items()
            }
        return self.mappings["suc_to_granska"]

    @property
    def suc_to_parole(self) -> dict[str, str]:
        """Return SUC to Parole tag mapping."""
        return _suc_to_parole

    @property
    def suc_to_simple(self) -> dict[str, str]:
        """Return SUC to SUC pos tag mapping."""
        if "suc_to_simple" not in self.mappings:
            self.mappings["suc_to_simple"] = {suc: split_tag(suc)[0] for suc in tags.suc_tags}
        return self.mappings["suc_to_simple"]

    @property
    def saldo_params_to_suc(self) -> dict[str, str]:
        """Return SALDO params to SUC tag mapping."""
        return saldo_params_to_suc


mappings = Mappings()


class Tags:
    """Class with methods for accessing tag sets."""

    def __init__(self) -> None:
        """Initialize Tags class."""
        self.tags = {
            "granska_tags": _granska_tags,
            "saldo_tags": _saldo_tags,
        }

    def __getitem__(self, item: str) -> dict:
        """Get a tag set through subscripting for backward compatibility.

        Args:
            item: The tag set to get.

        Returns:
            The tag set.
        """
        if item in self.tags:
            return self.tags[item]
        return getattr(self, item)

    @property
    def granska_tags(self) -> set[str]:
        """Return Granska tag set."""
        return self.tags["granska_tags"]

    @property
    def parole_tags(self) -> set[str]:
        """Return Parole tag set."""
        if "parole_tags" not in self.tags:
            self.tags["parole_tags"] = set(mappings.parole_to_suc)
        return self.tags["parole_tags"]

    @property
    def saldo_tags(self) -> set[str]:
        """Return SALDO tag set."""
        return self.tags["saldo_tags"]

    @property
    def simple_tags(self) -> set[str]:
        """Return SUC pos tag set."""
        if "simple_tags" not in self.tags:
            self.tags["simple_tags"] = set(mappings.suc_to_simple.values())
        return self.tags["simple_tags"]

    @property
    def suc_tags(self) -> set[str]:
        """Return SUC tag set."""
        if "suc_tags" not in self.tags:
            self.tags["suc_tags"] = set(_suc_descriptions)
        return self.tags["suc_tags"]


tags = Tags()

# assert tags.suc_tags == set(mappings.suc_to_parole.keys())
# assert tags.suc_tags == set(mappings.suc_to_granska.keys())
# assert tags.suc_tags == set(mappings.parole_to_suc.values())
# assert tags.suc_tags == set(mappings.granska_to_suc.values())
#
# assert _granska_tags == set(mappings.granska_to_parole.keys())
# assert _granska_tags == set(mappings.granska_to_suc.keys())
# assert _granska_tags == set().union(*list(mappings.parole_to_granska.values()))
# assert _granska_tags == set().union(*list(mappings.suc_to_granska.values()))
#
# assert tags.parole_tags == set(mappings.parole_to_suc.keys())
# assert tags.parole_tags == set(mappings.parole_to_granska.keys())
# assert tags.parole_tags == set(_suc_to_parole.values())
# assert tags.parole_tags == set(_granska_to_parole.values())
