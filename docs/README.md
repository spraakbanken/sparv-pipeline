# Sparv Documentation

Sparv's documentation is written in markdown and can be rendered as HTML or PDF.


## Setup HTML documentation

Create symlinks to documentation directories if needed:
```
cd docsify
ln -s ../user-manual user-manual
ln -s ../developers-guide developers-guide
ln -s ../images _media
cd ..
```

Set Sparv version number:
```
cd doscify
./set_version.sh
cd ..
```

Serve documentation with python (from the `docs` directory):
```
python3 -m http.server --directory docsify 3000
```

*or* with docsify (from the `docs` directory):
```
npm i docsify-cli -g
docsify serve docsify --port 3000
```

The documentation should now be available under http://localhost:3000/.

Sync HTML documentation to server:
- Create a file `config.sh` inside the docsify directory containing variables `user` (the user to use for login to
  server), `host` (the address to the host) and `path` (the absolute path on the server to the root of the
  documentation)
- Run `./sync_doc.sh`.

## Render documentation as PDF

Install requirements (markdown and latex):
```
sudo apt-get install markdown pandoc texlive-latex-base texlive-fonts-recommended texlive-fonts-extra texlive-latex-extra
```

Convert User Manual and Developer's Guide from markdown to PDF:
```
cd md2pdf
./make_pdf.sh
```

<!--
## MISC

### URLs that may have to be updated regularly
-->
