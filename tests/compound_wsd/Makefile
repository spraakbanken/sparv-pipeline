include ../../makefiles/Makefile.config

corpus = corpusname
original_dir = original
files := $(basename $(notdir $(wildcard $(original_dir)/*.xml)))

vrt_columns_annotations = word pos msd baseform $(_saldo_annotations)
vrt_columns             = word pos msd lemma    $(_saldo)
vrt_structs_annotations = text
vrt_structs             = text

xml_elements    = text
xml_annotations = text
xml_skip =

token_chunk = sentence
token_segmenter = better_word

sentence_chunk = text
sentence_segmenter = linebreaks

include ../../makefiles/Makefile.rules
