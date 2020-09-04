
# Installation and Setup
This section describes how to get the Sparv corpus pipeline developed by [Språkbanken][1] up and running on your own
machine. It also describes additional software that you may need to install in order to run all the analyses provided
through Sparv.

## Installing Sparv
In order to install Sparv you will need a Unix-like environment (e.g. Linux, OS X) with [Python 3.6](http://python.org/)
or newer installed on it.

The Sparv pipeline can be installed using [pip](https://pip.pypa.io/en/stable/installing):
    
    pip install --user sparv-pipeline


Alternatively you can install Sparv from the latest release from GitHub with pipx:


    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    pipx install https://github.com/spraakbanken/sparv-pipeline/archive/latest.tar.gz


## Setting up Sparv
To check if your installation of Sparv was successful you can type `sparv` on your command line. The Sparv help should
now be displayed.

<a name="datadir"></a>Sparv needs access to a directory on your system where it can store data, such as language models
and configuration files. This is called the Sparv data directory. By running `sparv setup` you can tell Sparv where to
set up its data directory.

If you like you can pre-build the model files. This step is optional and the only advantage is that annotating corpora
will be quicker once all the models are set up. If you skip this step, models will be downloaded and built automatically
on demand when annotating your first corpus. Pre-building models can be done by running `sparv build-models`. If you do
this in a directory where there is no [corpus config](#corpus_config) you have to tell Sparv what language the models
should be built for (otherwise the language of the corpus config is chosen automatically). The language is provided as a
three-letter code with the `--language` flag (check [this table](#language_table) for available languages and their
codes). For example, if you would like to build all the Swedish models you can run `sparv build-models --language swe`.

## Installing additional Third-party Software
The Sparv Pipeline is typically used together with several plugins and third-party software. Which of these you will
need to install depends on what analyses you want to run with Sparv. Please note that different licenses may apply for
different software.

Unless stated otherwise in the instructions below, you won't have to download any additional language models or
parameter files. If the software is installed correctly, Sparv will download and install the necessary model files for
you prior to annotating data.

### Hunpos
[Hunpos](http://code.google.com/p/hunpos/) is used for Swedish part-of-speech tagging and it is a prerequisite for many
other annotations, such as all of the SALDO annotations. Hunpos can be downloaded from
[here](http://code.google.com/p/hunpos/). Installation is done by unpacking and then adding the executables to your path
(you will need at least `hunpos-tag`). Alternatively you can place the binaries inside your [Sparv data
directory](#datadir) under `bin/hunpos`.

If you are running a 64-bit OS, you might also have to install 32-bit compatibility libraries if Hunpos won't run:

    sudo apt install ia32-libs

On Arch Linux, activate the `multilib` repository and install `lib32-gcc-libs`. If that doesn't work, you might have to
compile Hunpos from source.

### MaltParser
[MaltParser](http://www.maltparser.org/download.html) is used for Swedish dependency parsing. You will need
[Java][2] in order to run MaltParser.
The MaltParser version compatible with the Sparv pipeline is 1.7.2. Download and unpack the zip-file from the
[MaltParser home page](http://www.maltparser.org/download.html) and place the `maltparser-1.7.2` folder inside the `bin`
folder of the [Sparv data directory](#datadir). 

### Sparv wsd
The [Sparv-wsd](https://github.com/spraakbanken/sparv-wsd) is used for Swedish word-sense disambiguation. It is
developed at Språkbanken and runs under the same license as the Sparv pipeline. In order to use it within the Sparv
Pipeline it is enough to download the [saldowsd.jar from
GitHub](https://github.com/spraakbanken/sparv-wsd/raw/master/bin/saldowsd.jar) and place it inside your [Sparv data
directory](#datadir) under `bin/wsd`. You will need
[Java][2] in order to run word-sense
disambiguation.

### hfst-SweNER
The current version of [hfst-SweNER](http://www.ling.helsinki.fi/users/janiemi/finclarin/ner/hfst-swener-0.9.3.tgz)
expects to be run in a Python 2 environment while the Sparv pipeline is written in Python 3. Before installing
hfst-SweNER you need make sure that it will be run with the correct version of Python by replacing `python` with
`python2` in all the Python scripts in the `hfst-swener-0.9.3/scripts` directory. The first line in every script will
then look like this:

    #! /usr/bin/env python2

On Unix systems this can be done by running the following command from whithin the `hfst-swener-0.9.3/scripts`
directory:

    sed -i 's:#! \/usr/bin/env python:#! /usr/bin/env python2:g' *.py

After applying these changes please follow the installation instructions provided by hfst-SweNER.

### Corpus Workbench
TODO! Refer to Korp's instructions?

### Software for analysing other languages
Sparv can use different third-party software for analyzing corpora in other languages than Swedish.

<a name="language_table"></a>The following is a list over the languages currently supported by the corpus pipeline,
their language codes (ISO 639-3) and which tools Sparv can use to analyze them:

Language       |Code       |Analysis Tool
:--------------|:----------|:-------------
Asturian       |ast        |FreeLing
Bulgarian      |bul        |TreeTagger
Catalan        |cat        |FreeLing
Dutch          |nld        |TreeTagger
Estonian       |est        |TreeTagger
English        |eng        |FreeLing, Stanford Parser, TreeTagger
French         |fra        |FreeLing, TreeTagger
Finnish        |fin        |TreeTagger
Galician       |glg        |FreeLing
German         |deu        |FreeLing, TreeTagger
Italian        |ita        |FreeLing, TreeTagger
Latin          |lat        |TreeTagger
Norwegian      |nob        |FreeLing
Polish         |pol        |TreeTagger
Portuguese     |por        |FreeLing
Romanian       |ron        |TreeTagger
Russian        |rus        |FreeLing, TreeTagger
Slovak         |slk        |TreeTagger
Slovenian      |slv        |FreeLing
Spanish        |spa        |FreeLing, TreeTagger
Swedish        |swe        |Sparv

<!-- Swedish 1800's |sv-1800   |Sparv) -->
<!-- Swedish development mode |sv-dev    |Sparv) -->


#### TreeTagger
Version 3.2.3 of [TreeTagger](http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/) is compatible with Sparv (it may
work with newer versions, too). After downloading the software you need to have the `tree-tagger` binary in your path.
Alternatively you can place the `tree-tagger` binary file in the [Sparv data directory](#datadir) under
`bin/treetagger`.

#### Stanford Parser
Version 4.0.0 of [Stanford CoreNLP](https://stanfordnlp.github.io/CoreNLP/history.html) is compatible with Sparv (it may
work with newer versions, too). Please download, unzip and place contents inside the [Sparv data directory](#datadir)
under `bin/stanford_parser`. Stanford CoreNLP runs under the [GPL2
license](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html). You will need [Java][2] in order to run the Stanford
Parser.

#### FreeLing
[FreeLing](https://github.com/TALP-UPC/FreeLing/releases/tag/4.2) Please install the software according to the
instructions provided by FreeLing.

In order to use Freeling you will need to install the sparv-freeling plugin which is available via
[GitHub](https://github.com/spraakbanken/sparv-freeling) and runs under the [AGPL
license](http://www.gnu.org/licenses/agpl.html). Follow the installation instructions for the sparv-freeling module on
GitHub in order to set up the plugin correctly.

## Plugins
The only available plugin for Sparv available so far is [the sparv-freeling
plugin](https://github.com/spraakbanken/sparv-freeling). Please refer to its GitHub page for installation instructions.


# <a name="corpus_config"></a>Corpus Configuration

TODO!

* how/where to download test corpora and corpus configs?

- Config options that must be set:
  - classes.token
  - classes.sentence
  - classes.text

- Tipsa om att man kan konvertera strukturella attribut till ordattribut (till exempel NER). Det är praktiskt för csv-exporten!

- Om man listar element i `original_annotations` måste man också lägga in ett rot-element för varje dokument (element that encloses all other included elements and text content)

- How do headers work?

## Corpus Config Wizard
TODO!

# Running Sparv
When running `sparv` (or `sparv -h`) the available sparv commands will be listed:

    Annotating a corpus:
        run              Annotate a corpus and generate export files
        install          Annotate and install a corpus on remote server
        clean            Remove output directories
    
    Inspecting corpus details:
        config           Display the corpus config
        files            List available corpus documents (input for Sparv)
    
    Setting up the Sparv pipeline:
        setup            Set up the Sparv data directory
        build-models     Download and build the Sparv models
    
    Advanced commands:
        run-rule         Run specified rule(s) for creating annotations
        create-file      Create specified file(s)
        run-module       Run annotator module independently
        annotations      List available modules, annotations, and classes
        presets          List available annotation presets

You can learn more about a command by using it together with the `-h` flag, e.g.

    sparv run -h
    usage: sparv run [-h] [-l] [-n] [-j N] [-d DOC [DOC ...]] [--log [LOGLEVEL]] [--log-to-file [LOGLEVEL]]
                    [--debug]
                    [output [output ...]]

    Annotate a corpus and generate export files.

    positional arguments:
    output                The type of output format to generate

    optional arguments:
    -h, --help            Show this help message and exit
    -l, --list            List available output formats
    -n, --dry-run         Only dry-run the workflow
    -j N, --cores N       Use at most N cores in parallel
    -d DOC [DOC ...], --doc DOC [DOC ...]
                            Only annotate specified input document(s)
    --log [LOGLEVEL]      Set the log level (default: 'warning')
    --log-to-file [LOGLEVEL]
                            Set log level for logging to file (default: 'warning')
    --debug               Show debug messages

Typically you will want to run Sparv from within a corpus directory containing some text documents (the corpus) and a
corpus and a [corpus configuration file](#corpus_config). A typical corpus folder structure could look like this:

    mycorpus/
    ├── config.yaml
    └── source
        ├── document1.xml
        ├── document2.xml
        └── document3.xml

TODO!

# Custom Rules
TODO!
- How do custom rules work?
- Använd enkelfnuttar för regex-strängar i YAML!

# MISC
TODO!
- List and explain the segmeters available in `segment.py`




<!-- Links -->
[1]: https://spraakbanken.gu.se/
[2]: http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html
