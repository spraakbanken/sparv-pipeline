# Changelog

## version 4.0.0

- This version contains a complete make-over of the Sparv pipeline!
  - Everything is written in Python now (no more Makefiles or bash code).
  - Increased platform independence
  - This facilitates creating new modules, debugging, and maintenance.

- Easier installation process, Sparv is now on pypi!
  - New plugin system facilitates installation of Sparv plugins (like FreeLing).

- New format for corpus config files
  - The new format is yaml which is easier to write and more human readable than makefiles.
  - There is a command-line wizard which helps you create corpus config files.
  - The user no longer has to specify XML elements and attributes that should be kept from the original files. The  XML parser now parses all existing elements and their attributes by default. Their original names will be kept and included in the export (unless the user overrides this behaviour in the corpus config).

- Improved interface
  - New command line interface with help message
  - Better feedback with progress bar instead of illegible log output (log output is still available though)
  - More helpful error messages

- New corpus import and export formats
  - Import of plain text files
  - Export to csv (a user-friendly, non-technical column format)
  - Export to CoNNL-U format
  - Export to corpus statistics (word frequency lists)

- Better support for annotating other (i.e. non-Swedish) languages
  - Integrated Stanford Parser for English analysis (POS-tags, baseforms, dependency parsing, named-entity recognition).
  - Added named-entity recognition for FreeLing languages.
  - If a language is supported by different annotation tools, the user can now choose which tool to use.

- Improved code modularity and uniformity
  - Increased independence between modules and language models
  - This facilitates adding new annotation modules and import/export formats.
