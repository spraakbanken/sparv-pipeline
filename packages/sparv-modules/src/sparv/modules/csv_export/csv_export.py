"""CSV file export."""

from pathlib import Path

from sparv.api import (
    Annotation,
    Config,
    Export,
    ExportAnnotations,
    SourceAnnotations,
    SourceFilename,
    exporter,
    get_logger,
    util,
)

logger = get_logger(__name__)


@exporter(
    "CSV export",
    config=[
        Config("csv_export.delimiter", default="\t", description="Delimiter separating fields.", datatype=str),
        Config(
            "csv_export.source_annotations",
            description="List of annotations and attributes from the source data to include. Everything will be "
            "included by default.",
            datatype=list[str],
        ),
        Config("csv_export.annotations", description="Sparv annotations to include.", datatype=list[str]),
    ],
)
def csv(
    source_file: SourceFilename = SourceFilename(),
    out: Export = Export("csv_export/{file}.csv"),
    token: Annotation = Annotation("<token>"),
    word: Annotation = Annotation("[export.word]"),
    sentence: Annotation = Annotation("<sentence>"),
    annotations: ExportAnnotations = ExportAnnotations("csv_export.annotations"),
    source_annotations: SourceAnnotations = SourceAnnotations("csv_export.source_annotations"),
    remove_namespaces: bool = Config("export.remove_module_namespaces", False),
    sparv_namespace: str = Config("export.sparv_namespace"),
    source_namespace: str = Config("export.source_namespace"),
    delimiter: str = Config("csv_export.delimiter"),
) -> None:
    """Export annotations to CSV format."""
    # Create export dir
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    token_name = token.name

    # Read words
    word_annotation = list(word.read())

    # Get annotation spans, annotations list etc.
    annotation_list, token_attributes, export_names = util.export.get_annotation_names(
        annotations,
        source_annotations,
        source_file=source_file,
        token_name=token_name,
        remove_namespaces=remove_namespaces,
        sparv_namespace=sparv_namespace,
        source_namespace=source_namespace,
    )
    if token not in annotation_list:
        logger.warning(
            "The 'csv_export:csv' export requires the <token> annotation for the output to include "
            "the source text. Make sure to add <token> to the list of export annotations."
        )
    span_positions, annotation_dict = util.export.gather_annotations(
        annotation_list, export_names, source_file=source_file
    )

    # Make csv header
    csv_data = [_make_header(token_name, token_attributes, export_names, delimiter)]

    # Go through spans_dict and add to csv, line by line
    for _pos, instruction, span in span_positions:
        if instruction == "open":
            # Create token line
            if span.name == token_name:
                csv_data.append(
                    _make_token_line(
                        word_annotation[span.index],
                        token_name,
                        token_attributes,
                        annotation_dict,
                        span.index,
                        delimiter,
                    )
                )

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

    # Write result to file
    out_path.write_text("\n".join(csv_data), encoding="utf-8")
    logger.info("Exported: %s", out)


def _make_header(token: str, token_attributes: list[str], export_names: dict[str, str], delimiter: str) -> str:
    """Create a csv header containing the names of the token annotations.

    Args:
        token: The token name.
        token_attributes: A list of token attributes.
        export_names: A dictionary mapping annotation names to export names.
        delimiter: The delimiter used in the CSV file.

    Returns:
        A string representing the CSV header.
    """
    line = [export_names.get(token, token)] + [
        export_names.get(f"{token}:{annot}", annot) for annot in token_attributes
    ]
    return delimiter.join(line)


def _make_token_line(
    word: str, token: str, token_attributes: list[str], annotation_dict: dict[str, dict], index: int, delimiter: str
) -> str:
    """Create a line with the token and its annotations.

    Args:
        word: The text of the token.
        token: The token name.
        token_attributes: A list of token attributes.
        annotation_dict: Dictionary with annotations.
        index: Index of the token.
        delimiter: The delimiter used in the CSV file.

    Returns:
        A string representing the CSV line for the token.
    """
    line = [word.replace(delimiter, " ")]
    for attr in token_attributes:
        attr_str = util.constants.UNDEF if attr not in annotation_dict[token] else annotation_dict[token][attr][index]
        line.append(attr_str)
    return delimiter.join(line)


def _make_attrs(
    annotation: str, annotation_dict: dict[str, dict], export_names: dict[str, str], index: int
) -> list[str]:
    """Create a list with attribute-value strings for a structural element.

    Args:
        annotation: The name of the annotation.
        annotation_dict: Dictionary with annotations.
        export_names: Dictionary mapping annotation names to export names.
        index: Index of the annotation.

    Returns:
        A list of attribute-value strings.
    """
    attrs = []
    for name, annot in annotation_dict[annotation].items():
        export_name = export_names.get(f"{annotation}:{name}", name)
        annotation_name = export_names.get(annotation, annotation)
        if annot[index]:
            attrs.append(f"{annotation_name}.{export_name} = {annot[index]}")
    return attrs
