# Sparv Documentation

Sparv's documentation is written in markdown and can be rendered as HTML or PDF.


## Generate HTML documentation

To build the HTML version of the documentation we are using `mkdocs`. Install the optional `dev` dependencies to get
the necessary tools, i.e. by running `pip install .[dev]` in the Sparv root directory. 

### Serve documentation with mkdocs

```sh
mkdocs serve
```

The documentation should now be available under http://localhost:8000/.

### Update Sparv version number in the documentation

```sh
./set_version.sh
```

### Build HTML documentation

```sh
mkdocs build
```

### Sync HTML documentation to server

- Create a file `config.sh` inside the docs directory containing the variables `user` (the user to use for login to
  server), `host` (the address to the host) and `path` (the absolute path on the server to the root of the
  documentation)
- Run `./sync_doc.sh`.

## Render documentation as PDF

Install requirements (markdown and latex):
```sh
sudo apt-get install markdown pandoc texlive-latex-base texlive-fonts-recommended texlive-fonts-extra texlive-latex-extra
```

Convert User Manual and Developer's Guide from markdown to PDF:
```sh
cd md2pdf
./make_pdf.sh
```

<!--
## MISC

### URLs that may have to be updated regularly
-->
