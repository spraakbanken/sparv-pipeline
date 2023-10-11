# Sparv Decorators
Sparv decorators are used to make functions known to the Sparv registry. Only decorated functions will automatically
become part of the pipeline. When Sparv is run it will automatically search for decorated functions and scan their
arguments, thus building an index of their inputs and outputs. This index is then used to build the dependency graph.

The available decorators are listed below. Every decorator (except for `@wizard`) has one mandatory argument, the
description, which is a string describing what the function does. This is used for displaying help texts in the CLI. All
other arguments are optional and default to `None`.

## @annotator
A function decorated with `@annotator` usually takes some input (e.g. models, one or more arbitrary annotations like
tokens, sentences, parts of speeches etc.) and outputs one or more new annotations.

**Arguments:**

- `name`: Optional name to use instead of the function name.
- `description`: Description of the annotator. Used for displaying help texts in the CLI.
- `config`: List of Config instances defining config options for the annotator.
- `language`: List of supported languages. If no list is supplied all languages are supported.
- `priority`: Functions with higher priority will be preferred when scheduling which functions to run. The default
  priority is 0.
- `order`: If several annotators have the same output, this integer value will help decide which to try to use first. A
  lower number indicates higher priority.
- `wildcards`: List of wildcards used in the annotator function's arguments.
- `preloader`: Reference to a preloader function, used to preload models or processes.
- `preloader_params`: A list of names of parameters for the annotator, which will be used as arguments for the
  preloader.
- `preloader_target`: The name of the annotator parameter which should receive the return value of the preloader.
- `preloader_cleanup`: Reference to an optional cleanup function, which will be executed after each annotator use.
- `preloader_shared`: Set to False if the preloader result should not be shared among preloader processes.

**Example:**
```python
@annotator("Part-of-speech tags and baseforms from TreeTagger",
           language=["bul", "est", "fin", "lat", "nld", "pol", "ron", "slk", "deu", "eng", "fra", "spa", "ita", "rus"],
           config=[
               Config("treetagger.binary", "tree-tagger", description="TreeTagger executable"),
               Config("treetagger.model", "treetagger/[metadata.language].par", description="Path to TreeTagger model")
           ])
def annotate(lang: Language = Language(),
             model: Model = Model("[treetagger.model]"),
             tt_binary: Binary = Binary("[treetagger.binary]"),
             out_upos: Output = Output("<token>:treetagger.upos", cls="token:upos", description="Part-of-speeches in UD"),
             out_pos: Output = Output("<token>:treetagger.pos", cls="token:pos", description="Part-of-speeches from TreeTagger"),
             out_baseform: Output = Output("<token>:treetagger.baseform", description="Baseforms from TreeTagger"),
             word: Annotation = Annotation("<token:word>"),
             sentence: Annotation = Annotation("<sentence>")):
    ...
```

## @importer
A function decorated with `@importer` is used for importing corpus files in a certain file format. Its job is to read a
corpus file, extract the corpus text and existing markup (if applicable), and write annotation files for the corpus text
and markup.

Importers do not use the `Output` class to specify its outputs. Instead, outputs may be listed using the `outputs`
argument of the decorator. Any output that is to be used as explicit input by another part of the pipeline needs to be
listed here, but additional unlisted outputs may also be created.

Two outputs are implicit (and thus not listed in `outputs`) but required for every importer: the corpus text, saved by
using the `Text` class, and a list of the annotations created from existing markup, saved by using the
`SourceStructure` class.

**Arguments:**

- `description`: Description of the importer. Used for displaying help texts in the CLI.
- `file_extension`: The file extension of the type of source this importer handles, e.g. "xml" or "txt".
- `name`: Optional name to use instead of the function name.
- `outputs`: A list of annotations and attributes that the importer is guaranteed to generate. May also be a Config
    instance referring to such a list. It may generate more outputs than listed, but only the annotations listed here
    will be available to use as input for annotator functions.
- `config`: List of Config instances defining config options for the importer.

**Example:**
```python
@importer("TXT import", file_extension="txt", outputs=["text"])
def parse(source_file: SourceFilename = SourceFilename(),
          source_dir: Source = Source(),
          prefix: str = "",
          encoding: str = util.constants.UTF8,
          normalize: str = "NFC") -> None:
    ...
```

## @exporter
A function decorated with `@exporter` is used to produce "final" output (also called export), typically combining
information from multiple annotations into one file. Output produced by an exporter is usually not used as input in any
another module. An export can consist of one file per input corpus file, or it can combine information from all input
files into one output file.

**Arguments:**

- `description`: Description of the exporter. Used for displaying help texts in the CLI.
- `name`: Optional name to use instead of the function name.
- `config`: List of Config instances defining config options for the exporter.
- `language`: List of supported languages. If no list is supplied all languages are supported.
- `priority`: Functions with higher priority will be preferred when scheduling which functions to run. The default
  priority is 0.
- `order`: If several exporters have the same output, this integer value will help decide which to try to use first. A
  lower number indicates higher priority.
- `abstract`: Set to True if this exporter has no output.

**Example:**
```python
@exporter("Corpus word frequency list (withouth Swedish annotations)", order=2, config=[
    Config("stats_export.delimiter", default="\t", description="Delimiter separating columns"),
    Config("stats_export.cutoff", default=1, description="The minimum frequency a word must have in order to be included in the result")
])
def freq_list_simple(corpus: Corpus = Corpus(),
                     source_files: AllSourceFilenames = AllSourceFilenames(),
                     word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
                     pos: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:pos>"),
                     baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:baseform>"),
                     out: Export = Export("stats_export.frequency_list/stats_[metadata.id].csv"),
                     delimiter: str = Config("stats_export.delimiter"),
                     cutoff: int = Config("stats_export.cutoff")):
    ...
```

## @installer
A function decorated with `@installer` is used to deploy the corpus or related files to a remote location. For example,
the XML output could be copied to a web server, or SQL data could be inserted into a database.

Every installer needs to create a marker of the type `OutputMarker` at the end of a successful installation. Simply
call the `write()` method on the marker to create the required empty file.

It is recommended that an installer removes any related uninstaller's marker, to enable uninstallation. Use the
`MarkerOptional` class to refer to the uninstaller's marker without triggering an unnecessary installation.

**Arguments:**

- `description`: Description of the installer. Used for displaying help texts in the CLI.
- `name`: Optional name to use instead of the function name.
- `config`: List of Config instances defining config options for the installer.
- `language`: List of supported languages. If no list is supplied all languages are supported.
- `priority`: Functions with higher priority will be preferred when scheduling which functions to run. The default
  priority is 0.
- `uninstaller`: Name of related uninstaller.

**Example:**
```python
@installer("Copy compressed XML to remote host", config=[
    Config("xml_export.export_host", description="Remote host to copy XML export to."),
    Config("xml_export.export_path", description="Path on remote host to copy XML export to.")
])
def install(corpus: Corpus = Corpus(),
            xmlfile: ExportInput = ExportInput("xml_export.combined/[metadata.id].xml.bz2"),
            out: OutputMarker = OutputMarker("xml_export.install_export_pretty_marker"),
            export_path: str = Config("xml_export.export_path"),
            host: Optional[str] = Config("xml_export.export_host")):
    ...
```

## @uninstaller
A function decorated with `@uninstaller` is used to undo what an installer has done, e.g. remove corpus files from a
remote location or delete corpus data from a database.

Every uninstaller needs to create a marker of the type `OutputMarker` at the end of a successful uninstallation.
Simply call the `write()` method on the marker to create the required empty file.

It is recommended that an uninstaller removes any related installer's marker, to enable re-installation. Use the
`MarkerOptional` class to refer to the installer's marker without triggering an unnecessary installation.

**Arguments:**

- `description`: Description of the uninstaller. Used for displaying help texts in the CLI.
- `name`: Optional name to use instead of the function name.
- `config`: List of Config instances defining config options for the uninstaller.
- `language`: List of supported languages. If no list is supplied all languages are supported.
- `priority`: Functions with higher priority will be preferred when scheduling which functions to run. The default
  priority is 0.

**Example:**
```python
@uninstaller("Remove compressed XML from remote host", config=[
    Config("xml_export.export_host", description="Remote host to remove XML export from."),
    Config("xml_export.export_path", description="Path on remote host to remove XML export from.")
])
def uninstall(corpus: Corpus = Corpus(),
              xmlfile: ExportInput = ExportInput("xml_export.combined/[metadata.id].xml.bz2"),
              out: OutputMarker = OutputMarker("xml_export.uninstall_export_pretty_marker"),
              export_path: str = Config("xml_export.export_path"),
              host: Optional[str] = Config("xml_export.export_host")):
    ...
```

## @modelbuilder
A function decorated with `@modelbuilder` is used to set up a model used by other Sparv components (typically
annotators). Setting up a model could for example mean downloading a file, unzipping it, converting it into a different
format and saving it in Sparv's data directory. A model is usually not specific to one corpus. Once a model is set up on
your system it will be available for any corpus.

**Arguments:**

- `description`: Description of the installer. Used for displaying help texts in the CLI.
- `name`: Optional name to use instead of the function name.
- `config`: List of Config instances defining config options for the installer.
- `language`: List of supported languages. If no list is supplied all languages are supported.
- `priority`: Functions with higher priority will be preferred when scheduling which functions to run. The default
  priority is 0.
- `order`: If several modelbuilders have the same output, this integer value will help decide which to try to use first.
  A lower number indicates higher priority.

**Example:**
```python
@modelbuilder("Sentiment model (SenSALDO)", language=["swe"])
def build_model(out: ModelOutput = ModelOutput("sensaldo/sensaldo.pickle")):
   ...
```

## @wizard
A function decorated with `@wizard` is used to generate questions for the corpus config wizard.

**Arguments:**

- `config_keys`: a list of config keys to be set or changed by this function.
- `source_structure`: Set to `True` if the function needs access to a `SourceStructureParser` instance (the one holding
  information on the structure of the source files). Default: `False`

**Example:**
```python
@wizard(["export.source_annotations"], source_structure=True)
def import_wizard(answers, structure: SourceStructureParser):
    ...
```
