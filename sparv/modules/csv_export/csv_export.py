"""CSV file export."""

import logging
import os
from typing import Optional

import sparv.util as util
from sparv import Annotation, Config, Document, Export, ExportAnnotations, exporter

log = logging.getLogger(__name__)


@exporter("CSV export", config=[Config("csv_export.delimiter", default="\t")])
def csv(doc: str = Document,
        out: str = Export("csv/{doc}.csv"),
        token: str = Annotation("<token>"),
        word: str = Annotation("<token:word>"),
        sentence: str = Annotation("<sentence>"),
        annotations: list = ExportAnnotations(export_type="csv_export"),
        original_annotations: Optional[list] = Config("csv_export.original_annotations"),
        remove_namespaces: bool = Config("export.remove_export_namespaces", False),
        delimiter: str = Config("csv_export.delimiter")):
    """Export annotations to CSV format."""
    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Read words
    word_annotation = list(util.read_annotation(doc, word))

    # Get annotation spans, annotations list etc.
    annotations, token_annotations, export_names = util.get_annotation_names(doc, token, annotations,
                                                                             original_annotations, remove_namespaces)
    span_positions, annotation_dict = util.gather_annotations(doc, annotations, export_names)

    # Make csv header
    csv = [make_header(token, token_annotations, export_names, delimiter)]

    # Go through spans_dict and add to csv, line by line
    for _pos, instruction, span in span_positions:
        if instruction == "open":
            # Create token line
            if span.name == token:
                csv.append(make_token_line(word_annotation[span.index], token, token_annotations, annotation_dict,
                           span.index, delimiter))

            # Create line with structural annotation
            else:
                attrs = make_attrs(span.name, annotation_dict, export_names, span.index)
                for attr in attrs:
                    csv.append(f"# {attr}")
                if not attrs:
                    csv.append(f"# {span.export}")

        # Insert blank line after each closing sentence
        elif span.name == sentence and instruction == "close":
            csv.append("")

    # Write result to file
    csv = "\n".join(csv)
    with open(out, "w") as f:
        f.write(csv)
    log.info("Exported: %s", out)


def make_header(token, token_annotations, export_names, delimiter):
    """Create a csv header containing the names of the token annotations."""
    line = [export_names.get(token, token)]
    for annot in token_annotations:
        line.append(export_names.get(":".join([token, annot]), annot))
    return delimiter.join(line)


def make_token_line(word, token, token_annotations, annotation_dict, index, delimiter):
    """Create a line with the token and its annotations."""
    line = [word.replace(delimiter, " ")]
    for attr in token_annotations:
        if attr not in annotation_dict[token]:
            attr_str = util.UNDEF
        else:
            attr_str = annotation_dict[token][attr][index]
        line.append(attr_str)
    return delimiter.join(line)


def make_attrs(annotation, annotation_dict, export_names, index):
    """Create a list with attribute-value strings for a structural element."""
    attrs = []
    for name, annot in annotation_dict[annotation].items():
        export_name = export_names.get(":".join([annotation, name]), name)
        annotation_name = export_names.get(annotation, annotation)
        attrs.append("%s.%s = %s" % (annotation_name, export_name, annot[index]))
    return attrs
