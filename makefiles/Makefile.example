include $(SPARV_MAKEFILES)/Makefile.config

corpus = corpusname
original_dir = original

vrt_columns_annotations = word pos msd baseform lemgram sense compwf complemgram ref dephead.ref deprel
vrt_columns             = word pos msd lemma    lex     sense compwf complemgram ref dephead     deprel
vrt_structs_annotations = $(_ne_annotations) sentence.id sentence.geocontext  paragraph.n paragraph.geocontext
vrt_structs             = $(_ne)             sentence:id sentence:_geocontext paragraph:n paragraph:_geocontext

xml_elements    = text
xml_annotations = text
xml_skip =

token_chunk = sentence
token_segmenter = better_word

sentence_chunk = paragraph
sentence_segmenter = punkt_sentence

paragraph_chunk = text
paragraph_segmenter = blanklines

include $(SPARV_MAKEFILES)/Makefile.rules
