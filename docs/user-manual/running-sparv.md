# Running Sparv
Sparv is run from the command line. Typically you will want to run Sparv from within a corpus directory containing some
text documents (the corpus) and a [corpus config file](user-manual/corpus-configuration.md). A typical corpus folder
structure could look like this:

```
mycorpus/
├── config.yaml
└── source
    ├── document1.xml
    ├── document2.xml
    └── document3.xml
```

When trying out Sparv for the first time we recommend that you download and test run some of the [example
corpora](https://github.com/spraakbanken/sparv-pipeline/releases/latest/download/example_corpora.zip).

When running `sparv` (or `sparv -h`) the available sparv commands will be listed:
```
Annotating a corpus:
    run              Annotate a corpus and generate export files
    install          Annotate and install a corpus on remote server
    clean            Remove output directories

Inspecting corpus details:
    config           Display the corpus config
    files            List available corpus documents (input for Sparv)

Show annotation info:
    modules          List available modules and annotations
    presets          List available annotation presets
    classes          List available annotation classes

Setting up the Sparv pipeline:
    setup            Set up the Sparv data directory
    wizard           Run config wizard to create a corpus config
    build-models     Download and build the Sparv models

Advanced commands:
    run-rule         Run specified rule(s) for creating annotations
    create-file      Create specified file(s)
    run-module       Run annotator module independently
```

Every command in the Sparv command line interface has a help text which can be accessed with the `-h` flag. Below we
will give an overview for the most important commands in Sparv.

## Annotating a Corpus
**`sparv run`:** From inside a corpus directory with a config file you can annotate the corpus using `sparv run`. This
will start the annotation process and produce all the output formats (or exports) listed under `export.default` in your
config. You can also tell Sparv explicitely what output format to generate, e.g. `sparv run csv_export:csv`. Type `sparv
run -l` to learn what output formats there are available for your corpus. The output files will be stored in a folder
called `exports` inside your corpus directory.

**`sparv install`:** Installing a corpus means deploying it on a remote server. Sparv supports deployment of compressed
XML exports, CWB data files and SQL data. If you try to install a corpus Sparv will check if the necessary annotations
have been created. If any annotations are lacking, Sparv will run them for you. Thus you do not need to annotate the
corpus before installing. You can list the available installations with `sparv install -l`.

**`sparv clean`:** When annotating Sparv will create a folder called `annotations` inside your corpus directory. You
usually don't need to touch the files stored here. Leaving this directory as it is will usually lead to faster
processing of your corpus if you for example want to add a new output format. However, if you would like to delete this
folder (e.g. because you want to save disk space or because you want to rerun all annotations from scratch) you can do
so by running this command. The export directory and log files can also be removed with the `clean` command. Check out
the available options to learn more.

## Show Annotation Info
**`sparv modules`:** List available modules and annotations.

**`sparv presets`:** List available annotation presets available for your corpus. You can read more about presets in the
[section about annotation presets](user-manual/corpus-configuration.md#annotation-presets).

**`sparv classes`:** List available annotation classes. You can read more about classes in the [section about annotation
classes](user-manual/corpus-configuration.md#annotation-classes).

## Inspecting Corpus Details
**`sparv config`:** This command lets you inspect the configuration for your corpus. You can read more about this in the
[section about corpus configuration](user-manual/corpus-configuration.md).

**`sparv files`:** By using this command you can list all available input documents belonging to your corpus.

## Setting up the Sparv Pipeline
**`sparv setup`** and **`sparv build-models`:** These commands are explained in the section [Setting up
Sparv](user-manual/installation-and-setup.md#setting-up-sparv).

## Advanced Commands
**`sparv run-rule`** and **`sparv create-file`:** Instruct Sparv to run the specified annotation rule or to create
the specified file. Multiple arguments can be supplied.

Example running the part-of-speech annotation for all input files:
```bash
sparv run-rule hunpos:postag
```

Example creating the part-of-speech annotation for the input file `document1`:
```bash
sparv create-file annotations/dokument1/segment.token/hunpos.pos
```

**`sparv run-module`:** Run an annotator module independently (mostly for debugging). You must supply the module and the
function you want to run and all the mandatory arguments. E.g. to run the hunpos msd tagging module on the input file
called `document1` you could use the following command:
```bash
sparv run-module hunpos msdtag --out segment.token:hunpos.msd --word segment.token:misc.word --sentence segment.sentence --binary hunpos-tag --model hunpos/suc3_suc-tags_default-setting_utf8.model --morphtable hunpos/saldo_suc-tags.morphtable --patterns hunpos/suc.patterns --doc dokument1
```
