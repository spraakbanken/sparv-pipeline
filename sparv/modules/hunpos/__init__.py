from . import hunpos

annotations = {
    "msd": {
        "function": hunpos.msdtag,
        "type": "attribute",
        "class": None,
        "on_span_class": "token",
        "description": "Part-of-speech annotation with morphological descriptions"
    },
    "pos": {
        "function": hunpos.postag,
        "type": "attribute",
        "class": None,
        "on_span_class": "token",
        "description": "Part-of-speech annotation"
    }
}
