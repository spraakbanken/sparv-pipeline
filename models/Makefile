
TARGETS = help info clean all saldom.xml saldo.pickle
.PHONY: help info clean all

help:
	@echo "make ($(TARGETS))"

clean:
	rm -f saldom.xml

all: saldo.pickle saldo.compound.pickle

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

