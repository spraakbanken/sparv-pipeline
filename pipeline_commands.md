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
# Hunpos & Malt

python -m sparv.modules.hunpos.hunpos --doc korpus1 --out token:msd --word token:word --sentence sentence --model ../models/hunpos.suc3.suc-tags.default-setting.utf8.model --tag_mapping "" --morphtable "../models/hunpos.saldo.suc-tags.morphtable" --patterns "../models/hunpos.suc.patterns"

python -m sparv.modules.misc.misc --select --doc korpus1 --out token:pos --annotation token:msd --index 0 --separator .

python -m sparv.modules.malt.malt --doc korpus1 --maltjar ../bin/maltparser-1.7.2/maltparser-1.7.2.jar --model ../models/swemalt-1.7.2.mco --out token:malt --word token:word --pos token:pos --msd token:msd --sentence sentence --token token

python -m sparv.modules.misc.number --relative --doc korpus1 --out token:ref --parent sentence --child token

-------------------------------------------------------------
# Saldo

python -m sparv.modules.saldo.saldo --doc korpus1 --models ../models/saldo.pickle --out "token:baseform token:lemgram token:sense_tmp" --word token:word --token token --msd token:msd --sentence sentence --token token --reference token:ref --annotations "gf lem saldo" --precision ""

python -m sparv.modules.wsd.wsd --doc korpus1 --wsdjar ../bin/wsd/saldowsd.jar --sense_model ../models/wsd/ALL_512_128_w10_A2_140403_ctx1.bin --context_model ../models/wsd/lem_cbow0_s512_w10_NEW2_ctx.bin --out token:sense --sentence sentence --word token:word --ref token:ref --lemgram token:lemgram --saldo token:sense_tmp --pos token:pos --token token

## compound??

-------------------------------------------------------------
# Sentiment
python -m sparv.modules.sentiment.sentiment --doc korpus1 --sense token:sense --out_scores token:sentiment --out_labels token:sentimentclass --model ../models/sensaldo.pickle

-------------------------------------------------------------
# Geo-tagging

python -m sparv.modules.geo.geo --doc korpus1 --out sentence:geo --chunk sentence --context sentence --ne_type ne:type --ne_subtype ne:subtype --ne_name ne:name --model ../models/geo.pickle

python -m sparv.modules.geo.geo --metadata --doc korpus1 --out text:geo --chunk text --source text:source --model ../models/geo.pickle

-------------------------------------------------------------
# Lexical classes

python -m sparv.modules.lexical_classes.lexical_classes --annotate_bb_words --doc korpus1 --out token:blingbring --model ../models/blingbring.pickle --saldoids token:sense --pos token:pos

python -m sparv.modules.lexical_classes.lexical_classes --annotate_swefn_words --doc korpus1 --out token:swefn --model ../models/swefn.pickle --saldoids token:sense --pos token:pos

python -m sparv.modules.lexical_classes.lexical_classes --annotate_doc --doc korpus1 --out text:blingbring --in_token_annotation token:blingbring --text text --token token --saldoids token:sense --freq_model ../models/blingbring.freq.gp2008+suc3+romi.pickle

python -m sparv.modules.lexical_classes.lexical_classes --annotate_doc --doc korpus1 --out text:swefn --in_token_annotation token:swefn --text text --token token --saldoids token:sense --freq_model ../models/swefn.freq.gp2008+suc3+romi.pickle

-------------------------------------------------------------
# Treetagger

python -m sparv.modules.treetagger.treetagger --doc korpus1 --lang en --model ../models/treetagger/en.par --tt_binary ../bin/treetagger/tree-tagger --out_pos token:pos --out_msd token:msd --out_lemma token:lemma --word token:word --sentence sentence

-------------------------------------------------------------
# Freeling

python -m sparv.modules.xmlparser.xmlparser --doc korpus_en --source_dir "original/xml/"

## FreeLing with s-level

python -m sparv.freeling --doc korpus_en --text text --sentence sentence --token token --word token:word --lemma token:lemma --pos token:pos --msd token:msd --conf_file ../models/freeling/en.cfg --lang en

## FreeLing without s-level

python -m sparv.freeling --doc korpus_en --text text --token token --word token:word --lemma token:lemma --pos token:pos --msd token:msd --conf_file ../models/freeling/en.cfg --lang en --slevel s

-------------------------------------------------------------