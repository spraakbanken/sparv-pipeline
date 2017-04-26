include ../../makefiles/Makefile.config

corpus = corpusname
original_dir = original
files := $(basename $(notdir $(wildcard $(original_dir)/*.xml)))

vrt_columns_annotations = word weights
vrt_columns             = word weights
vrt_structs_annotations = text.label text.predicted text.predicted_raw text
vrt_structs             = text:label text:predicted text:predicted_raw text

xml_elements    = text text:label
xml_annotations = text text.label
xml_skip =

token_chunk = text
token_segmenter = better_word

sentence_chunk = text

predict = text.predicted
predict_model = models/text.label.model

predict_raw = text.predicted_raw
predict_raw_model = models/text.label.model

word_weights = token.weights
word_weights_model = models/text.label.model

include ../../makefiles/Makefile.rules
