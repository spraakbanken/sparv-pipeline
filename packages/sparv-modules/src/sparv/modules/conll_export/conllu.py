"""CoNNL-U file export (modified SBX version)."""

# ruff: noqa: PLR2004
from pathlib import Path

from sparv.api import Annotation, Config, Export, SourceAnnotations, SourceFilename, exporter, get_logger, util

logger = get_logger(__name__)


@exporter(
    "CoNLL-U (SBX version) export",
    language=["swe"],
    config=[
        Config(
            "conll_export.source_annotations",
            description="List of annotations and attributes from the source data to "
            "include. Everything will be included by default.",
            datatype=list[str],
        ),
        Config(
            "conll_export.conll_fields.sentid", default="<sentence>:misc.id", description="Sentence ID", datatype=str
        ),
        Config(
            "conll_export.conll_fields.id",
            default="<token:ref>",
            description="Annotation in ID field of CoNLL-U output",
            datatype=str,
        ),
        Config(
            "conll_export.conll_fields.lemma",
            default="<token:baseform>",
            description="Annotation in LEMMA field of CoNLL-U output",
            datatype=str,
        ),
        Config(
            "conll_export.conll_fields.upos",
            default="<token:pos>",
            description="Annotation in UPOS field of CoNLL-U output",
            datatype=str,
        ),
        Config(
            "conll_export.conll_fields.xpos",
            default="<token:msd>",
            description="Annotation in XPOS field of CoNLL-U output",
            datatype=str,
        ),
        Config(
            "conll_export.conll_fields.feats",
            default="<token:ufeats>",
            description="Annotation in FEATS field of CoNLL-U output",
            datatype=str,
        ),
        Config(
            "conll_export.conll_fields.head",
            default="<token:dephead_ref>",
            description="Annotation in HEAD field of CoNLL-U output",
            datatype=str,
        ),
        Config(
            "conll_export.conll_fields.deprel",
            default="<token:deprel>",
            description="Annotation in DEPREL field of CoNLL-U output",
            datatype=str,
        ),
        Config(
            "conll_export.conll_fields.deps", description="Annotation in DEPS field of CoNLL-U output", datatype=str
        ),
        Config(
            "conll_export.conll_fields.misc", description="Annotation in MISC field of CoNLL-U output", datatype=str
        ),
    ],
)
def conllu(
    source_file: SourceFilename = SourceFilename(),
    out: Export = Export("conll_export/{file}.conllu"),
    token: Annotation = Annotation("<token>"),
    sentence: Annotation = Annotation("<sentence>"),
    sentence_id: Annotation = Annotation("[conll_export.conll_fields.sentid]"),
    source_annotations: SourceAnnotations = SourceAnnotations("conll_export.source_annotations"),
    id_ref: Annotation | None = Annotation("[conll_export.conll_fields.id]"),
    form: Annotation | None = Annotation("[export.word]"),
    lemma: Annotation | None = Annotation("[conll_export.conll_fields.lemma]"),
    upos: Annotation | None = Annotation("[conll_export.conll_fields.upos]"),
    xpos: Annotation | None = Annotation("[conll_export.conll_fields.xpos]"),
    feats: Annotation | None = Annotation("[conll_export.conll_fields.feats]"),
    head: Annotation | None = Annotation("[conll_export.conll_fields.head]"),
    deprel: Annotation | None = Annotation("[conll_export.conll_fields.deprel]"),
    deps: Annotation | None = Annotation("[conll_export.conll_fields.deps]"),
    misc: Annotation | None = Annotation("[conll_export.conll_fields.misc]"),
) -> None:
    """Export annotations to CoNLL-U format."""
    # CoNLLU specification: https://universaldependencies.org/format.html
    # ID: Word index, integer starting at 1 for each new sentence; may be a range for multiword tokens; may be a decimal
    #     number for empty nodes (decimal numbers can be lower than 1 but must be greater than 0).
    # FORM: Word form or punctuation symbol.
    # LEMMA: Lemma or stem of word form.
    # UPOS: Universal part-of-speech tag.
    # XPOS: Language-specific part-of-speech tag; underscore if not available.
    # FEATS: List of morphological features from the universal feature inventory or from a defined language-specific
    #        extension; underscore if not available.
    # HEAD: Head of the current word, which is either a value of ID or zero (0).
    # DEPREL: Universal dependency relation to the HEAD (root iff HEAD = 0) or a defined language-specific subtype
    #         of one.
    # DEPS: Enhanced dependency graph in the form of a list of head-deprel pairs.
    # MISC: Any other annotation.
    conll_fields = [id_ref, form, lemma, upos, xpos, feats, head, deprel, deps, misc]
    conll_fields = [f if isinstance(f, Annotation) else Annotation() for f in conll_fields]

    # Create export dir
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    token_name = token.name

    # Get annotation spans, annotations list etc.
    # TODO: Add structural annotations from 'annotations'? This is a bit annoying though because then we'd have to
    # take annotations as a requirement which results in Sparv having to run all annotations, even the ones we don't
    # want to use here.
    annotations = [sentence, sentence_id, token, *conll_fields]
    annotations = [(annot, None) for annot in annotations]
    annotation_list, _, export_names = util.export.get_annotation_names(
        annotations, source_annotations, remove_namespaces=True, source_file=source_file, token_name=token_name
    )
    span_positions, annotation_dict = util.export.gather_annotations(
        annotation_list, export_names, source_file=source_file
    )

    csv_data = ["# global.columns = ID FORM LEMMA UPOS XPOS FEATS HEAD DEPREL DEPS MISC"]
    # Go through spans_dict and add to csv, line by line
    for _pos, instruction, span in span_positions:
        if instruction == "open":
            # Create token line
            if span.name == token_name:
                csv_data.append(_make_conll_token_line(conll_fields, token_name, annotation_dict, span.index))

            # Create line with structural annotation
            else:
                attrs = _make_attrs(span.name, annotation_dict, export_names, span.index)
                for attr in attrs:
                    csv_data.append(f"# {attr}")  # noqa: PERF401
                if not attrs:
                    csv_data.append(f"# {span.export}")

        # Insert blank line after each closing sentence
        elif span.name == sentence.name and instruction == "close":
            csv_data.append("")

    # Insert extra blank line to make CoNLL-U validator happy
    csv_data.append("")

    # Write result to file
    out_path.write_text("\n".join(csv_data), encoding="utf-8")
    logger.info("Exported: %s", out)


def _make_conll_token_line(
    conll_fields: list[Annotation], token: str, annotation_dict: dict[str, dict], index: int, delimiter: str = "\t"
) -> str:
    """Create a line in CoNLL-format with the token and its annotations.

    Args:
        conll_fields: List of CoNLL fields.
        token: The token name.
        annotation_dict: Dictionary with annotations.
        index: Index of the token.
        delimiter: Delimiter used in the CoNLL format (default is tab).

    Returns:
        str: A string representing the CoNLL line for the token.
    """
    line = []
    for i, annot in enumerate(conll_fields):
        if annot.attribute_name not in annotation_dict[token]:
            attr_str = "_"
        else:
            attr_str = annotation_dict[token][annot.attribute_name][index].strip("|") or "_"
        # If there are multiple lemmas, use the first one
        if i == 2:
            attr_str = util.misc.set_to_list(attr_str)[0]
        # Set head (index 6 in conll_fields) to '0' when root
        if i == 6 and attr_str == "_":
            attr_str = "0"
        # Convert deprel to lower case
        if i == 7:
            attr_str = attr_str.lower()
        line.append(attr_str)
    return delimiter.join(line)


def _make_attrs(
    annotation: str, annotation_dict: dict[str, dict], export_names: dict[str, str], index: int
) -> list[str]:
    """Create a list with attribute-value strings for a structural element.

    Args:
        annotation: The name of the annotation.
        annotation_dict: Dictionary with annotations.
        export_names: Dictionary with export names.
        index: Index of the annotation.

    Returns:
        A list of attribute-value strings.
    """
    attrs = []
    for name, annot in annotation_dict[annotation].items():
        export_name = export_names.get(f"{annotation}:{name}", name)
        annotation_name = export_names.get(annotation, annotation)
        if annotation_name == "sentence":
            annotation_name = "sent"
        attrs.append(f"{annotation_name}_{export_name} = {annot[index]}")
    return attrs
