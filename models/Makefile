include $(SPARV_MAKEFILES)/Makefile.config

TARGETS = help info clean space all saldom.xml saldo.pickle saldo.compound.pickle hunpos.saldo.suc-tags.morphtable hunpos.dalinm-swedberg.saldo.suc-tags.morphtable bettertokenizer.sv.saldo-tokens stats_all.txt stats.pickle dalinm.xml dalin.pickle diapivot.xml diapivot.pickle swedbergm.xml swedberg.pickle geo.pickle nst_utf8.txt nst.comp.pos.pickle blingbring.xml blingbring.pickle sensaldo.pickle swefn.xml swefn.pickle wsd
.PHONY: help info clean all wsd

ifndef python
python = python
endif

help:
	@echo "make ($(TARGETS))"

clean:
	rm -rf saldom.xml saldo.pickle saldo.compound.pickle stats.pickle stats_all.txt blingbring.pickle swefn.pickle wsd

space:
	rm -f stats_all.txt saldom.xml nst_utf8.txt dalinm.xml diapivot.xml swedbergm.xml blingbring.txt swefn.xml

all: saldo.pickle saldo.compound.pickle hunpos.saldo.suc-tags.morphtable hunpos.dalinm-swedberg.saldo.suc-tags.morphtable stats.pickle bettertokenizer.sv.saldo-tokens diapivot.pickle dalin.pickle swedberg.pickle nst.comp.pos.pickle geo.pickle blingbring.pickle sensaldo.pickle swefn.pickle wsd

info:
	@echo "Subversion revision:"
	@svn info https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/saldom/saldom.xml | grep 'Last Changed Rev:' | grep -o '[0-9]*'
	@echo "Local revision:"
	@head saldom.xml | grep -o 'saldom.xml [0-9]*' | grep -o '[0-9]*'

saldom.xml:
	@echo "Exporting saldom.xml from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/saldom/saldom.xml --force
	@head saldom.xml | grep -o 'saldom.xml [0-9]*' | grep -o '[0-9]*' > saldo.rev
	@echo "Done."

saldo.pickle: saldom.xml
	$(python) -m sparv.saldo --xml_to_pickle  --xml "saldom.xml"  --filename "$@"

saldo.compound.pickle: saldom.xml
	$(python) -m sparv.compound --xml_to_pickle  --xml "saldom.xml"  --filename "$@"

hunpos.saldo.suc-tags.morphtable: saldo.pickle hunpos.suc.morphtable hunpos.suc.patterns
	$(python) -m sparv.hunpos_morphtable --out "$@" --saldo_model "saldo.pickle" --suc "suc3.morphtable.words" --morphtable_base "hunpos.suc.morphtable" --morphtable_patterns "hunpos.suc.patterns"

hunpos.dalinm-swedberg.saldo.suc-tags.morphtable: hunpos.saldo.suc-tags.morphtable
	$(python) -m sparv.hunpos_morphtable_hist --out "$@" --files "hist_hunposfiles/swedberg-gender.hunpos hist_hunposfiles/dalinm.hunpos" --saldosuc_morphtable "$<"

bettertokenizer.sv.saldo-tokens:
	$(python) -m sparv.segment --build_token_wordlist --out "$@" --saldo_model "saldo.pickle" --segmenter better_word --model "bettertokenizer.sv" --no_pickled_model=True

stats_all.txt:
	@echo "Exporting stats_all.txt from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/frekvens/stats_all.txt --force
	@echo "Done."

stats.pickle: stats_all.txt
	$(python) -m sparv.train_stats_model --stats_infile "stats_all.txt" --picklefile "$@"

nst_utf8.txt:
	# Requires login
	svn export https://svn.spraakdata.gu.se/sb-arkiv/lexikon/NST_svensk_leksikon/nst_utf8.txt

nst.comp.pos.pickle: nst_utf8.txt
	$(python) -m sparv.train_nst_comp_model --nst_infile nst_utf8.txt --picklefile nst.comp.pos.pickle

dalinm.xml:
	@echo "Exporting dalinm.xml from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/dalinm/dalinm.xml --force
	@echo "Done."

dalin.pickle: dalinm.xml
	$(python) -m sparv.lmflexicon --xml_to_pickle --xml "dalinm.xml" --filename "dalin.pickle"

diapivot.xml:
	@echo "Exporting diapivot.xml from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/diapivot/diapivot.xml --force
	@echo "Done."

diapivot.pickle: diapivot.xml
	$(python) -m sparv.diapivot --xml_to_pickle  --xml "diapivot.xml"  --filename "$@"

swedbergm.xml:
	@echo "Exporting swedbergm.xml from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swedbergm/swedbergm.xml --force
	@echo "Done."

swedberg.pickle: swedbergm.xml
	$(python) -m sparv.lmflexicon --xml_to_pickle --xml "swedbergm.xml" --filename "swedberg.pickle"

geo_cities1000.txt:
	@echo "Downloading and extracting cities1000..."
	@wget http://download.geonames.org/export/dump/cities1000.zip
	@unzip cities1000.zip
	@mv cities1000.txt geo_cities1000.txt
	@rm cities1000.zip
	@echo "Done."

geo_alternateNames.txt:
	@echo "Downloading and extracting alternateNames..."
	@wget http://download.geonames.org/export/dump/alternateNames.zip
	@unzip alternateNames.zip
	@mv alternateNames.txt geo_alternateNames.txt
	@rm alternateNames.zip
	@echo "Done."

geo.pickle: geo_cities1000.txt geo_alternateNames.txt
	$(python) -m sparv.geo --build_model --geonames "geo_cities1000.txt" --alternate_names "geo_alternateNames.txt" --out "$@"

blingbring.txt:
	@echo "Exporting blingbring.txt from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/bring/blingbring.txt --force
	@echo "Done."

blingbring.pickle: blingbring.txt roget_hierarchy.xml
	$(python) -m sparv.lexical_classes --blingbring_to_pickle --tsv "blingbring.txt" --classmap "roget_hierarchy.xml" --filename "$@"

swefn.xml:
	@echo "Exporting swefn.xml from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swefn/swefn.xml --force
	@echo "Done."

swefn.pickle: swefn.xml
	$(python) -m sparv.lexical_classes --swefn_to_pickle --xml "swefn.xml" --filename "$@"

sensaldo.pickle: sensaldo.txt
	$(python) -m sparv.sentiment --sensaldo_to_pickle --tsv "sensaldo.txt" --filename "$@"

wsd: wsd/ALL_512_128_w10_A2_140403_ctx1.bin wsd/lem_cbow0_s512_w10_NEW2_ctx.bin

wsd/ALL_512_128_w10_A2_140403_ctx1.bin wsd/lem_cbow0_s512_w10_NEW2_ctx.bin:
	@mkdir -p wsd -m 775
	@echo "Downloading wsd models from GitHub..."
	@wget -N https://github.com/spraakbanken/sparv-wsd/raw/master/models/scouse/ALL_512_128_w10_A2_140403_ctx1.bin -P wsd/
	@wget -N https://github.com/spraakbanken/sparv-wsd/raw/master/models/scouse/lem_cbow0_s512_w10_NEW2_ctx.bin -P wsd/
	@echo "Done."
