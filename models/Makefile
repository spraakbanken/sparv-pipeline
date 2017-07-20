
TARGETS = help info clean space all saldom.xml saldo.pickle saldo.compound.pickle hunpos.saldo.suc-tags.morphtable hunpos.dalinm-swedberg.saldo.suc-tags.morphtable bettertokenizer.sv.saldo-tokens stats_all.txt stats.pickle dalinm.xml dalin.pickle diapivot.xml diapivot.pickle swedbergm.xml swedberg.pickle geo.pickle nst_utf8.txt nst.comp.pos.pickle
.PHONY: help info clean all

ifndef python
python = python
endif

help:
	@echo "make ($(TARGETS))"

clean:
	rm -f saldom.xml saldo.pickle saldo.compound.pickle stats.pickle stats_all.txt

space:
	rm -f stats_all.txt saldom.xml nst_utf8.txt dalinm.xml diapivot.xml swedbergm.xml

all: saldo.pickle saldo.compound.pickle hunpos.saldo.suc-tags.morphtable stats.pickle bettertokenizer.sv.saldo-tokens diapivot.pickle geo.pickle

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
	$(python) -m sb.saldo --xml_to_pickle  --xml "saldom.xml"  --filename "$@"

saldo.compound.pickle: saldom.xml
	$(python) -m sb.compound --xml_to_pickle  --xml "saldom.xml"  --filename "$@"

hunpos.saldo.suc-tags.morphtable: saldo.pickle hunpos.suc.morphtable hunpos.suc.patterns
	$(python) -m sb.hunpos_morphtable --out "$@" --saldo_model "saldo.pickle" --suc "suc3.morphtable.words" --morphtable_base "hunpos.suc.morphtable" --morphtable_patterns "hunpos.suc.patterns"

hunpos.dalinm-swedberg.saldo.suc-tags.morphtable: hunpos.saldo.suc-tags.morphtable
	$(python) -m sb.hunpos_morphtable_hist --out "$@" --files "hist_hunposfiles/swedberg-gender.hunpos hist_hunposfiles/dalinm.hunpos" --saldosuc_morphtable "$<"

bettertokenizer.sv.saldo-tokens:
	$(python) -m sb.segment --build_token_wordlist --out "$@" --saldo_model "saldo.pickle" --segmenter better_word --model "bettertokenizer.sv" --no_pickled_model=True

stats_all.txt:
	@echo "Exporting stats_all.txt from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/frekvens/stats_all.txt --force
	@echo "Done."

stats.pickle: stats_all.txt
	$(python) -m sb.train_stats_model --stats_infile "stats_all.txt" --picklefile "$@"

nst_utf8.txt:
	# Requires login
	svn export https://svn.spraakdata.gu.se/sb-arkiv/lexikon/NST_svensk_leksikon/nst_utf8.txt

nst.comp.pos.pickle: nst_utf8.txt
	$(python) -m sb.train_nst_comp_model --nst_infile nst_utf8.txt --picklefile nst.comp.pos.pickle

dalinm.xml:
	@echo "Exporting dalinm.xml from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/dalinm/dalinm.xml --force
	@echo "Done."

dalin.pickle: dalinm.xml
	$(python) -m sb.lmflexicon --xml_to_pickle --xml "dalinm.xml" --filename "dalin.pickle"

diapivot.xml:
	@echo "Exporting diapivot.xml from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/diapivot/diapivot.xml --force
	@echo "Done."

diapivot.pickle: diapivot.xml
	$(python) -m sb.diapivot --xml_to_pickle  --xml "diapivot.xml"  --filename "$@"

swedbergm.xml:
	@echo "Exporting swedbergm.xml from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swedbergm/swedbergm.xml --force
	@echo "Done."

swedberg.pickle: swedbergm.xml
	$(python) -m sb.lmflexicon --xml_to_pickle --xml "swedbergm.xml" --filename "swedberg.pickle"

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
	$(python) -m sb.geo --build_model --geonames "geo_cities1000.txt" --alternate_names "geo_alternateNames.txt" --out "$@"
