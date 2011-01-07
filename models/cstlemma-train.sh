#!/bin/bash

lemmafile="$1"
dictfile="$2"
flexfile="$3"

# för att skapa lemmafile, spara från saldom.xml
# genom sb.saldo.save_to_cstlemmatizer

if [ ! -f "$lemmafile" ] || [ ! "$dictfile" ] || [ ! "$flexfile" ]
then
    echo "Usage: $0 lemmafile(in) dictfile(out) flexfile(out)"
    exit 1
fi

# the order FBT corresponds to (F)fullform (B)lemma (T)postag:
format="FBT"

# latin-1 = iso-8859-1:
encoding="1"

# freqfile kan skapas från SUC eller STB
# t.ex. filen SUC2.0/WORDLISTS/tagged/textword.txt

# TODO: 
# - testa resultatet genom att testa på SUC och Saldo
# - ger det bättre resultat med endast POS (NN) eller hela taggen (NN UTR SIN IND NOM)?

echo
echo "-- Creating dictionary: $dictfile"
echo
# cstlemma -D -i "$lemmafile" -c "$format" -e $encoding -N "$freqfile" -n "$freqformat" -o "$dictfile"
time cstlemma -D -i "$lemmafile" -c "$format" -e "$encoding" -o "$dictfile"

echo
echo "-- Creating flex rules: $flexfile"
echo
time cstlemma -F -i "$lemmafile" -c "$format" -e "$encoding" -R -C 2 -o "$flexfile"


