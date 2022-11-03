# Running Sparv
Sparv is run from the command line. Typically, you will want to run Sparv from within a corpus directory containing some
text files (the corpus) and a [corpus config file](user-manual/corpus-configuration.md). A typical corpus directory
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
    files            List available corpus source files (input for Sparv)

Show annotation info:
    modules          List available modules and annotations
    presets          List available annotation presets
    classes          List available annotation classes
    languages        List supported languages

Setting up the Sparv Pipeline:
    setup            Set up the Sparv data directory
    wizard           Run config wizard to create a corpus config
    build-models     Download and build the Sparv models (optional)

Advanced commands:
    run-rule         Run specified rule(s) for creating annotations
    create-file      Create specified file(s)
    run-module       Run annotator module independently
    preload          Preload annotators and models
```

Every command in the Sparv command line interface has a help text which can be accessed with the `-h` flag. Below we
will give an overview of the most important commands in Sparv.

## Annotating a Corpus
**`sparv run`:** From inside a corpus directory with a config file you can annotate the corpus using `sparv run`. This
will start the annotation process and produce all the output formats (or _exports_) listed under `export.default` in
your config. You can also tell Sparv explicitly what output format to generate, e.g. `sparv run csv_export:csv`.
Type `sparv run -l` to learn what output formats there are available for your corpus. The output files will be
stored in a directory called `export` inside your corpus directory.

**`sparv install`:** Installing a corpus means deploying it in some way, either locally or on a remote server. Sparv
supports deployment of compressed XML exports, CWB data files and SQL data. If you try to install a corpus, Sparv will
check if the necessary annotations have been created. If any annotations are missing, Sparv will run them for you.
Therefore, you do not need to annotate the corpus before installing. You can list the available installation options
with `sparv install -l`.

**`sparv clean`:** While annotating, Sparv will create a directory called `sparv-workdir` inside your corpus directory.
You normally don't need to touch the files stored here. Leaving this directory as it is will usually lead to faster
processing of your corpus if you for example want to add a new output format. However, if you would like to delete this
directory (e.g. because you want to save disk space or because you want to rerun all annotations from scratch) you
can do so by running `sparv clean`. The export directory and log files can also be removed with the `clean` command
by adding appropriate flags. Check out the available options (`sparv clean -h`) to learn more.

## Show Annotation Info
**`sparv modules`:** List available modules and annotations.

**`sparv presets`:** List available annotation presets available for your corpus. You can read more about presets in the
[section about annotation presets](user-manual/corpus-configuration.md#annotation-presets).

**`sparv classes`:** List available annotation classes. You can read more about classes in the [section about annotation
classes](user-manual/corpus-configuration.md#annotation-classes).

**`sparv languages`:** List supported languages.

## Inspecting Corpus Details
**`sparv config`:** This command lets you inspect the configuration for your corpus. You can read more about this in the
[section about corpus configuration](user-manual/corpus-configuration.md).

**`sparv files`:** By using this command you can list all available source files belonging to your corpus.

## Setting Up the Sparv Pipeline
**`sparv setup`** and **`sparv build-models`:** These commands are explained in the section [Setting Up
Sparv](user-manual/installation-and-setup.md#setting-up-sparv).

## Advanced Commands
**`sparv run-rule`** and **`sparv create-file`:** Instruct Sparv to run the specified annotation rule or to create
the specified file. Multiple arguments can be supplied.

Example running the Stanza annotations (part-of-speech tagging and dependency parsing) for all input files:
```
sparv run-rule stanza:annotate
```

Example creating the part-of-speech annotation for the input file `document1`:
```
sparv create-file sparv-workdir/dokument1/segment.token/stanza.pos
```

**`sparv run-module`:** Run an annotator module independently (mostly for debugging). You must supply the module and the
function you want to run and all the mandatory arguments. E.g. to run the hunpos msd tagging module on the input file
called `document1` you could use the following command:
```
sparv run-module hunpos msdtag --out segment.token:hunpos.msd --word segment.token:misc.word --sentence segment.sentence --binary hunpos-tag --model hunpos/suc3_suc-tags_default-setting_utf8.model --morphtable hunpos/saldo_suc-tags.morphtable --patterns hunpos/suc.patterns --encoding UTF-8 --source_file dokument1
```

**`sparv preload`:** This command preloads annotators and their models and/or related binaries to speed up
annotation.
This is especially useful when annotating multiple smaller source files, where every model otherwise would have to
be loaded as many times as there are source files. Not every annotator supports preloading; use the `--list`
argument to see which annotators are supported.

The Sparv preloader can be run from anywhere as long as there is a `config.yaml` file in the same directory.
While the file follows the same format as all corpus configuration files, it doesn't necessarily have to be tied to a
corpus. All that is required is a `preload:` section, with a list of annotators to preload (from the list given by
the command above).
The listed annotators will be loaded using the settings in the configuration file (in combination with default settings,
as usual).

The Sparv preloader may be shared between several corpora,
as long as the configuration for the annotators doesn't differ (e.g. what models are used).
Sparv will automatically fall back to not using the preloader for a certain annotator if it detects that the preloaded
version is using a different configuration from what is needed for the corpus.

The preloader uses socket files for communication. Use the `--socket` argument to provide a path to the socket file
to create. If omitted, the default `sparv.socket` will be used.

The `--processes` argument tells Sparv how many parallel processes to start. If possible, use as many processes as you
plan on using when running Sparv (e.g. `sparv run -j 4`), or the preloader might become a bottleneck instead of
speeding things up.

Example of starting the preloader with four parallel processes:
```
sparv preload --socket my_socket.sock --processes 4
```

Once the preloader is up and running, use another terminal to annotate your corpus. To make Sparv use the preloader when
annotating, use the `--socket` argument and point it to the same socket file created by the preloader. For example:
```
sparv run --socket my_socket.sock
```

If the preloader is busy, by default Sparv will execute annotators the regular way without using the preloader. If you
would rather have Sparv wait for the preloader, use the `--force-preloader` flag with the `run` command.

To shut down the preloader, either press Ctrl-C in the preloader terminal, or use the command `sparv preload stop`
while pointing it to the relevant socket. For example:

```
sparv preload stop --socket my_socket.sock
```
