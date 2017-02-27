include ../../makefiles/Makefile.config

corpus = corpusname
original_dir = original
files := $(basename $(notdir $(wildcard $(original_dir)/*.xml)))

vrt_columns_annotations = word pos msd baseform lemgram saldo prefix suffix ref dephead.ref deprel
vrt_columns             = word pos msd lemma    lex     saldo prefix suffix ref dephead     deprel
vrt_structs_annotations = text
vrt_structs             = text

xml_elements    = text
xml_annotations = text
xml_skip =

token_chunk = sentence
token_segmenter = better_word

sentence_chunk = paragraph
sentence_segmenter = punkt_sentence

paragraph_chunk = text
paragraph_segmenter = blanklines

include ../../makefiles/Makefile.rules
