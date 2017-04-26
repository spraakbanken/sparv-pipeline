include ../../makefiles/Makefile.config

corpus = corpusname
original_dir = original
files := $(basename $(notdir $(wildcard $(original_dir)/*.xml)))

vrt_columns_annotations = word attr bttr
vrt_columns             = word attr bttr
vrt_structs_annotations = chapter.name text.title text.author
vrt_structs             = chapter:name text:title text:author

xml_elements    = w     w:attr     w:bttr     chapter chapter:name text:title text:author
xml_annotations = token token.attr token.bttr chapter chapter.name text.title text.author
xml_skip =

txt_export_column = word
txt_export_struct = chapter.name

sentence_chunk = chapter

include ../../makefiles/Makefile.rules
