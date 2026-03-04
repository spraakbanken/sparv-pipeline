#!/usr/bin/env bash

# Set current version number in zensical.toml

# Get version number from pyproject.toml
SPARV_VERSION=$(grep -o -P -m 1 '(?<=^version = ").*(?=")' ../pyproject.toml)

if [[ -z $SPARV_VERSION ]]; then
  echo "Couldn't extract version number"; exit 1
fi

if [[ $SPARV_VERSION =~ .*\.dev.* ]]; then
  SPARV_VERSION="$SPARV_VERSION (development version)"
fi

perl -p -i -e "s/version = .+?( +#.*)?\n/version = \"$SPARV_VERSION\"\1\n/" zensical.toml

echo "Version in zensical.toml set to:"
grep "^version = " zensical.toml
