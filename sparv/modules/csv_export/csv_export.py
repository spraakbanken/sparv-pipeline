"""CSV file export."""

import os

from sparv.api import (Annotation, Config, SourceFilename, Export, ExportAnnotations, SourceAnnotations, exporter, get_logger,
                       util)

logger = get_logger(__name__)


@exporter("CSV export", config=[
    Config("csv_export.delimiter", default="\t", description="Delimiter separating fields."),
    Config("csv_export.source_annotations",
           description="List of annotations and attributes from the source data to include. Everything will be "
                       "included by default."),
    Config("csv_export.annotations", description="Sparv annotations to include.")
])
def csv(source_file: SourceFilename = SourceFilename(),
        out: Export = Export("csv_export/{file}.csv"),
        token: Annotation = Annotation("<token>"),
        word: Annotation = Annotation("[export.word]"),
        sentence: Annotation = Annotation("<sentence>"),
        annotations: ExportAnnotations = ExportAnnotations("csv_export.annotations"),
        source_annotations: SourceAnnotations = SourceAnnotations("csv_export.source_annotations"),
        remove_namespaces: bool = Config("export.remove_module_namespaces", False),
        sparv_namespace: str = Config("export.sparv_namespace"),
        source_namespace: str = Config("export.source_namespace"),
        delimiter: str = Config("csv_export.delimiter")):
    """Export annotations to CSV format."""
    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    token_name = token.name

    # Read words
    word_annotation = list(word.read())

    # Get annotation spans, annotations list etc.
    annotation_list, token_attributes, export_names = util.export.get_annotation_names(
        annotations, source_annotations, source_file=source_file, token_name=token_name,
        remove_namespaces=remove_namespaces, sparv_namespace=sparv_namespace, source_namespace=source_namespace)
    if token not in annotation_list:
        logger.warning("The 'csv_export:csv' export requires the <token> annotation for the output to include "
                       "the source text. Make sure to add <token> to the list of export annotations.")
    span_positions, annotation_dict = util.export.gather_annotations(annotation_list, export_names,
                                                                     source_file=source_file)

    # Make csv header
    csv_data = [_make_header(token_name, token_attributes, export_names, delimiter)]

    # Go through spans_dict and add to csv, line by line
    for _pos, instruction, span in span_positions:
        if instruction == "open":
            # Create token line
            if span.name == token_name:
                csv_data.append(_make_token_line(word_annotation[span.index], token_name, token_attributes,
                                                 annotation_dict, span.index, delimiter))

            # Create line with structural annotation
            else:
                attrs = _make_attrs(span.name, annotation_dict, export_names, span.index)
                for attr in attrs:
                    csv_data.append(f"# {attr}")
                if not attrs:
                    csv_data.append(f"# {span.export}")

        # Insert blank line after each closing sentence
        elif span.name == sentence.name and instruction == "close":
            csv_data.append("")

    # Write result to file
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(csv_data))
    logger.info("Exported: %s", out)


def _make_header(token, token_attributes, export_names, delimiter):
    """Create a csv header containing the names of the token annotations."""
    line = [export_names.get(token, token)]
    for annot in token_attributes:
        line.append(export_names.get(":".join([token, annot]), annot))
    return delimiter.join(line)


def _make_token_line(word, token, token_attributes, annotation_dict, index, delimiter):
    """Create a line with the token and its annotations."""
    line = [word.replace(delimiter, " ")]
    for attr in token_attributes:
        if attr not in annotation_dict[token]:
            attr_str = util.constants.UNDEF
        else:
            attr_str = annotation_dict[token][attr][index]
        line.append(attr_str)
    return delimiter.join(line)


def _make_attrs(annotation, annotation_dict, export_names, index):
    """Create a list with attribute-value strings for a structural element."""
    attrs = []
    for name, annot in annotation_dict[annotation].items():
        export_name = export_names.get(":".join([annotation, name]), name)
        annotation_name = export_names.get(annotation, annotation)
        if annot[index]:
            attrs.append("%s.%s = %s" % (annotation_name, export_name, annot[index]))
    return attrs
