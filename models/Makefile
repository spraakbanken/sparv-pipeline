
TARGETS = help info clean all saldom.xml saldo.pickle saldo.compound.pickle hunpos.saldo.suc-tags.morphtable bettertokenizer.sv.saldo-tokens stats_all.txt stats.pickle dalinm.xml dalin.pickle swedbergm.xml swedberg.pickle
.PHONY: help info clean all

help:
	@echo "make ($(TARGETS))"

clean:
	rm -f saldom.xml

all: saldo.pickle saldo.compound.pickle hunpos.saldo.suc-tags.morphtable stats.pickle bettertokenizer.sv.saldo-tokens

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
	python -m sb.saldo --xml_to_pickle  --xml "saldom.xml"  --filename "$@"

saldo.compound.pickle: saldom.xml
	python -m sb.compound --xml_to_pickle  --xml "saldom.xml"  --filename "$@"

hunpos.saldo.suc-tags.morphtable: saldo.pickle hunpos.suc.morphtable hunpos.suc.patterns
	python -m sb.hunpos_morphtable --out "$@" --saldo_model "saldo.pickle" --suc "suc3.morphtable.words" --morphtable_base "hunpos.suc.morphtable" --morphtable_patterns "hunpos.suc.patterns"

bettertokenizer.sv.saldo-tokens:
	python segment.py --build_token_wordlist --out "$@" --saldo_model "saldo.pickle" --segmenter better_word --model "bettertokenizer.sv" --no_pickled_model=True

stats_all.txt:
	@echo "Exporting stats_all.txt from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/frekvens/stats_all.txt --force
	@echo "Done."

stats.pickle: stats_all.txt
	python -m sb.train_stats_model --stats_infile "stats_all.txt" --picklefile "$@"

dalinm.xml:
	@echo "Exporting dalinm.xml from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/dalinm/dalinm.xml --force
	@echo "Done."

dalin.pickle: dalinm.xml
	python -m sb.lmflexicon --xml_to_pickle --xml "dalinm.xml" --filename "dalin.pickle"

swedbergm.xml:
	@echo "Exporting swedbergm.xml from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swedbergm/swedbergm.xml --force
	@echo "Done."

swedberg.pickle: swedbergm.xml
	python -m sb.lmflexicon --xml_to_pickle --xml "swedbergm.xml" --filename "swedberg.pickle"
