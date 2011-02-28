
XML = saldom.xml

TARGETS = help info clean all saldom.xml saldo.pickle
.PHONY: help info clean all

help:
	@echo "make ($(TARGETS))"

clean:
	rm -f saldom.xml

all: saldo.pickle

info:
	@echo "Subversion revision:"
	@svn info https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/saldom/saldom.xml | grep 'Last Changed Rev:' | grep -o '[0-9]*'
	@echo "Local revision:"
	@head $(XML) | grep -o 'saldom.xml [0-9]*' | grep -o '[0-9]*'

saldom.xml:
	@echo "Exporting saldom.xml from Subversion..."
	@svn export https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/saldom/saldom.xml
	@echo "Done."

saldo.pickle: saldom.xml
	python -m sb.saldo --xml_to_pickle  --xml "$(XML)"  --filename "$@"

