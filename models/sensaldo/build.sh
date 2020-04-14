#!/usr/bin/env bash
set -e

echo "Downloading and extracting sensaldo-base-v02.txt"
wget -N https://svn.spraakdata.gu.se/sb-arkiv/pub/lexikon/sensaldo/sensaldo-v02.zip
unzip sensaldo-v02.zip
rm sensaldo-fullform-v02.txt sensaldo-v02.zip

echo "Building sensaldo.pickle"
$python -m sparv.modules.sensaldo.sensaldo --sensaldo_to_pickle --tsv "sensaldo-base-v02.txt" --filename "sensaldo.pickle"

echo "Cleaning up"
rm sensaldo-base-v02.txt
