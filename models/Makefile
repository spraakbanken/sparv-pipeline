include $(SPARV_MAKEFILES)/Makefile.config

TARGETS = help info clean space all saldo/saldom.xml saldo/saldo.pickle saldo/saldo.compound.pickle hunpos bettertokenizer.sv.saldo-tokens saldo/stats_all.txt saldo/stats.pickle dalinm.xml dalin.pickle diapivot.xml diapivot.pickle swedbergm.xml swedberg.pickle geo saldo/nst_utf8.txt saldo/nst.comp.pos.pickle sensaldo/sensaldo-base-v02.txt sensaldo/sensaldo.pickle lexical_classes wsd

.PHONY: help info clean all hunpos wsd lexical_classes geo

ifndef python
python = python
endif

help:
	@echo "make ($(TARGETS))"

clean:
	rm -rf saldo/saldom.xml saldo/saldo.pickle saldo/saldo.compound.pickle saldo/stats.pickle saldo/stats_all.txt lexical_classes/blingbring.pickle lexical_classes/swefn.pickle wsd

space:
	rm -f saldo/stats_all.txt saldo/saldom.xml saldo/nst_utf8.txt dalinm.xml diapivot.xml swedbergm.xml lexical_classes/blingbring.txt lexical_classes/swefn.xml sensaldo/sensaldo-base-v02.txt geo/geo_alternateNames.txt geo/geo_cities1000.txt

all: saldo/saldo.pickle saldo/saldo.compound.pickle hunpos saldo/stats.pickle segment/bettertokenizer.sv.saldo-tokens diapivot.pickle dalin.pickle swedberg.pickle geo.pickle sensaldo/sensaldo.pickle lexical_classes wsd

info:
	@echo "Subversion revision:"
	@svn info https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/saldom/saldom.xml | grep 'Last Changed Rev:' | grep -o '[0-9]*'
	@echo "Local revision:"
	@head saldom.xml | grep -o 'saldom.xml [0-9]*' | grep -o '[0-9]*'

saldo/saldom.xml:
	@echo "Downloading saldom.xml..."
	@wget -N https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/saldom/saldom.xml -P saldo/
	@echo "Done."

saldo/saldo.pickle: saldo/saldom.xml
	$(python) -m sparv.modules.saldo.saldo --xml_to_pickle  --xml "saldo/saldom.xml"  --filename "$@"

saldo/saldo.compound.pickle: saldo/saldom.xml
	$(python) -m sparv.modules.saldo.compound --xml_to_pickle  --xml "saldo/saldom.xml"  --filename "$@"

hunpos: hunpos/hunpos.saldo.suc-tags.morphtable hunpos/hunpos.dalinm-swedberg.saldo.suc-tags.morphtable

hunpos/hunpos.saldo.suc-tags.morphtable: saldo/saldo.pickle hunpos.suc.morphtable hunpos.suc.patterns
	$(python) -m sparv.modules.hunpos.hunpos_morphtable --out "$@" --saldo_model "saldo/saldo.pickle" --suc "suc3.morphtable.words" --morphtable_base "hunpos.suc.morphtable" --morphtable_patterns "hunpos.suc.patterns"

hunpos/hunpos.dalinm-swedberg.saldo.suc-tags.morphtable: hunpos.saldo.suc-tags.morphtable
	$(python) -m sparv.modules.hunpos.hunpos_morphtable_hist --out "$@" --files "hunpos/hist_hunposfiles/swedberg-gender.hunpos hunpos/hist_hunposfiles/dalinm.hunpos" --saldosuc_morphtable "$<"

segment/betterbettertokenizer.sv.saldo-tokens:
	$(python) -m sparv.modules.segment.segment --build_token_wordlist --out "$@" --saldo_model "saldo/saldo.pickle" --segmenter better_word --model "segment/bettertokenizer.sv" --no_pickled_model=True

stats_all.txt:
	@echo "Downloading stats_all.txt..."
	@wget -N https://svn.spraakdata.gu.se/sb-arkiv/pub/frekvens/stats_all.txt -P saldo/
	@echo "Done."

saldo/stats.pickle: saldo/stats_all.txt
	$(python) -m sparv.modules.saldo.train_stats_model --stats_infile "saldo/stats_all.txt" --picklefile "$@"

saldo/nst_utf8.txt:
	# Requires login
	svn export https://svn.spraakdata.gu.se/sb-arkiv/lexikon/NST_svensk_leksikon/nst_utf8.txt saldo/nst_utf8.txt

saldo/nst.comp.pos.pickle: saldo/nst_utf8.txt
	$(python) -m sparv.modules.saldo.train_nst_comp_model --nst_infile saldo/nst_utf8.txt --picklefile nst.comp.pos.pickle

dalinm.xml:
	@echo "Downloading dalinm.xml..."
	@wget -N https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/dalinm/dalinm.xml
	@echo "Done."

dalin.pickle: dalinm.xml
	$(python) -m sparv.util.lmflexicon --xml_to_pickle --xml "dalinm.xml" --filename "dalin.pickle"

diapivot.xml:
	@echo "Downloading diapivot.xml..."
	@wget -N https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/diapivot/diapivot.xml
	@echo "Done."

diapivot.pickle: diapivot.xml
	$(python) -m sparv.modules.hist.diapivot --xml_to_pickle  --xml "diapivot.xml"  --filename "$@"

swedbergm.xml:
	@echo "Downloading swedbergm.xml..."
	@wget -N https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swedbergm/swedbergm.xml
	@echo "Done."

swedberg.pickle: swedbergm.xml
	$(python) -m sparv.util.lmflexicon --xml_to_pickle --xml "swedbergm.xml" --filename "swedberg.pickle"

geo: geo/geo.pickle

geo/geo_cities1000.txt:
	@echo "Downloading and extracting cities1000..."
	@wget -N http://download.geonames.org/export/dump/cities1000.zip
	@unzip cities1000.zip
	@mv cities1000.txt geo_cities1000.txt
	@rm cities1000.zip
	@echo "Done."

geo/geo_alternateNames.txt:
	@echo "Downloading and extracting alternateNames..."
	@wget -N http://download.geonames.org/export/dump/alternateNames.zip
	@unzip alternateNames.zip
	@mv alternateNames.txt geo_alternateNames.txt
	@rm alternateNames.zip iso-languagecodes.txt
	@echo "Done."

geo/geo.pickle: geo_cities1000.txt geo_alternateNames.txt
	$(python) -m sparv.modules.geo.geo --build_model --geonames "geo_cities1000.txt" --alternative_names "geo_alternateNames.txt" --out "$@"

lexical_classes: lexical_classes/blingbring.pickle lexical_classes/swefn.pickle

lexical_classes/blingbring.txt:
	@echo "Downloading blingbring.txt..."
	@wget -N https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/bring/blingbring.txt -P lexical_classes/
	@echo "Done."

lexical_classes/blingbring.pickle: lexical_classes/blingbring.txt lexical_classes/roget_hierarchy.xml
	$(python) -m sparv.modules.lexical_classes.models --blingbring_to_pickle --tsv "lexical_classes/blingbring.txt" --classmap "lexical_classes/roget_hierarchy.xml" --filename "$@"

lexical_classes/swefn.xml:
	@echo "Downloading swefn.xml..."
	@wget -N https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swefn/swefn.xml -P lexical_classes/
	@echo "Done."

lexical_classes/swefn.pickle: lexical_classes/swefn.xml
	$(python) -m sparv.modules.lexical_classes.models --swefn_to_pickle --xml "lexical_classes/swefn.xml" --filename "$@"

sensaldo/sensaldo-base-v02.txt:
	@echo "Downloading and extracting sensaldo-base-v02.txt..."
	@wget -N https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/sensaldo/sensaldo-v02.zip
	@unzip sensaldo-v02.zip
	@rm sensaldo-fullform-v02.txt sensaldo-v02.zip
	@echo "Done."

sensaldo/sensaldo.pickle: sensaldo-base-v02.txt
	$(python) -m sparv.modules.sensaldo.sensaldo --sensaldo_to_pickle --tsv "sensaldo-base-v02.txt" --filename "$@"

wsd: wsd/ALL_512_128_w10_A2_140403_ctx1.bin wsd/lem_cbow0_s512_w10_NEW2_ctx.bin

wsd/ALL_512_128_w10_A2_140403_ctx1.bin wsd/lem_cbow0_s512_w10_NEW2_ctx.bin:
	@mkdir -p wsd -m 775
	@echo "Downloading wsd models from GitHub..."
	@wget -N https://github.com/spraakbanken/sparv-wsd/raw/master/models/scouse/ALL_512_128_w10_A2_140403_ctx1.bin -P wsd/
	@wget -N https://github.com/spraakbanken/sparv-wsd/raw/master/models/scouse/lem_cbow0_s512_w10_NEW2_ctx.bin -P wsd/
	@echo "Done."
