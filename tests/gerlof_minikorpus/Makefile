include ../../makefiles/Makefile.config

corpus = gerlof_minikorpus
original_dir = original
files := $(basename $(notdir $(wildcard $(original_dir)/*.xml)))

vrt_columns_annotations = word cat
vrt_columns             = word wcat
vrt_structs_annotations = d.did np.npfunct np.refstat np.phiagr sentence.npid sentence.sid sentence.annotator text.source text.time text.lang
vrt_structs             = d:did np:npfunct np:refstat np:phiagr sentence:npid sentence:sid sentence:annotator text:source text:time text:lang

xml_elements    = w     w:cat     d:did np:npfunct np:refstat np:phiagr s        s:npid        s:sid        s:annotator        corpus corpus:source corpus:time corpus:lang
xml_annotations = token token.cat d.did np.npfunct np.refstat np.phiagr sentence sentence.npid sentence.sid sentence.annotator text   text.source   text.time   text.lang
xml_skip =

txt_export_column = word
txt_export_struct = text.source

sentence_chunk = sentence

include ../../makefiles/Makefile.rules
