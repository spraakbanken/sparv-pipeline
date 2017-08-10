include ../../makefiles/Makefile.config

corpus = corpusname
original_dir = original
files := $(basename $(notdir $(wildcard $(original_dir)/*.xml)))

vrt_columns_annotations = word pos
vrt_columns             = word pos
vrt_structs_annotations = sentence paragraph text text.nk text.lix text.ovix text.what
vrt_structs             = sentence paragraph text text:nk text:lix text:ovix text:what

xml_elements    = text text:what
xml_annotations = text text.what
xml_skip =

token_chunk = sentence
token_segmenter = better_word

sentence_chunk = paragraph
sentence_segmenter = punkt_sentence

paragraph_chunk = text
paragraph_segmenter = blanklines

include ../../makefiles/Makefile.rules
