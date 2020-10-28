# Sparv Documentation

Sparv's documentation is written in markdown and can be rendered as HTML or PDF.


## Setup HTML documentation

Create symlinks to documentation folders:
```bash
cd docsify
ln -s ../user-manual user-manual
ln -s ../developers-guide developers-guide
ln -s ../images _media
cd ..
```

Set Sparv version number:
```bash
cd doscify
./set_version.sh
```

Serve documentation with python:
```bash
python3 -m http.server --directory docsify 3000
```

or with docsify:
```bash
npm i docsify-cli -g
docsify serve docsify --port 3000
```

## Render documentation as PDF

Convert User Manual and Developer's Guide from markdown to PDF (requires markdown and latex):
```bash
cd md2pdf
./make_pdf.sh
```

## MISC

### URLs that may have to be updated regularly

- Example corpora download: https://github.com/spraakbanken/sparv-pipeline/releases/download/v4.0/example_corpora.zip
- Java download: http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html