"""Tools for exporting, encoding and aligning corpora for Corpus Workbench."""

from __future__ import annotations

import re
from collections import OrderedDict
from pathlib import Path

from sparv.api import (
    AllSourceFilenames,
    Annotation,
    AnnotationAllSourceFiles,
    Config,
    Corpus,
    Export,
    ExportAnnotationNames,
    ExportAnnotations,
    ExportInput,
    SourceAnnotations,
    SourceAnnotationsAllSourceFiles,
    SourceFilename,
    SparvErrorMessage,
    exporter,
    get_logger,
    util,
)
from sparv.modules.xml_export import xml_utils

logger = get_logger(__name__)

CWB_MAX_LINE_LEN = 65534


@exporter(
    "VRT export",
    config=[
        Config(
            "cwb.source_annotations",
            description="List of annotations and attributes from the source data to include. Everything will be "
            "included by default.",
            datatype=list[str],
        ),
        Config("cwb.annotations", description="Sparv annotations to include.", datatype=list[str]),
    ],
)
def vrt(
    source_file: SourceFilename = SourceFilename(),
    out: Export = Export("cwb.vrt/{file}.vrt"),
    token: Annotation = Annotation("<token>"),
    word: Annotation = Annotation("[export.word]"),
    annotations: ExportAnnotations = ExportAnnotations("cwb.annotations"),
    source_annotations: SourceAnnotations = SourceAnnotations("cwb.source_annotations"),
    all_source_annotations: SourceAnnotationsAllSourceFiles = SourceAnnotationsAllSourceFiles("cwb.source_annotations"),
    remove_namespaces: bool = Config("export.remove_module_namespaces", False),
    sparv_namespace: str = Config("export.sparv_namespace"),
    source_namespace: str = Config("export.source_namespace"),
) -> None:
    """Export annotations to vrt.

    Args:
        source_file: The source file to export.
        out: The output file path for the exported VRT file.
        token: The token annotation to use for the export.
        word: The word annotation to use for the export.
        annotations: The annotations to include in the export.
        source_annotations: The source annotations to include in the export.
        all_source_annotations: All source annotations for all source files.
        remove_namespaces: Whether to remove namespaces from annotation names.
        sparv_namespace: The namespace for Sparv annotations.
        source_namespace: The namespace for source annotations.
    """
    # Create export dir
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Read words
    word_annotation = list(word.read())

    # Make a list of all token attributes for all source files. We need this because all VRT files need to have the
    # exact same token attributes in the same order.
    all_token_attributes = [
        a[0].attribute_name
        for a in set(annotations).union(all_source_annotations)
        if a[0].annotation_name == token.annotation_name and a[0].has_attribute()
    ]
    all_token_attributes.sort()

    # Get annotation spans, annotations list etc.
    annotation_list, _token_attributes, export_names = util.export.get_annotation_names(
        annotations,
        source_annotations,
        source_file=source_file,
        token_name=token.name,
        remove_namespaces=remove_namespaces,
        sparv_namespace=sparv_namespace,
        source_namespace=source_namespace,
    )
    if token not in annotation_list:
        logger.warning(
            "The 'cwb:vrt' export requires the <token> annotation for the output to include "
            "the source text. Make sure to add <token> to the list of export annotations."
        )
    xml_utils.replace_invalid_chars_in_names(export_names)
    span_positions, annotation_dict = util.export.gather_annotations(
        annotation_list, export_names, source_file=source_file
    )
    vrt_data = create_vrt(
        span_positions, token.name, word_annotation, all_token_attributes, annotation_dict, export_names, source_file
    )

    # Write result to file
    out_path.write_text(vrt_data, encoding="utf-8")
    logger.info("Exported: %s", out)


@exporter(
    "Scrambled VRT export",
    config=[Config("cwb.scramble_on", description="Annotation to use for scrambling.", datatype=str)],
)
def vrt_scrambled(
    source_file: SourceFilename = SourceFilename(),
    out: Export = Export("cwb.vrt_scrambled/{file}.vrt"),
    chunk: Annotation = Annotation("[cwb.scramble_on]"),
    chunk_order: Annotation = Annotation("[cwb.scramble_on]:misc.number_random"),
    token: Annotation = Annotation("<token>"),
    word: Annotation = Annotation("[export.word]"),
    annotations: ExportAnnotations = ExportAnnotations("cwb.annotations"),
    source_annotations: SourceAnnotations = SourceAnnotations("cwb.source_annotations"),
    all_source_annotations: SourceAnnotationsAllSourceFiles = SourceAnnotationsAllSourceFiles("cwb.source_annotations"),
    remove_namespaces: bool = Config("export.remove_module_namespaces", False),
    sparv_namespace: str = Config("export.sparv_namespace"),
    source_namespace: str = Config("export.source_namespace"),
) -> None:
    """Export annotations to vrt in scrambled order.

    Args:
        source_file: The source file to export.
        out: The output file path for the exported VRT file.
        chunk: The annotation to use for scrambling.
        chunk_order: The annotation to use for the order of scrambling.
        token: The token annotation to use for the export.
        word: The word annotation to use for the export.
        annotations: The annotations to include in the export.
        source_annotations: The source annotations to include in the export.
        all_source_annotations: All source annotations for all source files.
        remove_namespaces: Whether to remove namespaces from annotation names.
        sparv_namespace: The namespace for Sparv annotations.
        source_namespace: The namespace for source annotations.

    Raises:
        SparvErrorMessage: If the chunk annotation used for scrambling is not included in the export.
    """
    logger.progress(total=6)
    # Get annotation spans, annotations list etc.
    annotation_list, _token_attributes, export_names = util.export.get_annotation_names(
        annotations,
        source_annotations,
        source_file=source_file,
        token_name=token.name,
        remove_namespaces=remove_namespaces,
        sparv_namespace=sparv_namespace,
        source_namespace=source_namespace,
    )
    logger.progress()
    if token not in annotation_list:
        logger.warning(
            "The 'cwb:vrt_scrambled' export requires the <token> annotation for the output to include "
            "the source text. Make sure to add <token> to the list of export annotations."
        )
    if chunk not in annotation_list:
        raise SparvErrorMessage(f"The annotation used for scrambling ({chunk}) needs to be included in the output.")
    xml_utils.replace_invalid_chars_in_names(export_names)
    span_positions, annotation_dict = util.export.gather_annotations(
        annotation_list, export_names, source_file=source_file, split_overlaps=True
    )
    logger.progress()

    # Read words and scramble order
    word_annotation = list(word.read())
    chunk_order_data = list(chunk_order.read())

    logger.progress()

    # Make a list of all token attributes for all source files. We need this because all VRT files need to have the
    # exact same token attributes in the same order.
    all_token_attributes = [
        a[0].attribute_name
        for a in set(annotations).union(all_source_annotations)
        if a[0].annotation_name == token.annotation_name and a[0].has_attribute()
    ]
    all_token_attributes.sort()

    # Reorder chunks and open/close tags in correct order
    new_span_positions = util.export.scramble_spans(span_positions, chunk.name, chunk_order_data)
    logger.progress()
    # Make vrt format
    vrt_data = create_vrt(
        new_span_positions,
        token.name,
        word_annotation,
        all_token_attributes,
        annotation_dict,
        export_names,
        source_file,
    )
    logger.progress()
    # Create export dir
    out_path = Path(out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write result to file
    out_path.write_text(vrt_data, encoding="utf-8")
    logger.info("Exported: %s", out)
    logger.progress()


@exporter(
    "CWB encode",
    order=2,
    config=[
        Config(
            "cwb.bin_path", default="", description="Path to directory containing the CWB executables", datatype=str
        ),
        Config("cwb.encoding", default="utf8", description="Encoding to use", datatype=str),
        Config("cwb.skip_compression", default=False, description="Whether to skip compression", datatype=bool),
        Config("cwb.skip_validation", default=False, description="Whether to skip validation", datatype=bool),
    ],
)
def encode(
    corpus: Corpus = Corpus(),
    annotations: ExportAnnotationNames = ExportAnnotationNames("cwb.annotations"),
    source_annotations: SourceAnnotationsAllSourceFiles = SourceAnnotationsAllSourceFiles("cwb.source_annotations"),
    source_files: AllSourceFilenames = AllSourceFilenames(),
    words: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[export.word]"),
    vrt_files: ExportInput = ExportInput("cwb.vrt/{file}.vrt", all_files=True),
    out_registry: Export = Export("cwb.encoded/registry/[metadata.id]"),
    out_marker: Export = Export("cwb.encoded/data/.marker"),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    bin_path: Config = Config("cwb.bin_path"),
    encoding: str = Config("cwb.encoding"),
    remove_namespaces: bool = Config("export.remove_module_namespaces", False),
    sparv_namespace: str = Config("export.sparv_namespace"),
    source_namespace: str = Config("export.source_namespace"),
    skip_compression: bool | None = Config("cwb.skip_compression"),
    skip_validation: bool | None = Config("cwb.skip_validation"),
) -> None:
    """Encode CWB corpus from VRT files.

    Args:
        corpus: The name of the corpus to encode.
        annotations: The annotations to include in the export.
        source_annotations: The source annotations to include in the export.
        source_files: The source files to include in the export.
        words: The word annotation to use for the export.
        vrt_files: The input VRT files to encode.
        out_registry: The output registry file path.
        out_marker: The output marker file path.
        token: The token annotation to use for the export.
        bin_path: The path to the directory containing the CWB executables.
        encoding: The encoding to use for the export.
        remove_namespaces: Whether to remove namespaces from annotation names.
        sparv_namespace: The namespace for Sparv annotations.
        source_namespace: The namespace for source annotations.
        skip_compression: Whether to skip compression of the encoded files.
        skip_validation: Whether to skip validation of the encoded files.
    """
    cwb_encode(
        corpus,
        annotations,
        source_annotations,
        source_files,
        words,
        vrt_files,
        out_registry,
        out_marker,
        token.name,
        bin_path,
        encoding,
        remove_namespaces,
        sparv_namespace,
        source_namespace,
        skip_compression,
        skip_validation,
    )


@exporter("CWB encode, scrambled", order=1)
def encode_scrambled(
    corpus: Corpus = Corpus(),
    annotations: ExportAnnotationNames = ExportAnnotationNames("cwb.annotations"),
    source_annotations: SourceAnnotationsAllSourceFiles = SourceAnnotationsAllSourceFiles("cwb.source_annotations"),
    source_files: AllSourceFilenames = AllSourceFilenames(),
    words: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[export.word]"),
    vrt_files: ExportInput = ExportInput("cwb.vrt_scrambled/{file}.vrt", all_files=True),
    out_registry: Export = Export("cwb.encoded_scrambled/registry/[metadata.id]"),
    out_marker: Export = Export("cwb.encoded_scrambled/data/.scrambled_marker"),
    token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
    bin_path: str = Config("cwb.bin_path"),
    encoding: str = Config("cwb.encoding"),
    remove_namespaces: bool = Config("export.remove_module_namespaces", False),
    sparv_namespace: str = Config("export.sparv_namespace"),
    source_namespace: str = Config("export.source_namespace"),
    skip_compression: bool | None = Config("cwb.skip_compression"),
    skip_validation: bool | None = Config("cwb.skip_validation"),
) -> None:
    """Encode CWB corpus from scrambled VRT files.

    Args:
        corpus: The name of the corpus to encode.
        annotations: The annotations to include in the export.
        source_annotations: The source annotations to include in the export.
        source_files: The source files to include in the export.
        words: The word annotation to use for the export.
        vrt_files: The input VRT files to encode.
        out_registry: The output registry file path.
        out_marker: The output marker file path.
        token: The token annotation to use for the export.
        bin_path: The path to the directory containing the CWB executables.
        encoding: The encoding to use for the export.
        remove_namespaces: Whether to remove namespaces from annotation names.
        sparv_namespace: The namespace for Sparv annotations.
        source_namespace: The namespace for source annotations.
        skip_compression: Whether to skip compression of the encoded files.
        skip_validation: Whether to skip validation of the encoded files.
    """
    cwb_encode(
        corpus,
        annotations,
        source_annotations,
        source_files,
        words,
        vrt_files,
        out_registry,
        out_marker,
        token.name,
        bin_path,
        encoding,
        remove_namespaces,
        sparv_namespace,
        source_namespace,
        skip_compression,
        skip_validation,
    )


def cwb_encode(
    corpus: str,
    annotations: ExportAnnotationNames,
    source_annotations: SourceAnnotationsAllSourceFiles,
    source_files: AllSourceFilenames,
    words: AnnotationAllSourceFiles,
    vrt_files: ExportInput,
    out_registry: Export,
    out_marker: Export,
    token_name: str,
    bin_path: str,
    encoding: str,
    remove_namespaces: bool,
    sparv_namespace: str,
    source_namespace: str,
    skip_compression: bool,
    skip_validation: bool,
) -> None:
    """Encode a number of vrt files, by calling cwb-encode.

    Args:
        corpus: The name of the corpus to encode.
        annotations: The annotations to include in the export.
        source_annotations: The source annotations to include in the export.
        source_files: The source files to include in the export.
        words: The word annotation to use for the export.
        vrt_files: The input VRT files to encode.
        out_registry: The output registry file path.
        out_marker: The output marker file path.
        token_name: The name of the token annotation.
        bin_path: The path to the directory containing the CWB executables.
        encoding: The encoding to use for the export.
        remove_namespaces: Whether to remove namespaces from annotation names.
        sparv_namespace: The namespace for Sparv annotations.
        source_namespace: The namespace for source annotations.
        skip_compression: Whether to skip compression of the encoded files.
        skip_validation: Whether to skip validation of the encoded files.

    Raises:
        SparvErrorMessage: If the corpus name is not set.
    """
    if not corpus.strip():
        raise SparvErrorMessage("metadata.id needs to be set.")

    # Get vrt files
    vrt_files = [vrt_files.replace("{file}", file) for file in source_files]
    vrt_files.sort()

    # Word annotation should always be included in CWB export
    annotations = [(words, None), *list(annotations)]

    # Get annotation names
    annotation_list, token_attributes, export_names = util.export.get_annotation_names(
        annotations,
        source_annotations,
        token_name=token_name,
        remove_namespaces=remove_namespaces,
        sparv_namespace=sparv_namespace,
        source_namespace=source_namespace,
        keep_struct_names=True,
    )
    xml_utils.replace_invalid_chars_in_names(export_names)

    # Sort token attributes (but keep word first) to be in the same order as the VRT columns
    token_attributes = token_attributes[:1] + sorted(token_attributes[1:])

    # Get VRT columns
    token_attributes = [(token_name + ":" + i) for i in token_attributes]
    # First column must be called "word"
    token_attributes[0] = "word"
    columns = [cwb_escape(export_names.get(i, i)) for i in token_attributes]

    # Get VRT structs
    struct_annotations = [
        cwb_escape(export_names.get(a.name, a.name)) for a in annotation_list if a.annotation_name != token_name
    ]
    structs = parse_structural_attributes(struct_annotations)

    data_dir = Path(out_marker).resolve().parent
    registry_dir = Path(out_registry).resolve().parent
    registry_file = Path(out_registry).resolve()

    # Create export dirs
    data_dir.mkdir(exist_ok=True)
    registry_dir.mkdir(exist_ok=True)

    # Remove any existing files in data dir except for the .info file
    for f in data_dir.glob("*"):
        if f.name != ".info":
            f.unlink()

    encode_args = ["-s", "-p", "-", "-d", data_dir, "-R", registry_file, "-c", encoding, "-x"]

    for vrtfile in vrt_files:
        encode_args += ["-f", vrtfile]

    for col in columns:
        if col != "-":
            encode_args += ["-P", col]
    for struct, attrs in structs:
        attrs2 = "+".join(attrs)
        if attrs2:
            attrs2 = "+" + attrs2
        # ":0" is added to the s-attribute name to enable nesting support in cwb-encode
        encode_args += ["-S", f"{struct}:0{attrs2}"]

    bin_path = Path(bin_path)

    _, stderr = util.system.call_binary(bin_path / "cwb-encode", encode_args)
    if stderr:
        logger.warning(stderr.decode().strip())
    # Use xargs to avoid "Argument list too long" problems
    # util.system.call_binary(bin_path / "cwb-encode",
    #                         raw_command="cat %s | xargs cat | %%s %s" % (vrtfiles, " ".join(encode_args)),
    #                         use_shell=True)

    index_args = ["-V", "-r", registry_dir, corpus.upper()]
    util.system.call_binary(bin_path / "cwb-makeall", index_args)
    logger.info("Encoded and indexed %d columns, %d structs", len(columns), len(structs))

    if not skip_compression:
        logger.info("Compressing corpus files...")
        compress_args = ["-A", "-r", registry_dir, corpus.upper()]
        if skip_validation:
            compress_args.insert(0, "-T")
            logger.info("Skipping validation")
        # Compress token stream
        util.system.call_binary(bin_path / "cwb-huffcode", compress_args)
        logger.info("Removing uncompressed token stream...")
        for f in data_dir.glob("*.corpus"):
            f.unlink()
        # Compress index files
        util.system.call_binary(bin_path / "cwb-compress-rdx", compress_args)
        logger.info("Removing uncompressed index files...")
        for f in data_dir.glob("*.corpus.rev"):
            f.unlink()
        for f in data_dir.glob("*.corpus.rdx"):
            f.unlink()
        logger.info("Compression done.")

    # Write marker file
    Path(out_marker).touch()


# TODO: Add snake-support!
def cwb_align(
    corpus: str,
    other: str,
    link: str,
    align_dir: str = "annotations/align",
    bin_dir: str = "",
    registry_dir: str = "",
    encoding: str = Config("cwb.encoding", "utf8"),
) -> None:
    """Align 'corpus' with 'other' corpus, using the 'link' annotation for alignment.

    Args:
        corpus: The name of the first corpus to align.
        other: The name of the second corpus to align.
        link: The name of the annotation to use for alignment.
        align_dir: The directory to store the alignment files.
        bin_dir: The path to the directory containing the CWB executables.
        registry_dir: The path to the directory containing the CWB registry files.
        encoding: The encoding to use for the alignment files.

    Raises:
        ValueError: If the link annotation is not specified correctly.
    """
    aligndir_path = Path(align_dir)
    aligndir_path.mkdir(parents=True, exist_ok=True)
    alignfile = aligndir_path / f"{corpus}.align"
    logger.info("Aligning %s <-> %s", corpus, other)

    try:
        [(link_name, [(link_attr, _path)])] = parse_structural_attributes(link)
    except ValueError:
        raise ValueError("You have to specify exactly one alignment link.") from None
    link_attr = link_name + "_" + link_attr

    bin_path = Path(bin_dir)

    # Align linked chunks
    args = ["-v", "-o", alignfile, "-V", link_attr, corpus, other, link_name]
    result, _ = util.system.call_binary(bin_path / "cwb-align", args, encoding=encoding)
    alignfile_result = alignfile.with_suffix(".result")
    with alignfile_result.open("w", encoding="utf-8") as f:
        print(result, file=f)
    _, lastline = result.rsplit("Alignment complete.", 1)
    logger.info("%s", lastline.strip())
    if " 0 alignment" in lastline.strip():
        logger.warning("No alignment regions created")
    logger.info("Alignment file/result: %s/.result", alignfile)

    # Add alignment parameter to registry
    # cwb-regedit is not installed by default, so we skip it and modify the regfile directly instead:
    regfile = Path(registry_dir, corpus)
    with regfile.open(encoding="utf-8") as f:
        skip_align = (f"ALIGNED {other}") in f.read()

    if not skip_align:
        with regfile.open("a", encoding="utf-8") as f:
            print(file=f)
            print("# Added by cwb.py", file=f)
            print("ALIGNED", other, file=f)
        logger.info("Added alignment to registry: %s", regfile)
    # args = [corpus, ":add", ":a", other]
    # result, _ = util.system.call_binary(bin_path / "cwb-regedit", args)
    # logger.info("%s", result.strip())

    # Encode the alignments into CWB
    args = ["-v", "-D", alignfile]
    result, _ = util.system.call_binary(bin_path / "cwb-align-encode", args, encoding=encoding)
    logger.info("%s", result.strip())


################################################################################
# Auxiliaries
################################################################################


def create_vrt(
    span_positions: list[tuple],
    token_name: str,
    word_annotation: list[str],
    token_attributes: list[str | None],
    annotation_dict: dict[str, dict],
    export_names: dict[str, str],
    source_file: SourceFilename,
) -> str:
    """Go through span_positions and create VRT, line by line.

    Args:
        span_positions: List of tuples containing span positions and instructions.
        token_name: The name of the token annotation.
        word_annotation: The word annotation data.
        token_attributes: List of token attributes.
        annotation_dict: Dictionary with annotations.
        export_names: Dictionary with export names for annotations.
        source_file: The source file to export.

    Returns:
        str: The VRT data as a string.
    """
    vrt_lines = []
    for _pos, instruction, span in span_positions:
        # Create token line
        if span.name == token_name and instruction == "open":
            vrt_lines.append(
                make_token_line(
                    word_annotation[span.index], token_name, token_attributes, annotation_dict, span.index, source_file
                )
            )

        # Create line with structural annotation
        elif span.name != token_name:
            cwb_span_name = cwb_escape(span.export)
            # Open structural element
            if instruction == "open":
                attrs = make_attr_str(span.name, annotation_dict, export_names, span.index)
                if attrs:
                    vrt_lines.append(f"<{cwb_span_name} {attrs}>")
                else:
                    vrt_lines.append(f"<{cwb_span_name}>")
            # Close element
            else:
                vrt_lines.append(f"</{cwb_span_name}>")

    return "\n".join(vrt_lines)


def make_attr_str(annotation: str, annotation_dict: dict[str, dict], export_names: dict[str, str], index: int) -> str:
    """Create a string with attributes and values for a struct element.

    Args:
        annotation: The name of the annotation.
        annotation_dict: Dictionary with annotations.
        export_names: Dictionary with export names for annotations.
        index: The index of the annotation.

    Returns:
        A string with the attributes and their values.
    """
    attrs = []
    for name, annot in annotation_dict[annotation].items():
        export_name = export_names.get(f"{annotation}:{name}", name)
        export_name = cwb_escape(export_name)
        # Escape special characters in value
        value = annot[index].replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        attrs.append(f'{export_name}="{value}"')
    return " ".join(attrs)


def make_token_line(
    word: str,
    token: str,
    token_attributes: list[str | None],
    annotation_dict: dict[str, dict],
    index: int,
    source_file: str,
) -> str:
    """Create a string with the token and its annotations.

    Whitespace and / need to be replaced for CQP parsing to work. / is only allowed in the word itself.

    Args:
        word: The text of the token.
        token: The token name.
        token_attributes: List of token attributes.
        annotation_dict: Dictionary with annotations.
        index: Index of the token.
        source_file: The source file to export.

    Returns:
        str: The formatted token line with annotations.
    """
    # Warn if the word contains whitespace/newlines
    if re.search(r"\s", word):
        logger.warning(
            "Found whitespace in token %r in source file %r. To avoid issues in CWB, all whitespace will be replaced "
            "with underscores.",
            word,
            source_file,
        )

    line = [word.replace(" ", "_").replace("\n", "_").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")]
    for attr in token_attributes:
        attr_str = util.constants.UNDEF if attr not in annotation_dict[token] else annotation_dict[token][attr][index]
        line.append(
            attr_str.replace(" ", "_").replace("/", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        )
    line_string = util.misc.remove_control_characters("\t".join(line))

    # Send warning if line exceeds the max line length in CWB
    if len(line_string) > CWB_MAX_LINE_LEN:
        if "misc.head" in token_attributes or "misc.tail" in token_attributes:
            logger.warning(
                "Found a line that exceeds the max line length in CWB (%d). "
                "If this leads to a crash in CWB encode you could try setting the 'misc.head_tail_max_length' config "
                "variable to a lower value. In that case you will need to re-run the misc.head and misc.tail analyses.",
                CWB_MAX_LINE_LEN,
            )
        else:
            logger.warning(
                "Found a line that exceeds the max line length in CWB (%d). This may lead to a crash in CWB encode.",
                CWB_MAX_LINE_LEN,
            )

    return line_string


def parse_structural_attributes(structural_atts: list[str]) -> list[tuple[str, list[str]]]:
    """Parse a list of annotation names (annotation:attribute) into a list of tuples.

    Args:
        structural_atts: A list of strings representing annotation names in the format 'annotation:attribute'.

    Returns:
        A list of tuples, where each tuple contains an annotation name and a list of its attributes.
    """
    structs = OrderedDict()
    for struct in structural_atts:
        elem, _, attr = struct.partition(":")
        if elem not in structs:
            structs[elem] = []
        if attr:
            structs[elem].append(attr)
    return [(elem, structs[elem]) for elem in structs]


def cwb_escape(name: str) -> str:
    """Replace dots with "-" for CWB compatibility.

    Args:
        name: The name to escape.

    Returns:
        The escaped name.
    """
    # From the CWB documentation: "By convention, all attribute names must be lowercase
    # (more precisely, they may only contain the characters a-z, 0-9, -, and _, and may not start with a digit)"
    return re.sub(r"\.", "-", name)


def truncate_set(
    string: str, maxlength: int = 4095, delimiter: str = "|", affix: str = "|", encoding: str = "UTF-8"
) -> str:
    """Truncate a Corpus Workbench set to a maximum length.

    Args:
        string: The string to truncate.
        maxlength: The maximum length of the string.
        delimiter: The delimiter used in the string.
        affix: The affix used in the string.
        encoding: The encoding to use.

    Returns:
        The truncated string.
    """
    if len(string) <= maxlength or string == "|":
        return string
    length = 1  # Including the last affix
    values = string[1:-1].split("|")
    truncated_index = len(values)
    for i, value in enumerate(values):
        length += len(value.encode(encoding)) + 1
        if length > maxlength:
            truncated_index = i
            break
    return util.misc.cwbset(values[:truncated_index], delimiter, affix)
