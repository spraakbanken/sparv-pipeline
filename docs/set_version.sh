#!/usr/bin/env bash

# Set current version number in mkdocs.yml

# Find version number
SPARV_VERSION=$(grep -o -P '(?<=__version__ = ")(.*)(?=")' ../sparv/__init__.py)

if [[ -z $SPARV_VERSION ]]; then
  echo "Couldn't extract version number"; exit 1
fi

if [[ $SPARV_VERSION =~ .*\.dev.* ]]; then
  SPARV_VERSION="$SPARV_VERSION (development version)"
fi

perl -p -i -e "s/version: .+?( +#.*)?\n/version: $SPARV_VERSION\1\n/" mkdocs.yml

echo "Version in mkdocs.yml set to:"
grep "version:" mkdocs.yml
