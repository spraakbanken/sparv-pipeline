#!/usr/bin/env bash

# Set correct version number in _coverpage.md

line=$(grep -F "__version__" ../../sparv/__init__.py) # Find version number
version=${line#"__version__ = \""} # Remove prefix
SPARV_VERSION=${version%"\""} # Remove suffix
sed -i "s/<p class=\"version\"> version .\+ <\/p>/<p class=\"version\"> version $SPARV_VERSION <\/p>/" _coverpage.md
if [[ $SPARV_VERSION =~ .*\.dev.* ]]; then
    sed -i "s/# Sparv Pipeline Documentation.*/# Sparv Pipeline Documentation (development version)/" _coverpage.md
else
    sed -i "s/# Sparv Pipeline Documentation.*/# Sparv Pipeline Documentation/" _coverpage.md
fi
