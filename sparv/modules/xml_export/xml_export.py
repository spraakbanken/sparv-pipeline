"""Export annotated corpus data to xml."""

from collections import defaultdict
import xml.etree.cElementTree as etree
import os

import sparv.util as util

UNDEF = "__UNDEF__"  # Do we need this for xml exports?


def export(doc, export_dir, token, word, annotations, original_annotations=None):
    """Export annotations to XML in export_dir.

    - doc: name of the original document
    - token: name of the token level annotation span
    - word: annotation containing the token strings.
    - annotations: list of elements:attributes (annotations) to include.
    - original_annotations: list of elements:attributes from the original document
      to be kept. If not specified, everything will be kep.
    """
    # TODO: make option for renaming elements/attributes

    # Prepare xml export
    word_annotation, sorted_spans, annotation_dict = prepare_xml_export(
        doc, export_dir, token, word, annotations, original_annotations=original_annotations)

    # Create root node
    root_tag = sorted_spans[0][1]
    root_node = etree.Element(root_tag)
    add_attrs(root_node, root_tag, annotation_dict, 0)
    node_stack = [(root_node, sorted_spans[0])]

    # Go through sorted_spans and build xml tree
    for span in sorted_spans[1:]:
        # Pop stack if top stack element is no parent to current span
        while not util.is_child(span[0], node_stack[-1][1][0]):
            node_stack.pop()
        # Create child node to top stack node
        new_node = etree.SubElement(node_stack[-1][0], span[1])
        node_stack.append((new_node, span))
        add_attrs(new_node, span[1], annotation_dict, span[2])
        # Add text if this node is a token
        if span[1] == token:
            new_node.text = word_annotation[span[2]]

    # Write xml to file
    out_file = os.path.join(export_dir, "%s_export.xml" % doc)
    etree.ElementTree(root_node).write(out_file, xml_declaration=False, method="xml", encoding=util.UTF8)
    util.log.info("Exported: %s", out_file)


def export_formatted(doc, export_dir, token, word, annotations, original_annotations=None):
    """Export annotations to XML in export_dir and keep whitespaces and indentation from original file."""
    # Prepare xml export
    word_annotation, sorted_spans, annotation_dict = prepare_xml_export(
        doc, export_dir, token, word, annotations, original_annotations=original_annotations)
    pass


########################################################################################################
# HELPERS
########################################################################################################


def prepare_xml_export(doc, export_dir, token, word, annotations, original_annotations):
    """Prepare xml export (abstraction for export and export_formatted).

    Create export dir, figure out what annotations to include and order the spans.
    """
    # Create export dir
    os.makedirs(os.path.dirname(export_dir), exist_ok=True)

    # Read words
    word_annotation = list(util.read_annotation(doc, word))

    # Add original_annotations to annotations
    annotations = util.split(annotations)
    original_annotations = util.split(original_annotations)
    if not original_annotations:
        original_annotations = util.split(util.read_data(doc, "@structure"))
    annotations.extend(original_annotations)

    sorted_spans, annotation_dict = util.gather_annotations(doc, annotations)

    # Check if root tag covers the last span
    assert util.is_child(sorted_spans[-1][0], sorted_spans[0][0]), "Root tag is missing!"

    return word_annotation, sorted_spans, annotation_dict


def add_attrs(node, annotation, annotation_dict, index):
    """Att attributes from annotation_dict to node."""
    for name, annotation in annotation_dict[annotation].items():
        if name != "@span":
            node.set(name, annotation[index])


########################################################################################################
# OLD STUFF NOT UPDATED
########################################################################################################

def write_formatted(out, annotations_columns, annotations_structs, columns, structs, structs_count, text):
    """Export xml with the same whitespaces and indentation as in the original."""
    txt, anchor2pos, pos2anchor = util.corpus.read_corpus_text(text)
    structs_order = ["__token__"] + [s[0] for s in structs]
    anchors = defaultdict(dict)
    for elem, attrs in structs:
        for attr in attrs:
            struct = util.read_annotation(annotations_structs[attr[1]][0])
            for edge in struct:
                if util.edgeStart(edge) == util.edgeEnd(edge):
                    anchors[util.edgeStart(edge)].setdefault("structs", {}).setdefault((elem, anchor2pos[util.edgeEnd(edge)], "close"), []).append((attr[0], struct[edge]))
                else:
                    anchors[util.edgeStart(edge)].setdefault("structs", {}).setdefault((elem, anchor2pos[util.edgeEnd(edge)]), []).append((attr[0], struct[edge]))
                    anchors[util.edgeEnd(edge)].setdefault("close", set()).add((elem, edge))
    for n, annot in enumerate(annotations_columns):
        n += structs_count
        for tok, value in util.read_annotation_iteritems(annot):
            if n > structs_count:  # Any column except the first (the word)
                value = "|" if value == "|/|" else value
            anchors[util.edgeStart(tok)].setdefault("token", []).append(value.replace("\n", " "))
            if n == structs_count:
                anchors[util.edgeEnd(tok)].setdefault("close", set()).add(("__token__", None))
    currpos = 0

    with open(out, "w") as OUT:
        OUT.write("<corpus>")
        for pos, anchor in sorted(list(pos2anchor.items()), key=lambda x: x[0]):
            OUT.write(txt[currpos:pos].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
            if anchor in anchors:
                if "close" in anchors[anchor]:
                    if ("__token__", None) in anchors[anchor]["close"]:
                        OUT.write("</w>")
                    OUT.write("".join("</%s>" % e[0] for e in sorted(anchors[anchor]["close"], key=lambda x: structs_order.index(x[0])) if not e[0] == "__token__"))

                if "structs" in anchors[anchor]:
                    for elem, annot in sorted(iter(list(anchors[anchor]["structs"].items())), key=lambda x: (-x[0][1], -structs_order.index(x[0][0]))):
                        if elem not in ("close", "token"):
                            attrstring = "".join(' %s="%s"' % (attr, val.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;"))
                                                 for (attr, val) in annot if val and not attr == UNDEF)
                            close = "/" if len(elem) == 3 else ""
                            OUT.write("<%s%s%s>" % (elem[0], attrstring, close))

                if "token" in anchors[anchor]:
                    attrstring = "".join(' %s="%s"' % (columns[i + 1], a.replace("&", "&amp;").replace('"', '&quot;').replace("<", "&lt;").replace(">", "&gt;"))
                                         for i, a in enumerate(anchors[anchor]["token"][1:]) if a)
                    OUT.write("<w%s>" % attrstring)

            currpos = pos
        OUT.write("</corpus>")
    util.log.info("Exported: %s", out)


def combine_xml(master, out, xmlfiles="", xmlfiles_list=""):
    """Combine xmlfiles into a single xml file and save to out."""
    assert master != "", "Master not specified"
    assert out != "", "Outfile not specified"
    assert (xmlfiles or xmlfiles_list), "Missing source"

    if xmlfiles:
        if isinstance(xmlfiles, str):
            xmlfiles = xmlfiles.split()
    elif xmlfiles_list:
        with open(xmlfiles_list) as insource:
            xmlfiles = [line.strip() for line in insource]

    xmlfiles.sort()

    with open(out, "w") as OUT:
        print('<corpus id="%s">' % master.replace("&", "&amp;").replace('"', "&quot;"), file=OUT)
        for infile in xmlfiles:
            util.log.info("Read: %s", infile)
            with open(infile, "r") as IN:
                # Append everything but <corpus> and </corpus>
                print(IN.read()[9:-10], end=' ', file=OUT)
        print("</corpus>", file=OUT)
        util.log.info("Exported: %s" % out)


if __name__ == "__main__":
    util.run.main(export,
                  export_formatted=export_formatted,
                  combine_xml=combine_xml)
