# Sparv v4 pipeline commands

-------------------------------------------------------------
# Parsing

python -m sparv.modules.xmlparser.xmlparser --doc korpus1 --source_dir "original/xml/"

-------------------------------------------------------------
# Segmentation

python -m sparv.modules.segment.segment --doc korpus1 --out sentence --chunk text --segmenter punkt_sentence

python -m sparv.modules.segment.segment --doc korpus1 --out token --chunk sentence --segmenter better_word --model "../models/bettertokenizer.sv" --no_pickled_model=true

python -m sparv.modules.misc.misc --doc korpus1 --text_spans --out token:word --chunk token

-------------------------------------------------------------
# IDs

python -m sparv.modules.misc.ids --doc_id --out docid --docs "korpus1 korpus2"

python -m sparv.modules.misc.ids --id --doc korpus1 --annotation sentence --out sentence:id --docid docid

-------------------------------------------------------------
# Hunpos & Malt

python -m sparv.modules.hunpos.hunpos --doc korpus1 --out token:msd --word token:word --sentence sentence --model ../models/hunpos.suc3.suc-tags.default-setting.utf8.model --tag_mapping "" --morphtable "../models/hunpos.saldo.suc-tags.morphtable" --patterns "../models/hunpos.suc.patterns"

python -m sparv.modules.misc.misc --select --doc korpus1 --out token:pos --annotation token:msd --index 0 --separator .

python -m sparv.modules.misc.number --relative --doc korpus1 --out token:ref --parent sentence --child token

python -m sparv.modules.malt.malt --doc korpus1 --maltjar ../bin/maltparser-1.7.2/maltparser-1.7.2.jar --model ../models/swemalt-1.7.2.mco --out_dephead token:dephead --out_dephead_ref token:dephead.ref --out_deprel token:deprel --word token:word --pos token:pos --msd token:msd --ref token:ref --sentence sentence --token token

-------------------------------------------------------------
# Saldo

python -m sparv.modules.saldo.saldo --doc korpus1 --models ../models/saldo.pickle --out "token:baseform token:lemgram token:sense_tmp" --word token:word --token token --msd token:msd --sentence sentence --token token --reference token:ref --annotations "gf lem saldo" --precision ""

python -m sparv.modules.wsd.wsd --doc korpus1 --wsdjar ../bin/wsd/saldowsd.jar --sense_model ../models/wsd/ALL_512_128_w10_A2_140403_ctx1.bin --context_model ../models/wsd/lem_cbow0_s512_w10_NEW2_ctx.bin --out token:sense --sentence sentence --word token:word --ref token:ref --lemgram token:lemgram --saldo token:sense_tmp --pos token:pos --token token

## compound analysis

python -m sparv.modules.saldo.compound --doc korpus1 --out_complemgrams token:complemgram --out_compwf token:compwf --out_baseform token:baseform2 --word token:word --msd token:msd --baseform_tmp token:baseform  --saldo_comp_model ../models/saldo.compound.pickle --nst_model ../models/nst.comp.pos.pickle --stats_model ../models/stats.pickle

-------------------------------------------------------------
# Word Picture

python -m sparv.modules.korp.relations --doc korpus1 --out relations --word token:word --pos token:pos --lemgram token:lemgram --dephead token:dephead --deprel token:deprel --sentence_id sentence:id --ref token:ref --baseform token:baseform

python -m sparv.modules.korp.relations --sql --corpus KORPUS --db_name TEST_DB --out relations.sql --relations relations --docs "korpus1"

-------------------------------------------------------------
# Sentiment

python -m sparv.modules.sensaldo.sensaldo --doc korpus1 --sense token:sense --out_scores token:sentiment --out_labels token:sentimentclass --model ../models/sensaldo.pickle

-------------------------------------------------------------
# Geo-tagging

python -m sparv.modules.geo.geo --doc korpus1 --out sentence:geo --chunk sentence --context sentence --ne_type ne:type --ne_subtype ne:subtype --ne_name ne:name --model ../models/geo.pickle

python -m sparv.modules.geo.geo --metadata --doc korpus1 --out text:geo --chunk text --source text:source --model ../models/geo.pickle

-------------------------------------------------------------
# Named entity recognition

python -m sparv.modules.swener.swener --doc korpus1 --out_ne ne --out_ne_ex ne:ex --out_ne_type ne:type --out_ne_subtype ne:subtype --out_ne_name ne:name --word token:word --sentence sentence --token token

-------------------------------------------------------------
# Lexical classes

python -m sparv.modules.lexical_classes.lexical_classes --annotate_bb_words --doc korpus1 --out token:blingbring --model ../models/blingbring.pickle --saldoids token:sense --pos token:pos

python -m sparv.modules.lexical_classes.lexical_classes --annotate_swefn_words --doc korpus1 --out token:swefn --model ../models/swefn.pickle --saldoids token:sense --pos token:pos

python -m sparv.modules.lexical_classes.lexical_classes --annotate_doc --doc korpus1 --out text:blingbring --in_token_annotation token:blingbring --text text --token token --saldoids token:sense --freq_model ../models/blingbring.freq.gp2008+suc3+romi.pickle

python -m sparv.modules.lexical_classes.lexical_classes --annotate_doc --doc korpus1 --out text:swefn --in_token_annotation token:swefn --text text --token token --saldoids token:sense --freq_model ../models/swefn.freq.gp2008+suc3+romi.pickle

-------------------------------------------------------------
# Readability measures

python -m sparv.modules.readability.readability --lix --doc korpus1 --text text --sentence sentence --word token:word --pos token:pos --out text:lix

python -m sparv.modules.readability.readability --ovix --doc korpus1 --text text --word token:word --pos token:pos --out text:ovix

python -m sparv.modules.readability.readability --nominal_ratio --doc korpus1 --text text --pos token:pos --out text:nk

-------------------------------------------------------------
# Treetagger

python -m sparv.modules.treetagger.treetagger --doc korpus_en --lang la --model ../models/treetagger/la.par --tt_binary ../bin/treetagger/tree-tagger --out_pos token:pos --out_msd token:msd --out_lemma token:lemma --word token:word --sentence sentence

-------------------------------------------------------------
# Freeling

python -m sparv.modules.xmlparser.xmlparser --doc korpus_en --source_dir "original/xml/"

## FreeLing without s-level

python -m sparv.freeling --doc korpus_en --text text --sentence sentence --token token --word token:word --lemma token:lemma --pos token:pos --msd token:msd --conf_file ../models/freeling/en.cfg --lang en

## FreeLing with s-level

python -m sparv.freeling --doc korpus_en --text text --token token --word token:word --lemma token:lemma --pos token:pos --msd token:msd --conf_file ../models/freeling/en.cfg --lang en --slevel s

-------------------------------------------------------------
# Export

## XML export
### minimal command:
python -m sparv.modules.xml_export.xml_export --doc korpus1 --docid "docid" --export_dir "export/xml/" --token token --word token:word --annotations "text sentence token token:pos token:baseform token:ref"

### with some customisation:
python -m sparv.modules.xml_export.xml_export --doc korpus1 --docid "docid" --export_dir "export/xml/" --token token --word token:word --annotations "text text:lix text:blingbring>lexical_class sentence token token:pos token:baseform token:sentimentclass token:ref ne:name ne:ex" --original_annotations "text text:date text:forfattare>author corpus>supertext"

### formatted export:
python -m sparv.modules.xml_export.xml_export --export_formatted --doc korpus1 --docid "docid" --export_dir "export/xml_formatted/" --token token --annotations "text text:lix sentence token token:pos token:ref ne:name ne:ex" --original_annotations "text text:date text:forfattare>author corpus"

## VRT export
### minimal command:
python -m sparv.modules.cwb.cwb --export --doc korpus1 --export_dir "export/vrt/" --token token --word token:word --annotations "text text:lix text:blingbring sentence token token:pos token:baseform token:sentimentclass token:ref"

### with some customisation:
python -m sparv.modules.cwb.cwb --export --doc korpus1 --export_dir "export/vrt/" --token token --word token:word --annotations "text text:lix text:blingbring>lexical_class sentence token token:pos token:baseform token:sentimentclass token:ref ne:name ne:ex" --original_annotations "text text:date text:forfattare>author corpus>supertext"

## CWB encode

python -m sparv.modules.cwb.cwb --encode --corpus mycorpus --columns "word pos baseform sentimentclass ref" --structs "corpus text text:id text:forfattare text:lix sentence" --vrtdir "export/vrt/"

-------------------------------------------------------------
