"""Export annotated corpus data to xml."""

from collections import defaultdict
import xml.etree.cElementTree as etree
import os

import sparv.util as util

UNDEF = "__UNDEF__"
WORD_ELEM = "w"


def export(doc, export_dir, token, word, annotations, original_annotations=None):
    """Export annotations to XML in export_dir.

    - doc: name of the original document
    - token: name of the token level annotation span
    - word: annotation containing the token strings.
    - original_annotations: list of elements:attributes from the original document
      to include. If none are specified, all original_annotations will be included.
    """
    os.makedirs(os.path.dirname(export_dir), exist_ok=True)

    word_annotation = util.read_annotation(doc, word)
    annotations = util.split(annotations)

    # Add original_annotations to annotations
    original_annotations = util.split(original_annotations)
    if not original_annotations:
        original_annotations = util.split(util.read_data(doc, "@structure"))
    annotations.extend(original_annotations)

    # Read all annotations in memory. Too much data?
    annotation_dict = defaultdict(dict)
    for annotation_pointer in annotations:
        print(annotation_pointer)
        a = list(util.read_annotation(doc, annotation_pointer))
        span, attr = util.split_annotation(annotation_pointer)
        annotation_dict[span][attr] = a

    xml_export = etree.Element("text")  # This must not be hard-coded!
    for word_index, word in enumerate(word_annotation):
        word_node = etree.SubElement(xml_export, WORD_ELEM)
        word_node.text = word
        for name, annotation in annotation_dict[token].items():
            word_node.set(name, annotation[word_index])

    # Write xml to file
    out_file = os.path.join(export_dir, "%s_export.xml" % doc)
    etree.ElementTree(xml_export).write(out_file, xml_declaration=False, method="xml", encoding=util.UTF8)


def export_formatted(doc, export_dir, word, annotations=None):
    """Export annotations to XML in export_dir and keep whitespaces and indentation from original file."""
    # Will be similar to export(). Some abstraction is needed here.
    pass


def write_xml(out, structs, structs_count, columns, column_nrs, tokens, vrt, fileid, fileids, valid_xml):
    """Write annotations to a valid xml file, unless valid_xml == False.

    >>> with tempfile.NamedTemporaryFile() as fileids:
    ...     util.write_annotation(fileids.name, {"fileid": "kokkonster"})
    ...     with tempfile.NamedTemporaryFile() as out:
    ...         write_xml(out.name,
    ...                   fileid="fileid",
    ...                   fileids=fileids.name,
    ...                   valid_xml=True,
    ...                   **example_data())
    ...         print(out.read().decode("UTF-8"))
    <corpus>
    <text title="Kokboken" author="Jane Oliver">
    <s>
    <w pos="DT">Ett</w>
    <w pos="NN">exempel</w>
    </s>
    <s>
    <w pos="NN">Banankaka</w>
    </s>
    </text>
    <text title="Nya kokboken" author="Jane Oliver">
    <s>
    <w pos="VB">Flambera</w>
    </s>
    </text>
    </corpus>
    <BLANKLINE>

    >>> for valid_xml in [True, False]:
    ...     print('<!-- valid_xml: ' + str(valid_xml) + ' -->')
    ...     with tempfile.NamedTemporaryFile() as fileids:
    ...         util.write_annotation(fileids.name, {"fileid": "typography"})
    ...         with tempfile.NamedTemporaryFile() as out:
    ...             write_xml(out.name,
    ...                       fileid="fileid",
    ...                       fileids=fileids.name,
    ...                       valid_xml=valid_xml,
    ...                       **example_overlapping_data())
    ...             print(out.read().decode("UTF-8"))
    <!-- valid_xml: True -->
    <corpus>
    <b>
    <w>bold</w>
    <i _overlap="typography-1">
    <w>bold_italic</w>
    </i>
    </b>
    <i _overlap="typography-1">
    <w>italic</w>
    </i>
    </corpus>
    <!-- valid_xml: False -->
    <corpus>
    <b>
    <w>bold</w>
    <i>
    <w>bold_italic</w>
    </b>
    <w>italic</w>
    </i>
    </corpus>
    <BLANKLINE>
    """
    assert fileid, "fileid not specified"
    assert fileids, "fileids not specified"

    fileid = util.read_annotation(fileids)[fileid]
    overlap = False
    open_tag_stack = []
    pending_tag_stack = []
    str_buffer = ["<corpus>"]
    elemid = 0
    elemids = {}
    invalid_str_buffer = ["<corpus>"]
    old_attr_values = dict((elem, None) for (elem, _attrs) in structs)
    for tok in tokens:
        cols = vrt[tok]
        new_attr_values = {}

        # Close tags/fix overlaps
        for elem, attrs in structs:
            new_attr_values[elem] = [(attr, cols[n]) for (attr, n) in attrs if cols.get(n)]
            if old_attr_values[elem] and new_attr_values[elem] != old_attr_values[elem]:
                if not valid_xml:
                    invalid_str_buffer.append("</%s>" % elem)

                # Check for overlap
                while elem != open_tag_stack[-1][0]:
                    overlap = True
                    # Close top stack element, remember to re-open later
                    str_buffer.append("</%s>" % open_tag_stack[-1][0])
                    pending_tag_stack.append(open_tag_stack.pop())

                # Fix pending tags
                while pending_tag_stack:
                    if elem == open_tag_stack[-1][0]:
                        str_buffer.append("</%s>" % elem)
                        open_tag_stack.pop()
                    # Re-open pending tag
                    pending_elem, attrstring = pending_tag_stack[-1]
                    if not elemids.get(pending_elem):
                        elemid += 1
                        elemids[pending_elem] = elemid
                    line = '<%s _overlap="%s-%s"%s>' % (pending_elem, fileid, elemids[pending_elem], attrstring)
                    str_buffer.append(line)
                    open_tag_stack.append(pending_tag_stack.pop())
                    old_attr_values[elem] = None

                # Close last open tag from overlap
                if elem == open_tag_stack[-1][0] and not pending_tag_stack:
                    str_buffer.append("</%s>" % elem)
                    open_tag_stack.pop()
                    old_attr_values[elem] = None
                    elemids = {}

        # Open tags
        for elem, _attrs in reversed(structs):
            if any(x[1][0] for x in new_attr_values[elem]) and new_attr_values[elem] != old_attr_values[elem]:
                attrstring = ''.join(' %s="%s"' % (attr, val[1].replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;"))
                                     for (attr, val) in new_attr_values[elem] if val and not attr == UNDEF)
                line = "<%s%s>" % (elem, attrstring)
                str_buffer.append(line)
                old_attr_values[elem] = new_attr_values[elem]
                open_tag_stack.append((elem, attrstring))
                if not valid_xml:
                    invalid_str_buffer.append("<%s%s>" % (elem, attrstring))

        # Add word annotations
        word = cols.get(structs_count, UNDEF).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

        attrstring = "".join(' %s="%s"' % (columns[n - structs_count], cols.get(n, UNDEF).replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")) for n in column_nrs[1:] if cols.get(n, UNDEF) != UNDEF)

        line = "<w%s>%s</w>" % (attrstring, word)
        str_buffer.append(util.remove_control_characters(line))
        if not valid_xml:
            invalid_str_buffer.append(util.remove_control_characters(line))

    # Close remaining open tags
    if open_tag_stack:
        for elem in reversed(open_tag_stack):
            str_buffer.append("</%s>" % elem[0])
    if not valid_xml:
        for elem, _attrs in structs:
            if old_attr_values[elem]:
                invalid_str_buffer.append("</%s>" % elem)

    str_buffer.append("</corpus>")
    invalid_str_buffer.append("</corpus>")

    # Convert str_buffer list to string
    str_buffer = "\n".join(str_buffer)
    invalid_str_buffer = "\n".join(invalid_str_buffer)

    if not valid_xml:
        # Write string buffer to invalid xml file
        with open(out, "w") as OUT:
            print(invalid_str_buffer, file=OUT)
    elif not overlap:
        # Write string buffer
        with open(out, "w") as OUT:
            print(str_buffer, file=OUT)
    else:
        # Go through xml structure and add missing _overlap attributes
        xmltree = etree.ElementTree(etree.fromstring(str_buffer))
        for child in xmltree.getroot().iter():
            # If child has and id, get previous element with same tag
            if child.tag != "w" and child.attrib.get("_overlap"):
                elemlist = list(xmltree.getroot().iter(child.tag))
                if child != elemlist[0]:
                    prev_elem = elemlist[elemlist.index(child) - 1]
                    # If previous element has no id, add id of child
                    if not prev_elem.attrib.get("_overlap"):
                        prev_elem.set("_overlap", child.attrib.get("_overlap"))
        xmltree.write(out, xml_declaration=False, method="xml", encoding=util.UTF8)

    util.log.info("Exported %d tokens, %d columns, %d structs: %s", len(tokens), len(column_nrs), len(structs), out)


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
