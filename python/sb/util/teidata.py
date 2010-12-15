# -*- coding: utf-8 -*-

"""
This module contains information about TEI elements
"""

toplevel_elements = set("teiCorpus TEI tei.2".split())


text_elements = set("text".split())

div_elements = set("body group div div0 div1 div2 div3 list table front back epigraph".split())

header = "teiHeader"

header_elements = set("""
teiHeader
  fileDesc
    titleStmt title author sponsor funder principal
      respStmt resp 
    editionStmt edition respStmt
    extent
    publicationStmt publisher distributor authority
                    pubPlace idno availability 
    seriesStmt title idno respStmt
    notesStmt 
    sourceDesc biblFull listBibl
      __bibl__ author title date address
        addrLine
  encodingDesc
    projectDesc
    samplingDecl
    editorialDecl
    refsDecl
    classDecl
  catRef
  profileDesc creation langUsage textClass
    keywords term classcode
  revisionDesc change
  monogr biblStruct imprint biblScope noteStmt
  correction quotation segmentation normalization language editor hyphenation
""".split())

paragraph_elements = set("""
byline p head poem lg item label gap row cell opener closer caption figure bibl
""".split())

sentence_elements = set("s l".split())
token_elements = set("w c".split())
link_elements = set("link".split())

markup_elements = set("""
hi q note distinct quote author date sic foreign name n address comment milestone mentioned 
add del corr abbr num ptr ref reg rs emph page
""".split())

all_elements = (toplevel_elements | header_elements | text_elements | div_elements |
                paragraph_elements | sentence_elements |
                token_elements | link_elements | markup_elements)

overlapping_elements = set("""
link page
""".split())

def can_overlap(tag, overlaps):
    return (tag in overlapping_elements or
            all(t in overlapping_elements for t in overlaps))


# The HTMLParser returns all elements in lowercase,
# so here is a helper dictionary to translate them back to mixed case:
mixed_case_elements = dict((elem.lower(), elem) for elem in all_elements)
