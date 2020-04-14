#!/usr/bin/env bash
set -e

echo "Downloading and extracting cities1000"
wget -N http://download.geonames.org/export/dump/cities1000.zip
unzip cities1000.zip
mv cities1000.txt geo_cities1000.txt
rm cities1000.zip

echo "Downloading and extracting alternateNames"
wget -N http://download.geonames.org/export/dump/alternateNames.zip
unzip alternateNames.zip
mv alternateNames.txt geo_alternateNames.txt
rm alternateNames.zip iso-languagecodes.txt

echo "Building geo.pickle"
$python -m sparv.modules.geo.geo --build_model --geonames "geo_cities1000.txt" --alternative_names "geo_alternateNames.txt" --out "geo.pickle"

echo "Cleaning up"
rm geo_alternateNames.txt geo_cities1000.txt
