"""Tools for exporting, encoding and aligning corpora for Corpus Workbench."""

import os
import re
from collections import OrderedDict
from glob import glob
from pathlib import Path
from typing import Optional

from sparv.api import (AllSourceFilenames, Annotation, AnnotationAllSourceFiles, Config, Corpus, SourceFilename, Export,
                       ExportAnnotations, ExportInput, SourceAnnotations, SourceAnnotationsAllSourceFiles,
                       SparvErrorMessage, exporter, get_logger, util)

logger = get_logger(__name__)


@exporter("VRT export", config=[
    Config("cwb.source_annotations",
           description="List of annotations and attributes from the source data to include. Everything will be "
                       "included by default."),
    Config("cwb.annotations", description="Sparv annotations to include.")
])
def vrt(source_file: SourceFilename = SourceFilename(),
        out: Export = Export("cwb.vrt/{file}.vrt"),
        token: Annotation = Annotation("<token>"),
        word: Annotation = Annotation("[export.word]"),
        annotations: ExportAnnotations = ExportAnnotations("cwb.annotations"),
        source_annotations: SourceAnnotations = SourceAnnotations("cwb.source_annotations"),
        remove_namespaces: bool = Config("export.remove_module_namespaces", False),
        sparv_namespace: str = Config("export.sparv_namespace"),
        source_namespace: str = Config("export.source_namespace")):
    """Export annotations to vrt.

    - annotations: list of elements:attributes (annotations) to include.
    - source_annotations: list of elements:attributes from the original source file
      to be kept. If not specified, everything will be kept.
    """
    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Read words
    word_annotation = list(word.read())

    # Get annotation spans, annotations list etc.
    annotation_list, token_attributes, export_names = util.export.get_annotation_names(
        annotations, source_annotations, source_file=source_file, token_name=token.name,
        remove_namespaces=remove_namespaces, sparv_namespace=sparv_namespace, source_namespace=source_namespace)
    if token not in annotation_list:
        logger.warning("The 'cwb:vrt' export requires the <token> annotation for the output to include "
                       "the source text. Make sure to add <token> to the list of export annotations.")
    span_positions, annotation_dict = util.export.gather_annotations(annotation_list, export_names,
                                                                     source_file=source_file)
    vrt_data = create_vrt(span_positions, token.name, word_annotation, token_attributes, annotation_dict,
                          export_names)

    # Write result to file
    with open(out, "w", encoding="utf-8") as f:
        f.write(vrt_data)
    logger.info("Exported: %s", out)


@exporter("Scrambled VRT export", config=[
    Config("cwb.scramble_on", description="Annotation to use for scrambling.")
])
def vrt_scrambled(source_file: SourceFilename = SourceFilename(),
                  out: Export = Export("cwb.vrt_scrambled/{file}.vrt"),
                  chunk: Annotation = Annotation("[cwb.scramble_on]"),
                  chunk_order: Annotation = Annotation("[cwb.scramble_on]:misc.number_random"),
                  token: Annotation = Annotation("<token>"),
                  word: Annotation = Annotation("[export.word]"),
                  annotations: ExportAnnotations = ExportAnnotations("cwb.annotations"),
                  source_annotations: SourceAnnotations = SourceAnnotations("cwb.source_annotations"),
                  remove_namespaces: bool = Config("export.remove_module_namespaces", False),
                  sparv_namespace: str = Config("export.sparv_namespace"),
                  source_namespace: str = Config("export.source_namespace")):
    """Export annotations to vrt in scrambled order."""
    logger.progress(total=6)
    # Get annotation spans, annotations list etc.
    annotation_list, token_attributes, export_names = util.export.get_annotation_names(
        annotations, source_annotations, source_file=source_file, token_name=token.name,
        remove_namespaces=remove_namespaces, sparv_namespace=sparv_namespace, source_namespace=source_namespace)
    logger.progress()
    if token not in annotation_list:
        logger.warning("The 'cwb:vrt_scrambled' export requires the <token> annotation for the output to include "
                       "the source text. Make sure to add <token> to the list of export annotations.")
    if chunk not in annotation_list:
        raise SparvErrorMessage(
            "The annotation used for scrambling ({}) needs to be included in the output.".format(chunk))
    span_positions, annotation_dict = util.export.gather_annotations(annotation_list, export_names,
                                                                     source_file=source_file, split_overlaps=True)
    logger.progress()

    # Read words and scramble order
    word_annotation = list(word.read())
    chunk_order_data = list(chunk_order.read())

    logger.progress()

    # Reorder chunks and open/close tags in correct order
    new_span_positions = util.export.scramble_spans(span_positions, chunk.name, chunk_order_data)
    logger.progress()
    # Make vrt format
    vrt_data = create_vrt(new_span_positions, token.name, word_annotation, token_attributes, annotation_dict,
                          export_names)
    logger.progress()
    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Write result to file
    with open(out, "w", encoding="utf-8") as f:
        f.write(vrt_data)
    logger.info("Exported: %s", out)
    logger.progress()


@exporter("CWB encode", order=2, config=[
    Config("cwb.bin_path", default="", description="Path to directory containing the CWB executables"),
    Config("cwb.encoding", default="utf8", description="Encoding to use"),
    Config("cwb.skip_compression", False, description="Whether to skip compression"),
    Config("cwb.skip_validation", False, description="Whether to skip validation")
])
def encode(corpus: Corpus = Corpus(),
           annotations: ExportAnnotations = ExportAnnotations("cwb.annotations", is_input=False),
           source_annotations: SourceAnnotationsAllSourceFiles = SourceAnnotationsAllSourceFiles(
               "cwb.source_annotations"),
           source_files: AllSourceFilenames = AllSourceFilenames(),
           words: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[export.word]"),
           vrtfiles: ExportInput = ExportInput("cwb.vrt/{file}.vrt", all_files=True),
           out_registry: Export = Export("cwb.encoded/registry/[metadata.id]"),
           out_marker: Export = Export("cwb.encoded/data/.marker"),
           token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
           bin_path: Config = Config("cwb.bin_path"),
           encoding: str = Config("cwb.encoding"),
           remove_namespaces: bool = Config("export.remove_module_namespaces", False),
           sparv_namespace: str = Config("export.sparv_namespace"),
           source_namespace: str = Config("export.source_namespace"),
           skip_compression: Optional[bool] = Config("cwb.skip_compression"),
           skip_validation: Optional[bool] = Config("cwb.skip_validation")):
    """Encode CWB corpus from VRT files."""
    cwb_encode(corpus, annotations, source_annotations, source_files, words, vrtfiles, out_registry, out_marker,
               token.name, bin_path, encoding, remove_namespaces, sparv_namespace, source_namespace,
               skip_compression, skip_validation)


@exporter("CWB encode, scrambled", order=1)
def encode_scrambled(corpus: Corpus = Corpus(),
                     annotations: ExportAnnotations = ExportAnnotations("cwb.annotations", is_input=False),
                     source_annotations: SourceAnnotationsAllSourceFiles = SourceAnnotationsAllSourceFiles(
                         "cwb.source_annotations"),
                     source_files: AllSourceFilenames = AllSourceFilenames(),
                     words: AnnotationAllSourceFiles = AnnotationAllSourceFiles("[export.word]"),
                     vrtfiles: ExportInput = ExportInput("cwb.vrt_scrambled/{file}.vrt", all_files=True),
                     out_registry: Export = Export("cwb.encoded_scrambled/registry/[metadata.id]"),
                     out_marker: Export = Export("cwb.encoded_scrambled/data/.scrambled_marker"),
                     token: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token>"),
                     bin_path: Config = Config("cwb.bin_path"),
                     encoding: str = Config("cwb.encoding"),
                     remove_namespaces: bool = Config("export.remove_module_namespaces", False),
                     sparv_namespace: str = Config("export.sparv_namespace"),
                     source_namespace: str = Config("export.source_namespace"),
                     skip_compression: Optional[bool] = Config("cwb.skip_compression"),
                     skip_validation: Optional[bool] = Config("cwb.skip_validation")):
    """Encode CWB corpus from scrambled VRT files."""
    cwb_encode(corpus, annotations, source_annotations, source_files, words, vrtfiles, out_registry, out_marker,
               token.name, bin_path, encoding, remove_namespaces, sparv_namespace, source_namespace,
               skip_compression, skip_validation)


def cwb_encode(corpus, annotations, source_annotations, source_files, words, vrtfiles, out_registry, out_marker,
               token_name: str, bin_path, encoding, remove_namespaces, sparv_namespace, source_namespace,
               skip_compression, skip_validation):
    """Encode a number of vrt files, by calling cwb-encode."""
    if not corpus.strip():
        raise SparvErrorMessage("metadata.id needs to be set.")

    # Get vrt files
    vrtfiles = [vrtfiles.replace("{file}", file) for file in source_files]
    vrtfiles.sort()

    # Word annotation should always be included in CWB export
    annotations.insert(0, (words, None))

    # Get annotation names
    annotation_list, token_attributes, export_names = util.export.get_annotation_names(
        annotations, source_annotations, source_files=source_files, token_name=token_name,
        remove_namespaces=remove_namespaces, sparv_namespace=sparv_namespace, source_namespace=source_namespace,
        keep_struct_names=True)

    # Get VRT columns
    token_attributes = [(token_name + ":" + i) for i in token_attributes]
    # First column must be called "word"
    token_attributes[0] = "word"
    columns = [cwb_escape(export_names.get(i, i)) for i in token_attributes]

    # Get VRT structs
    struct_annotations = [cwb_escape(export_names.get(a.name, a.name)) for a in annotation_list if
                          not a.annotation_name == token_name]
    structs = parse_structural_attributes(struct_annotations)

    data_dir = Path(out_marker).resolve().parent
    registry_dir = Path(out_registry).resolve().parent
    registry_file = Path(out_registry).resolve()

    # Create export dirs
    data_dir.mkdir(exist_ok=True)
    registry_dir.mkdir(exist_ok=True)

    encode_args = ["-s", "-p", "-",
                   "-d", data_dir,
                   "-R", registry_file,
                   "-c", encoding,
                   "-x"
                   ]

    for vrtfile in vrtfiles:
        encode_args += ["-f", vrtfile]

    for col in columns:
        if col != "-":
            encode_args += ["-P", col]
    for struct, attrs in structs:
        attrs2 = "+".join(attrs)
        if attrs2:
            attrs2 = "+" + attrs2
        # ":0" is added to the s-attribute name to enable nesting support in cwb-encode
        encode_args += ["-S", "%s:0%s" % (struct, attrs2)]

    _, stderr = util.system.call_binary(os.path.join(bin_path, "cwb-encode"), encode_args)
    if stderr:
        logger.warning(stderr.decode().strip())
    # Use xargs to avoid "Argument list too long" problems
    # util.system.call_binary(os.path.join(bin_path, "cwb-encode"),
    #                         raw_command="cat %s | xargs cat | %%s %s" % (vrtfiles, " ".join(encode_args)),
    #                         use_shell=True)

    index_args = ["-V", "-r", registry_dir, corpus.upper()]
    util.system.call_binary(os.path.join(bin_path, "cwb-makeall"), index_args)
    logger.info("Encoded and indexed %d columns, %d structs", len(columns), len(structs))

    if not skip_compression:
        logger.info("Compressing corpus files...")
        compress_args = ["-A", "-r", registry_dir, corpus.upper()]
        if skip_validation:
            compress_args.insert(0, "-T")
            logger.info("Skipping validation")
        # Compress token stream
        util.system.call_binary(os.path.join(bin_path, "cwb-huffcode"), compress_args)
        logger.info("Removing uncompressed token stream...")
        for f in glob(os.path.join(data_dir, "*.corpus")):
            os.remove(f)
        # Compress index files
        util.system.call_binary(os.path.join(bin_path, "cwb-compress-rdx"), compress_args)
        logger.info("Removing uncompressed index files...")
        for f in glob(os.path.join(data_dir, "*.corpus.rev")):
            os.remove(f)
        for f in glob(os.path.join(data_dir, "*.corpus.rdx")):
            os.remove(f)
        logger.info("Compression done.")

    # Write marker file
    Path(out_marker).touch()


# TODO: Add snake-support!
def cwb_align(corpus, other, link, aligndir="annotations/align", bin_path="",
              encoding: str = Config("cwb.encoding", "utf8")):
    """Align 'corpus' with 'other' corpus, using the 'link' annotation for alignment."""
    os.makedirs(aligndir, exist_ok=True)
    alignfile = os.path.join(aligndir, corpus + ".align")
    logger.info("Aligning %s <-> %s", corpus, other)

    try:
        [(link_name, [(link_attr, _path)])] = parse_structural_attributes(link)
    except ValueError:
        raise ValueError("You have to specify exactly one alignment link.")
    link_attr = link_name + "_" + link_attr

    # Align linked chunks
    args = ["-v", "-o", alignfile, "-V", link_attr, corpus, other, link_name]
    result, _ = util.system.call_binary(os.path.join(bin_path, "cwb-align"), args, encoding=encoding)
    with open(alignfile + ".result", "w", encoding="utf-8") as F:
        print(result, file=F)
    _, lastline = result.rsplit("Alignment complete.", 1)
    logger.info("%s", lastline.strip())
    if " 0 alignment" in lastline.strip():
        logger.warning("No alignment regions created")
    logger.info("Alignment file/result: %s/.result", alignfile)

    # Add alignment parameter to registry
    # cwb-regedit is not installed by default, so we skip it and modify the regfile directly instead:
    regfile = os.path.join(os.environ["CORPUS_REGISTRY"], corpus)
    with open(regfile, encoding="utf-8") as F:
        skip_align = ("ALIGNED %s" % other) in F.read()

    if not skip_align:
        with open(regfile, "a", encoding="utf-8") as F:
            print(file=F)
            print("# Added by cwb.py", file=F)
            print("ALIGNED", other, file=F)
        logger.info("Added alignment to registry: %s", regfile)
    # args = [corpus, ":add", ":a", other]
    # result, _ = util.system.call_binary(os.path.join(bin_path, "cwb-regedit"), args)
    # logger.info("%s", result.strip())

    # Encode the alignments into CWB
    args = ["-v", "-D", alignfile]
    result, _ = util.system.call_binary(os.path.join(bin_path, "cwb-align-encode"), args, encoding=encoding)
    logger.info("%s", result.strip())


################################################################################
# Auxiliaries
################################################################################


def create_vrt(span_positions, token_name: str, word_annotation, token_attributes, annotation_dict, export_names):
    """Go through span_positions and create vrt, line by line."""
    vrt_lines = []
    for _pos, instruction, span in span_positions:
        # Create token line
        if span.name == token_name and instruction == "open":
            vrt_lines.append(make_token_line(word_annotation[span.index], token_name, token_attributes, annotation_dict,
                                             span.index))

        # Create line with structural annotation
        elif span.name != token_name:
            cwb_span_name = cwb_escape(span.export)
            # Open structural element
            if instruction == "open":
                attrs = make_attr_str(span.name, annotation_dict, export_names, span.index)
                if attrs:
                    vrt_lines.append("<%s %s>" % (cwb_span_name, attrs))
                else:
                    vrt_lines.append("<%s>" % cwb_span_name)
            # Close element
            else:
                vrt_lines.append("</%s>" % cwb_span_name)

    return "\n".join(vrt_lines)


def make_attr_str(annotation, annotation_dict, export_names, index):
    """Create a string with attributes and values for a struct element."""
    attrs = []
    for name, annot in annotation_dict[annotation].items():
        export_name = export_names.get(":".join([annotation, name]), name)
        export_name = cwb_escape(export_name)
        # Escape special characters in value
        value = annot[index].replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
        attrs.append('%s="%s"' % (export_name, value))
    return " ".join(attrs)


def make_token_line(word, token, token_attributes, annotation_dict, index):
    """Create a string with the token and its annotations.

    Whitespace and / need to be replaced for CQP parsing to work. / is only allowed in the word itself.
    """
    line = [word.replace(" ", "_").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")]
    for attr in token_attributes:
        if attr not in annotation_dict[token]:
            attr_str = util.constants.UNDEF
        else:
            attr_str = annotation_dict[token][attr][index]
        line.append(
            attr_str.replace(" ", "_").replace("/", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    line = "\t".join(line)
    return util.misc.remove_control_characters(line)


def parse_structural_attributes(structural_atts):
    """Parse a list of annotation names (annotation:attribute) into a list of tuples."""
    structs = OrderedDict()
    for struct in structural_atts:
        elem, _, attr = struct.partition(":")
        if elem not in structs:
            structs[elem] = []
        if attr:
            structs[elem].append(attr)
    return [(elem, structs[elem]) for elem in structs]


def cwb_escape(inname):
    """Replace dots with "-" for CWB compatibility."""
    # From the CWB documentation: "By convention, all attribute names must be lowercase
    # (more precisely, they may only contain the characters a-z, 0-9, -, and _, and may not start with a digit)"
    return re.sub(r"\.", "-", inname)


def truncateset(string, maxlength=4095, delimiter="|", affix="|", encoding="UTF-8"):
    """Truncate a Corpus Workbench set to a maximum length."""
    if len(string) <= maxlength or string == "|":
        return string
    else:
        length = 1  # Including the last affix
        values = string[1:-1].split("|")
        for i, value in enumerate(values):
            length += len(value.encode(encoding)) + 1
            if length > maxlength:
                return util.misc.cwbset(values[:i], delimiter, affix)
