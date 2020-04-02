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
      to be kept. If not specified, everything will be kept.
    """
    # TODO: add file ID to overlap index

    # Prepare xml export
    word_annotation, span_positions, annotation_dict, export_names = prepare_xml_export(
        doc, export_dir, token, word, annotations, original_annotations=original_annotations)

    # Create root node
    first_span = span_positions[0][2]
    root_tag = first_span.export
    root_node = etree.Element(root_tag)
    root_node.text = "\n"
    add_attrs(root_node, root_tag, annotation_dict, export_names, 0)
    node_stack = [(root_node, first_span)]

    # Go through span_positions and build xml tree
    overlap_ids = defaultdict(int)  # Keeps track of which overlapping spans belong together
    for _pos, instruction, span in span_positions[1:]:

        # Create child node under the top stack node
        if instruction == "open":
            new_node = etree.SubElement(node_stack[-1][0], span.export)
            node_stack.append((new_node, span))
            add_attrs(new_node, span.name, annotation_dict, export_names, span.index)
            # Add text if this node is a token
            if span.name == token:
                new_node.text = word_annotation[span.index]
            # Some formatting: add new lines between elements
            else:
                new_node.text = "\n"
            new_node.tail = "\n"

        # Close node
        else:
            # Closing node == top stack node: pop stack and move on to next span
            if span == node_stack[-1][1]:
                node_stack.pop()

            # Handle overlapping spans
            else:
                overlap_stack = []
                # Close all overlapping spans and add and _overlap attribute to them
                while node_stack[-1][1] != span:
                    overlap_elem = node_stack.pop()
                    overlap_ids[overlap_elem[1].name] += 1
                    overlap_elem[0].set("_overlap", str(overlap_ids[overlap_elem[1].name]))  # TODO: add file ID to index
                    overlap_stack.append(overlap_elem[1])
                node_stack.pop()  # Close current span

                # Re-open overlapping spans and add and _overlap attribute to them
                while overlap_stack:
                    overlap_elem = overlap_stack.pop()
                    new_node = etree.SubElement(node_stack[-1][0], overlap_elem.export)
                    new_node.text = new_node.tail = "\n"
                    new_node.set("_overlap", str(overlap_ids[overlap_elem.name]))
                    node_stack.append((new_node, overlap_elem))
                    add_attrs(new_node, overlap_elem.name, annotation_dict, export_names, overlap_elem.index)

    # Write xml to file
    out_file = os.path.join(export_dir, "%s_export.xml" % doc)
    etree.ElementTree(root_node).write(out_file, xml_declaration=False, method="xml", encoding=util.UTF8)
    util.log.info("Exported: %s", out_file)


def export_formatted(doc, export_dir, token, word, annotations, original_annotations=None):
    """Export annotations to XML in export_dir and keep whitespaces and indentation from original file."""
    # Prepare xml export
    word_annotation, span_positions, annotation_dict, export_names = prepare_xml_export(
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

    # Get annotation spans, annotations list etc.
    annotations, _, export_names = util.get_annotation_names(doc, token, annotations, original_annotations)
    span_positions, annotation_dict = util.gather_annotations(doc, annotations, export_names)

    # Check the validity of the root tag
    first_item = span_positions[0]
    last_item = span_positions[-1]
    assert (
        first_item[1] == "open"
        and last_item[1] == "close"
        and first_item[2].name == last_item[2].name
        and first_item[2].index == last_item[2].index
    ), "Root tag is missing!"

    return word_annotation, span_positions, annotation_dict, export_names


def add_attrs(node, annotation, annotation_dict, export_names, index):
    """Att attributes from annotation_dict to node."""
    for name, annot in annotation_dict[annotation].items():
        if name != "@span":
            export_name = export_names.get(":".join([annotation, name]), name)
            node.set(export_name, annot[index])


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
