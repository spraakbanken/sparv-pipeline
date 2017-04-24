include ../../makefiles/Makefile.config

corpus = corpusname
original_dir = original
files := $(basename $(notdir $(wildcard $(original_dir)/*.xml)))

vrt_columns_annotations = word
vrt_columns             = word
vrt_structs_annotations = text.label text.predicted text
vrt_structs             = text:label text:predicted text

xml_elements    = text text:label
xml_annotations = text text.label
xml_skip =

token_chunk = text
token_segmenter = better_word

sentence_chunk = text

predict = text.predicted
predict_model = models/text.label.model

include ../../makefiles/Makefile.rules
