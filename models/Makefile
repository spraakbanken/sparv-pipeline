
XML = saldom.xml

TARGETS = help info clean all saldom.xml saldo.saldoid.pickle saldo.baseform.pickle saldo.lemgram.pickle
.PHONY: help info clean all

help:
	@echo "make ($(TARGETS))"

clean:
	rm -f saldom.xml

all: saldo.saldoid.pickle saldo.baseform.pickle saldo.lemgram.pickle

info:
	svn info https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/saldom/saldom.xml

saldom.xml:
	@echo "Exporting saldom.xml from SVN..."
	svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/saldom/saldom.xml
	@echo "Done."

saldo.saldoid.pickle: saldom.xml
	python -m sb.saldo --xml_to_pickle  --xml "$(XML)"  --value_element "saldo"  --filename "$@"

saldo.baseform.pickle: saldom.xml
	python -m sb.saldo --xml_to_pickle  --xml "$(XML)"  --value_element "gf"  --filename "$@"

saldo.lemgram.pickle: saldom.xml
	python -m sb.saldo --xml_to_pickle  --xml "$(XML)"  --value_element "lem"  --filename "$@"

