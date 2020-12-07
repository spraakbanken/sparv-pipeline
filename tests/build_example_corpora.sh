#!/usr/bin/env bash

# Script for building example corpora zip file

echo "Creating example_corpora"
rm -rf example_corpora
mkdir example_corpora
for x in test_corpora/*
do
    dest=example_corpora/${x#*/}/
    mkdir $dest
    cp -r $x/source $dest
    cp -r $x/config.yaml $dest
    cp -r $x/*.py $dest 2>/dev/null
done

echo "Creating example_corpora.zip"
rm -f example_corpora.zip
zip -qr example_corpora.zip example_corpora
rm -r example_corpora
echo "Done!"
