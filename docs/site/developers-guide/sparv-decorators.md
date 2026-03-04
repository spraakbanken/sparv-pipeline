# Sparv Decorators

Sparv is built around a modular pipeline of processors, each responsible for a specific task in the corpus
processing workflow. Processors are implemented as Python functions and registered using Sparv's decorators. These
decorators attach metadata to each function—such as a description and configuration options—and
register the function within the pipeline.

Sparv provides several types of processors: annotators, importers, exporters, installers, uninstallers, model builders,
and wizards. Each processor type has a corresponding decorator, described in detail below.

For all decorators (except `@wizard`), the only required argument is `description`, a string explaining what the
function does. This description is displayed in CLI help texts. The first line of the description should be a short
summary, usually one sentence long. Optionally, a longer description can be added below the first line, separated by a
blank line.

<style>
  /* Hide the module docstring */
  article > div.doc > div.doc > p {
    display: none !important;
  }
</style>

::: sparv.core.registry
    options:
      show_root_toc_entry: false
      members:
       - annotator

**Example:**

```python
@annotator(
    "Part-of-speech tags and baseforms from TreeTagger",
    language=["bul", "est", "fin", "lat", "nld", "pol", "ron", "slk", "deu", "eng", "fra", "spa", "ita", "rus"],
    config=[
        Config("treetagger.binary", "tree-tagger", description="TreeTagger executable"),
        Config("treetagger.model", "treetagger/[metadata.language].par", description="Path to TreeTagger model"),
    ],
)
def annotate(
    lang: Language = Language(),
    model: Model = Model("[treetagger.model]"),
    tt_binary: Binary = Binary("[treetagger.binary]"),
    out_upos: Output = Output("<token>:treetagger.upos", cls="token:upos", description="Part-of-speeches in UD"),
    out_pos: Output = Output("<token>:treetagger.pos", cls="token:pos", description="Part-of-speeches from TreeTagger"),
    out_baseform: Output = Output("<token>:treetagger.baseform", description="Baseforms from TreeTagger"),
    word: Annotation = Annotation("<token:word>"),
    sentence: Annotation = Annotation("<sentence>"),
):
    ...
```

::: sparv.core.registry
    options:
      show_root_toc_entry: false
      members:
       - importer

**Example:**

```python
@importer("TXT import", file_extension="txt", outputs=["text"])
def parse(
    source_file: SourceFilename = SourceFilename(),
    source_dir: Source = Source(),
    prefix: str = "",
    encoding: str = util.constants.UTF8,
    normalize: str = "NFC",
) -> None:
    ...
```

::: sparv.core.registry
    options:
      show_root_toc_entry: false
      members:
       - exporter

**Example:**

```python
@exporter(
    "Corpus word frequency list (without Swedish annotations)",
    order=2,
    config=[
        Config("stats_export.delimiter", default="\t", description="Delimiter separating columns"),
        Config(
            "stats_export.cutoff",
            default=1,
            description="The minimum frequency a word must have in order to be included in the result",
        ),
    ],
)
def freq_list_simple(
    corpus: Corpus = Corpus(),
    source_files: AllSourceFilenames = AllSourceFilenames(),
    word: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:word>"),
    pos: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:pos>"),
    baseform: AnnotationAllSourceFiles = AnnotationAllSourceFiles("<token:baseform>"),
    out: Export = Export("stats_export.frequency_list/stats_[metadata.id].csv"),
    delimiter: str = Config("stats_export.delimiter"),
    cutoff: int = Config("stats_export.cutoff"),
):
    ...
```

::: sparv.core.registry
    options:
      show_root_toc_entry: false
      members:
       - installer

**Example:**

```python
@installer(
    "Copy compressed XML to remote host",
    config=[
        Config("xml_export.export_host", description="Remote host to copy XML export to."),
        Config("xml_export.export_path", description="Path on remote host to copy XML export to."),
    ],
    uninstaller="xml_export:uninstall"
)
def install(
    corpus: Corpus = Corpus(),
    xmlfile: ExportInput = ExportInput("xml_export.combined/[metadata.id].xml.bz2"),
    out: OutputMarker = OutputMarker("xml_export.install_export_pretty_marker"),
    uninstall_marker: MarkerOptional = MarkerOptional("xml_export.uninstall_export_pretty_marker"),
    export_path: str = Config("xml_export.export_path"),
    host: str | None = Config("xml_export.export_host"),
):
    ...
```

::: sparv.core.registry
    options:
      show_root_toc_entry: false
      members:
       - uninstaller

**Example:**

```python
@uninstaller(
    "Remove compressed XML from remote host",
    config=[
        Config("xml_export.export_host", description="Remote host to remove XML export from."),
        Config("xml_export.export_path", description="Path on remote host to remove XML export from."),
    ],
)
def uninstall(
    corpus: Corpus = Corpus(),
    xmlfile: ExportInput = ExportInput("xml_export.combined/[metadata.id].xml.bz2"),
    out: OutputMarker = OutputMarker("xml_export.uninstall_export_pretty_marker"),
    install_marker: MarkerOptional = MarkerOptional("xml_export.install_export_pretty_marker"),
    export_path: str = Config("xml_export.export_path"),
    host: str | None = Config("xml_export.export_host"),
):
    ...
```

::: sparv.core.registry
    options:
      show_root_toc_entry: false
      members:
       - modelbuilder

**Example:**

```python
@modelbuilder("Sentiment model (SenSALDO)", language=["swe"])
def build_model(out: ModelOutput = ModelOutput("sensaldo/sensaldo.pickle")):
   ...
```

::: sparv.core.registry
    options:
      show_root_toc_entry: false
      members:
       - wizard

**Example:**

```python
@wizard(["export.source_annotations"], source_structure=True)
def import_wizard(answers, structure: SourceStructureParser):
    ...
```
