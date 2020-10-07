#!/usr/bin/env bash
# set -x

# Script for creating PDFs from markdown
# Requires markdown and latex

USER_MANUAL_FILES="
../user-manual/installation-and-setup.md
../user-manual/running-sparv.md
../user-manual/requirements-for-input-data.md
../user-manual/corpus-configuration.md
../user-manual/misc.md
"

DEVELOPERS_GUIDE_FILES="
../developers-guide/writing-sparv-modules.md
../developers-guide/sparv-decorators.md
../developers-guide/sparv-classes.md
../developers-guide/config.md
../developers-guide/wildcards.md
../developers-guide/misc.md
../developers-guide/writing-plugins.md
"

# Get version number from sparv/__init__.py
line=$(grep -F "__version__" ../../sparv/__init__.py) # Find version number
version=${line#"__version__ = \""} # Remove prefix
SPARV_VERSION=${version%"\""} # Remove suffix

function make_document {
    # $1: file name (without extension)
    # $2: markdown file list
    # $3: Title string

    HEADER="
---
title: Sparv Pipeline $SPARV_VERSION - $3
author: |
  | Språkbanken Text
  | Institutionen för svenska språket
  | Göteborgs universitet
  |
  |
  |
  |
  | ![](../images/sparv.png){width=2.5cm}  
---
    "

    # Concat header and files
    echo -e "$HEADER" > $1.md
    for f in $2
    do
      cat $f >> $1.md
      echo -e "\n" >> $1.md
    done

    # Convert markdown to latex/pdf:
    # pandoc -t latex -o $1.tex $1.md \
    pandoc -t latex -o $1.pdf $1.md \
    -H settings_template.tex `# include in header` \
    --template template.tex `# use template`  \
    --toc `# table of contents` \
    -N `# numbered sections` \
    -V urlcolor=RoyalBlue `# color links blue` \
    --listings `# use listings package for LaTeX code blocks`
    #-V links-as-notes=true `# print links as footnotes` \
}

# Make PDFs
make_document user-manual "$USER_MANUAL_FILES" "User Manual"
make_document developers-guide "$DEVELOPERS_GUIDE_FILES" "Developer's Guide"

# Clean-up
rm user-manual.md
rm developers-guide.md
