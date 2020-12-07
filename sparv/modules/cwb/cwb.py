"""Tools for exporting, encoding and aligning corpora for Corpus Workbench."""

import logging
import os
import re
from glob import glob
from pathlib import Path
from typing import Optional

import sparv.util as util
from sparv import (AllDocuments, Annotation, AnnotationAllDocs, Config, Corpus, Document, Export, ExportAnnotations,
                   ExportInput, SourceAnnotations, exporter)
from sparv.core import paths

log = logging.getLogger(__name__)


@exporter("VRT export", config=[
    Config("cwb.source_annotations",
           description="List of annotations and attributes from the source data to include. Everything will be "
                       "included by default."),
    Config("cwb.annotations", description="Sparv annotations to include.")
])
def vrt(doc: Document = Document(),
        out: Export = Export("vrt/{doc}.vrt"),
        token: Annotation = Annotation("<token>"),
        word: Annotation = Annotation("[export.word]"),
        annotations: ExportAnnotations = ExportAnnotations("cwb.annotations"),
        source_annotations: SourceAnnotations = SourceAnnotations("cwb.source_annotations"),
        remove_namespaces: bool = Config("export.remove_module_namespaces", False),
        sparv_namespace: str = Config("export.sparv_namespace"),
        source_namespace: str = Config("export.source_namespace")):
    """Export annotations to vrt.

    - annotations: list of elements:attributes (annotations) to include.
    - source_annotations: list of elements:attributes from the original document
      to be kept. If not specified, everything will be kept.
    """
    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Read words
    word_annotation = list(word.read())

    # Get annotation spans, annotations list etc.
    annotation_list, token_attributes, export_names = util.get_annotation_names(annotations, source_annotations,
                                                                                doc=doc, token_name=token.name,
                                                                                remove_namespaces=remove_namespaces,
                                                                                sparv_namespace=sparv_namespace,
                                                                                source_namespace=source_namespace)
    span_positions, annotation_dict = util.gather_annotations(annotation_list, export_names, doc=doc)
    vrt_data = create_vrt(span_positions, token.name, word_annotation, token_attributes, annotation_dict,
                          export_names)

    # Write result to file
    with open(out, "w") as f:
        f.write(vrt_data)
    log.info("Exported: %s", out)


@exporter("Scrambled VRT export", config=[
    Config("cwb.scramble_on", description="Annotation to use for scrambling.")
])
def vrt_scrambled(doc: Document = Document(),
                  out: Export = Export("vrt_scrambled/{doc}.vrt"),
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
    # Get annotation spans, annotations list etc.
    annotation_list, token_attributes, export_names = util.get_annotation_names(annotations, source_annotations,
                                                                                doc=doc, token_name=token.name,
                                                                                remove_namespaces=remove_namespaces,
                                                                                sparv_namespace=sparv_namespace,
                                                                                source_namespace=source_namespace)
    if chunk not in annotation_list:
        raise util.SparvErrorMessage(
            "The annotation used for scrambling ({}) needs to be included in the output.".format(chunk))
    span_positions, annotation_dict = util.gather_annotations(annotation_list, export_names, doc=doc,
                                                              split_overlaps=True)

    # Read words and document ID
    word_annotation = list(word.read())
    chunk_order_data = list(chunk_order.read())

    # Reorder chunks and open/close tags in correct order
    new_span_positions = util.scramble_spans(span_positions, chunk.name, chunk_order_data)

    # Make vrt format
    vrt_data = create_vrt(new_span_positions, token.name, word_annotation, token_attributes, annotation_dict,
                          export_names)

    # Create export dir
    os.makedirs(os.path.dirname(out), exist_ok=True)

    # Write result to file
    with open(out, "w") as f:
        f.write(vrt_data)
    log.info("Exported: %s", out)


@exporter("CWB encode", order=2, config=[
    Config("cwb.corpus_registry", default=paths.corpus_registry, description="Path to CWB registry directory"),
    Config("cwb.cwb_datadir", default=paths.cwb_datadir, description="Path to CWB data directory"),
    Config("cwb.bin_path", default="", description="Path to directory containing the CWB executables"),
    Config("cwb.encoding", default=paths.cwb_encoding, description="Encoding to use"),
    Config("cwb.skip_compression", False, description="Whether to skip compression"),
    Config("cwb.skip_validation", False, description="Whether to skip validation")
])
def encode(corpus: Corpus = Corpus(),
           annotations: ExportAnnotations = ExportAnnotations("cwb.annotations", is_input=False),
           source_annotations: SourceAnnotations = SourceAnnotations("cwb.source_annotations"),
           docs: AllDocuments = AllDocuments(),
           words: AnnotationAllDocs = AnnotationAllDocs("[export.word]"),
           vrtfiles: ExportInput = ExportInput("vrt/{doc}.vrt", all_docs=True),
           out: Export = Export("[cwb.corpus_registry]/[metadata.id]", absolute_path=True),
           out_marker: Export = Export("[cwb.cwb_datadir]/[metadata.id]/.original_marker", absolute_path=True),
           token: AnnotationAllDocs = AnnotationAllDocs("<token>"),
           bin_path: Config = Config("cwb.bin_path"),
           encoding: str = Config("cwb.encoding"),
           datadir: str = Config("cwb.cwb_datadir"),
           registry: str = Config("cwb.corpus_registry"),
           remove_namespaces: bool = Config("export.remove_module_namespaces", False),
           sparv_namespace: str = Config("export.sparv_namespace"),
           source_namespace: str = Config("export.source_namespace"),
           skip_compression: Optional[bool] = Config("cwb.skip_compression"),
           skip_validation: Optional[bool] = Config("cwb.skip_validation")):
    """Do cwb encoding with vrt files in original order."""
    cwb_encode(corpus, annotations, source_annotations, docs, words, vrtfiles, out, out_marker, token.name,
               bin_path, encoding, datadir, registry, remove_namespaces, sparv_namespace, source_namespace,
               skip_compression, skip_validation)


@exporter("CWB encode, scrambled", order=1)
def encode_scrambled(corpus: Corpus = Corpus(),
                     annotations: ExportAnnotations = ExportAnnotations("cwb.annotations", is_input=False),
                     source_annotations: SourceAnnotations = SourceAnnotations("cwb.source_annotations"),
                     docs: AllDocuments = AllDocuments(),
                     words: AnnotationAllDocs = AnnotationAllDocs("[export.word]"),
                     vrtfiles: ExportInput = ExportInput("vrt_scrambled/{doc}.vrt", all_docs=True),
                     out: Export = Export("[cwb.corpus_registry]/[metadata.id]", absolute_path=True),
                     out_marker: Export = Export("[cwb.cwb_datadir]/[metadata.id]/.scrambled_marker",
                                                 absolute_path=True),
                     token: AnnotationAllDocs = AnnotationAllDocs("<token>"),
                     bin_path: Config = Config("cwb.bin_path"),
                     encoding: str = Config("cwb.encoding"),
                     datadir: str = Config("cwb.cwb_datadir"),
                     registry: str = Config("cwb.corpus_registry"),
                     remove_namespaces: bool = Config("export.remove_module_namespaces", False),
                     sparv_namespace: str = Config("export.sparv_namespace"),
                     source_namespace: str = Config("export.source_namespace"),
                     skip_compression: Optional[bool] = Config("cwb.skip_compression"),
                     skip_validation: Optional[bool] = Config("cwb.skip_validation")):
    """Do cwb encoding with vrt files in scrambled order."""
    cwb_encode(corpus, annotations, source_annotations, docs, words, vrtfiles, out, out_marker, token.name,
               bin_path, encoding, datadir, registry, remove_namespaces, sparv_namespace, source_namespace,
               skip_compression, skip_validation)


def cwb_encode(corpus, annotations, source_annotations, docs, words, vrtfiles, out, out_marker, token_name: str,
               bin_path, encoding, datadir, registry, remove_namespaces, sparv_namespace, source_namespace,
               skip_compression, skip_validation):
    """Encode a number of vrt files, by calling cwb-encode."""
    assert datadir, "CWB_DATADIR not specified"
    assert registry, "CORPUS_REGISTRY not specified"

    # Get vrt files
    vrtfiles = [vrtfiles.replace("{doc}", doc) for doc in docs]
    vrtfiles.sort()

    # Word annotation should always be included in CWB export
    annotations.insert(0, (words, None))

    # Get annotation names
    annotation_list, token_attributes, export_names = util.get_annotation_names(annotations, source_annotations,
                                                                                docs=docs, token_name=token_name,
                                                                                remove_namespaces=remove_namespaces,
                                                                                sparv_namespace=sparv_namespace,
                                                                                source_namespace=source_namespace,
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

    corpus_registry = os.path.join(registry, corpus)
    corpus_datadir = os.path.join(datadir, corpus)
    util.system.clear_directory(corpus_datadir)

    encode_args = ["-s", "-p", "-",
                   "-d", corpus_datadir,
                   "-R", corpus_registry,
                   "-c", encoding,
                   "-x"
                   ]

    for vrtfile in vrtfiles:
        encode_args += ["-f", vrtfile]

    for col in columns:
        if col != "-":
            encode_args += ["-P", col]
    for struct, attrs in structs:
        attrs2 = "+".join(attr for attr, _n in attrs if not attr == util.UNDEF)
        if attrs2:
            attrs2 = "+" + attrs2
        encode_args += ["-S", "%s:0%s" % (struct, attrs2)]

    util.system.call_binary(os.path.join(bin_path, "cwb-encode"), encode_args, verbose=True)
    # Use xargs to avoid "Argument list too long" problems
    # util.system.call_binary(os.path.join(bin_path, "cwb-encode"), raw_command="cat %s | xargs cat | %%s %s" % (vrtfiles, " ".join(encode_args)), use_shell=True)

    index_args = ["-V", "-r", registry, corpus.upper()]
    util.system.call_binary(os.path.join(bin_path, "cwb-makeall"), index_args)
    log.info("Encoded and indexed %d columns, %d structs", len(columns), len(structs))

    if not skip_compression:
        log.info("Compressing corpus files...")
        compress_args = ["-A", corpus.upper()]
        if skip_validation:
            compress_args.insert(0, "-T")
            log.info("Skipping validation")
        # Compress token stream
        util.system.call_binary(os.path.join(bin_path, "cwb-huffcode"), compress_args)
        log.info("Removing uncompressed token stream...")
        for f in glob(os.path.join(corpus_datadir, "*.corpus")):
            os.remove(f)
        # Compress index files
        util.system.call_binary(os.path.join(bin_path, "cwb-compress-rdx"), compress_args)
        log.info("Removing uncompressed index files...")
        for f in glob(os.path.join(corpus_datadir, "*.corpus.rev")):
            os.remove(f)
        for f in glob(os.path.join(corpus_datadir, "*.corpus.rdx")):
            os.remove(f)
        log.info("Compression done.")

    # Write marker file
    Path(out_marker).touch()


# TODO: Add snake-support!
def cwb_align(corpus, other, link, aligndir="annotations/align", bin_path="",
              encoding: str = Config("cwb.encoding", "utf8")):
    """Align 'corpus' with 'other' corpus, using the 'link' annotation for alignment."""
    os.makedirs(aligndir, exist_ok=True)
    alignfile = os.path.join(aligndir, corpus + ".align")
    log.info("Aligning %s <-> %s", corpus, other)

    try:
        [(link_name, [(link_attr, _path)])] = parse_structural_attributes(link)
    except ValueError:
        raise ValueError("You have to specify exactly one alignment link.")
    link_attr = link_name + "_" + link_attr

    # Align linked chunks
    args = ["-v", "-o", alignfile, "-V", link_attr, corpus, other, link_name]
    result, _ = util.system.call_binary(os.path.join(bin_path, "cwb-align"), args, encoding=encoding)
    with open(alignfile + ".result", "w") as F:
        print(result, file=F)
    _, lastline = result.rsplit("Alignment complete.", 1)
    log.info("%s", lastline.strip())
    if " 0 alignment" in lastline.strip():
        log.warning("No alignment regions created")
    log.info("Alignment file/result: %s/.result", alignfile)

    # Add alignment parameter to registry
    # cwb-regedit is not installed by default, so we skip it and modify the regfile directly instead:
    regfile = os.path.join(os.environ["CORPUS_REGISTRY"], corpus)
    with open(regfile) as F:
        skip_align = ("ALIGNED %s" % other) in F.read()

    if not skip_align:
        with open(regfile, "a") as F:
            print(file=F)
            print("# Added by cwb.py", file=F)
            print("ALIGNED", other, file=F)
        log.info("Added alignment to registry: %s", regfile)
    # args = [corpus, ":add", ":a", other]
    # result, _ = util.system.call_binary(os.path.join(bin_path, "cwb-regedit"), args)
    # log.info("%s", result.strip())

    # Encode the alignments into CWB
    args = ["-v", "-D", alignfile]
    result, _ = util.system.call_binary(os.path.join(bin_path, "cwb-align-encode"), args, encoding=encoding)
    log.info("%s", result.strip())


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
            attr_str = util.UNDEF
        else:
            attr_str = annotation_dict[token][attr][index]
        line.append(
            attr_str.replace(" ", "_").replace("/", "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    line = "\t".join(line)
    return util.remove_control_characters(line)


def parse_structural_attributes(structural_atts):
    """Parse a list of annotations (element:attribute) into a list of tuples.

    >>> parse_structural_attributes("s - text:title text:author")
    [('s', [('__UNDEF__', 0)]), ('text', [('title', 2), ('author', 3)])]
    """
    if isinstance(structural_atts, str):
        structural_atts = structural_atts.split()
    structs = {}
    order = []
    for n, struct in enumerate(structural_atts):

        # From the CWB documentation: "By convention, all attribute names must be lowercase
        # (more precisely, they may only contain the characters a-z, 0-9, -, and _, and may not start with a digit)"
        assert not struct or struct == "-" or "." not in struct, "Struct should contain ':' or be equal to '-': %s" % struct

        if ":" in struct:
            elem, attr = struct.split(":")
        else:
            elem = struct
            attr = util.UNDEF
        if struct and not struct == "-":
            if elem not in structs:
                structs[elem] = []
                order.append(elem)
            structs[elem].append((attr, n))
    return [(elem, structs[elem]) for elem in order]


def cwb_escape(inname):
    """Replace dots with "-" for CWB compatibility."""
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
                return util.cwbset(values[:i], delimiter, affix)
