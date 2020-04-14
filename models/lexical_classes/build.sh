#!/usr/bin/env bash

echo "Downloading blingbring.txt"
wget -N https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/bring/blingbring.txt -P lexical_classes/
echo "Building blingbring.pickle"
$python -m sparv.modules.lexical_classes.models --blingbring_to_pickle --tsv "blingbring.txt" --classmap "roget_hierarchy.xml" --filename "blingbring.pickle"

echo "Downloading swefn.xml"
wget -N https://svn.spraakdata.gu.se/sb-arkiv/pub/lmf/swefn/swefn.xml -P lexical_classes/
echo "Building swefn.pickle"
$python -m sparv.modules.lexical_classes.models --swefn_to_pickle --xml "lexical_classes/swefn.xml" --filename "swefn.pickle"

echo "Cleaning up"
rm blingbring.txt swefn.xml
