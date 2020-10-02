**Table of Contents**
<!-- Generate table of contents: https://ecotrust-canada.github.io/markdown-toc/ -->

- [Installation and Setup](#installation-and-setup)
  * [Installing Sparv](#installing-sparv)
  * [Setting up Sparv](#setting-up-sparv)
  * [Installing Additional Third-party Software](#installing-additional-third-party-software)
    + [Hunpos](#hunpos)
    + [MaltParser](#maltparser)
    + [Sparv wsd](#sparv-wsd)
    + [hfst-SweNER](#hfst-swener)
    + [Corpus Workbench](#corpus-workbench)
    + [Software for Analysing other Languages](#software-for-analysing-other-languages)
      - [TreeTagger](#treetagger)
      - [Stanford Parser](#stanford-parser)
      - [FreeLing](#freeling)
  * [Plugins](#plugins)
- [Running Sparv](#running-sparv)
  * [Annotating a Corpus](#annotating-a-corpus)
  * [Inspecting Corpus Details](#inspecting-corpus-details)
  * [Setting up the Sparv Pipeline](#setting-up-the-sparv-pipeline)
  * [Advanced Commands](#advanced-commands)
- [Requirements for Input Data](#requirements-for-input-data)
- [Corpus Configuration](#corpus-configuration)
  * [Corpus Config Wizard](#corpus-config-wizard)
  * [Default Values](#default-values)
  * [Import Options](#import-options)
  * [Export Options](#export-options)
  * [Headers](#headers)
  * [Annotation Classes](#annotation-classes)
  * [Annotation Presets](#annotation-presets)
  * [Custom Annotations](#custom-annotations)
    + [Built-in Custom Annotations](#built-in-custom-annotations)
    + [Modifying Annotators with Custom Annotations](#modifying-annotators-with-custom-annotations)
    + [User-defined Custom Annotations](#user-defined-custom-annotations)
- [MISC](#misc)


# Installation and Setup
This section describes how to get the Sparv corpus pipeline developed by [Språkbanken][1] up and running on your own
machine. It also describes additional software that you may need to install in order to run all the analyses provided
through Sparv.

## Installing Sparv
In order to install Sparv you will need a Unix-like environment (e.g. Linux, OS X) with [Python 3.6](http://python.org/)
or newer installed on it.

The Sparv pipeline can be installed using [pip](https://pip.pypa.io/en/stable/installing). We even recommend using
[pipx](https://pipxproject.github.io/pipx/) so that you can install the `sparv` command globally:
```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install sparv-pipeline
```

Alternatively you can install Sparv from the latest release from GitHub:
```bash
pipx install https://github.com/spraakbanken/sparv-pipeline/archive/latest.tar.gz
```

## Setting up Sparv
To check if your installation of Sparv was successful you can type `sparv` on your command line. The Sparv help should
now be displayed.

<a name="datadir"></a>Sparv needs access to a directory on your system where it can store data, such as language models
and configuration files. This is called the *Sparv data directory*. By running `sparv setup` you can tell Sparv where to
set up its data directory.

If you like you can pre-build the model files. This step is optional and the only advantage is that annotating corpora
will be quicker once all the models are set up. If you skip this step, models will be downloaded and built automatically
on demand when annotating your first corpus. Pre-building models can be done by running `sparv build-models`. If you do
this in a directory where there is no [corpus config](#corpus-configuration) you have to tell Sparv what language the models
should be built for (otherwise the language of the corpus config is chosen automatically). The language is provided as a
three-letter code with the `--language` flag (check [this table](#language_table) for available languages and their
codes). For example, if you would like to build all the Swedish models you can run `sparv build-models --language swe`.

## Installing Additional Third-party Software
The Sparv Pipeline is typically used together with several plugins and third-party software. Which of these you will
need to install depends on what analyses you want to run with Sparv. Please note that different licenses may apply for
different software.

Unless stated otherwise in the instructions below, you won't have to download any additional language models or
parameter files. If the software is installed correctly, Sparv will download and install the necessary model files for
you prior to annotating data.

### Hunpos
|                                  |           |
|:---------------------------------|:----------
|**Purpose**                       |Swedish part-of-speech tagging (prerequisite for many other annotations, such as all of the SALDO annotations)
|**Download**                      |[Hunpos on Google Code](https://code.google.com/archive/p/hunpos/downloads)
|**License**                       |[BSD-3](https://opensource.org/licenses/BSD-3-Clause)
|**Version compatible with Sparv** |latest (1.0)

Installation is done by unpacking and then adding the executables to your path
(you will need at least `hunpos-tag`). Alternatively you can place the binaries inside your [Sparv data
directory](#datadir) under `bin`.

If you are running a 64-bit OS, you might also have to install 32-bit compatibility libraries if Hunpos won't run:
```bash
sudo apt install ia32-libs
```
On Arch Linux, activate the `multilib` repository and install `lib32-gcc-libs`. If that doesn't work, you might have to
compile Hunpos from source.

### MaltParser
|                                  |           |
|:---------------------------------|:----------
|**Purpose**                       |Swedish dependency parsing
|**Download**                      |[MaltParser webpage](http://www.maltparser.org/download.html)
|**License**                       |[MaltParser license](http://www.maltparser.org/license.html) (open source)
|**Version compatible with Sparv** |1.7.2
|**Dependencies**          		   |[Java][2]

Download and unpack the zip-file from the [MaltParser webpage](http://www.maltparser.org/download.html) and place the
`maltparser-1.7.2` folder inside the `bin` folder of the [Sparv data directory](#datadir).

### Sparv wsd
|                                  |           |
|:---------------------------------|:----------
|**Purpose**                       |Swedish word-sense disambiguation
|**Download**                      |[Sparv wsd](https://github.com/spraakbanken/sparv-wsd/raw/master/bin/saldowsd.jar)
|**License**                       |[MIT](https://opensource.org/licenses/MIT)
|**Dependencies**          		   |[Java][2]

[Sparv wsd](https://github.com/spraakbanken/sparv-wsd) is
developed at Språkbanken and runs under the same license as the Sparv pipeline. In order to use it within the Sparv
Pipeline it is enough to download the saldowsd.jar from
GitHub (see downloadlink above) and place it inside your [Sparv data
directory](#datadir) under `bin/wsd`.

### hfst-SweNER
|                                  |           |
|:---------------------------------|:----------
|**Purpose**                       |Swedish named-entity recognition
|**Download**                      |[hfst-SweNER](http://www.ling.helsinki.fi/users/janiemi/finclarin/ner/hfst-swener-0.9.3.tgz)
|**Version compatible with Sparv** |0.9.3

The current version of hfst-SweNER expects to be run in a Python 2 environment while the Sparv pipeline is written in
Python 3. Before installing hfst-SweNER you need make sure that it will be run with the correct version of Python by
replacing `python` with `python2` in all the Python scripts in the `hfst-swener-0.9.3/scripts` directory. The first line
in every script will then look like this:
```python
#! /usr/bin/env python2
```
On Unix systems this can be done by running the following command from whithin the `hfst-swener-0.9.3/scripts`
directory:
```bash
sed -i 's:#! \/usr/bin/env python:#! /usr/bin/env python2:g' *.py
```

After applying these changes please follow the installation instructions provided by hfst-SweNER.

### Corpus Workbench
|                                  |           |
|:---------------------------------|:----------
|**Purpose**                       |Creating corpus workbench binary files. You will only need it if you want to be able to search corpora with this tool.
|**Download**                      |[Corpus Workbench on SourceForge](http://cwb.sourceforge.net/beta.php)
|**License**                       |[GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html)
|**Version compatible with Sparv** |beta 3.4.21 (probably works with newer versions)

Refer to the INSTALL text file for instructions on how to build and install on your system. CWB needs two directories
for storing the corpora, one for the data, and one for the corpus registry. You will have to create these directories
and you will have to set the environment variables `CWB_DATADIR` and `CORPUS_REGISTRY` and point them to the directories
you created. For example:
```bash
export CWB_DATADIR=~/cwb/data;
export CORPUS_REGISTRY=~/cwb/registry;
```

### Software for Analysing other Languages
Sparv can use different third-party software for analyzing corpora in other languages than Swedish.

<a name="language_table"></a>The following is a list over the languages currently supported by the corpus pipeline,
their language codes (ISO 639-3) and which tools Sparv can use to analyze them:

Language       |ISO Code   |Analysis Tool
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
|                                  |           |
|:---------------------------------|:----------
|**Purpose**                       |POS-tagging and lemmatisation for [some languages](#language_table)
|**Download**                      |[TreeTagger webpage](http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/)
|**License**                       |[TreeTagger license](https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/Tagger-Licence) (freely available for research, education and evaluation)
|**Version compatible with Sparv** |3.2.3 (may work with newer versions)

After downloading the software you need to have the `tree-tagger` binary in your path. Alternatively you can place the
`tree-tagger` binary file in the [Sparv data directory](#datadir) under `bin    `.

#### Stanford Parser
|                                  |           |
|:---------------------------------|:----------
|**Purpose**                       |Various analyses for English
|**Download**                      |[Stanford CoreNLP webpage](https://stanfordnlp.github.io/CoreNLP/history.html)
|**Version compatible with Sparv** |4.0.0 (may work with newer versions)
|**License**                       |[GPL-2.0](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
|**Dependencies**          		   |[Java][2]

Please download, unzip and place contents inside the [Sparv data directory](#datadir) under `bin/stanford_parser`.

#### FreeLing
|                                  |           |
|:---------------------------------|:----------
|**Purpose**                       |Tokenisation, POS-tagging, lemmatisation and named entity recognition for [some languages](#language_table)
|**Download**                      |[FreeLing on GitHub](https://github.com/TALP-UPC/FreeLing/releases/tag/4.2)
|**Version compatible with Sparv** |4.2
|**License**                       |[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.en.html)

Please install the software (including the additional language data) according to the instructions provided by FreeLing.
You will also need to install the [sparv-freeling plugin](https://github.com/spraakbanken/sparv-freeling). Please follow
the installation instructions for the sparv-freeling module on [GitHub](https://github.com/spraakbanken/sparv-freeling)
in order to set up the plugin correctly.

<!-- #### fast_align
|                                  |           |
|:---------------------------------|:----------
|**Purpose**                       |word-linking on parallel corpora
|**Download**                      |[fast_align on GitHub](https://github.com/clab/fast_align)
|**License**                       |[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)

Please follow the installation instructions given in the fast_align repository and make sure to have the binaries
`atools` and `fast_align` in your path. Alternatively you can place them in the [Sparv data directory](#datadir) under
`bin/word_alignment`. -->


## Plugins
The only available plugin for Sparv available so far is [the sparv-freeling
plugin](https://github.com/spraakbanken/sparv-freeling). Please refer to its GitHub page for installation instructions.


# Running Sparv
Sparv is run from the command line. Typically you will want to run Sparv from within a corpus directory containing some
text documents (the corpus) and a corpus and a [corpus config file](#corpus-configuration). A typical corpus folder
structure could look like this:

    mycorpus/
    ├── config.yaml
    └── source
        ├── document1.xml
        ├── document2.xml
        └── document3.xml

When trying out Sparv for the first time we recommend that you download and test run some of the [example corpora][3].

When running `sparv` (or `sparv -h`) the available sparv commands will be listed:
```
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
```

Every command in the Sparv command line interface (CLI) has a help text which can be accessed with the `-h` flag. Below
we will give an overview for the most important commands in Sparv. 

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

## Inspecting Corpus Details
**`sparv config`:** This command lets you inspect the configuration for your corpus. You can read more about this in the
[section about corpus configuration](#corpus-configuration).

**`sparv files`:** By using this command you can list all available input documents belonging to your corpus.

## Setting up the Sparv Pipeline
**`sparv setup`** and **`sparv build-models`:** These commands are explained in the section [Setting up
Sparv](#setting-up-sparv).

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

**`sparv annotations`:** List all available modules, annotations, and classes.

**`sparv presets`:** List available annotation presets available for your corpus. You can read more about presets in the
[section about annotation presets](#annotation-presets).

# Requirements for Input Data
**TODO**
- valid XML where the text to be analyzed is actual text (not attribute values) in the XML
- document size?
- no elements/attributes called "not"
- make sure to not have `annotations` or `export` dir in corpus dir


# Corpus Configuration
To be able to annotate a corpus with Sparv you will need to create a corpus config file. A corpus config file is written
in [YAML](https://docs.ansible.com/ansible/latest/reference_appendices/YAMLSyntax.html), a fairly human-readable format
for creating structured data. This file contains information about your corpus (metadata) and instructions for Sparv on
how to process it. The [corpus config wizard](#corpus-config-wizard) can help you create one. If you want to see some
examples of config files you can download the [example corpora][3].

A minimal config file contains a corpus ID, information about which XML element is regarded the document element
(**TODO**: what if the input is not XML?) and a list of (automatic) annotations you want to be included in the output.
Here is an example of a small config file:

```yaml
metadata:
    # Corpus ID (Machine name, only lower case ASCII letters (a-z) and "-" allowed. No white spaces.)
    id: mini-swe
import:
    # The element representing one text document. Text-level annotations will be made on this element.
    document_element: text
export:
    # Automatic annotations to be included in the export
    annotations:
        - <sentence>:misc.id
        - <token>:saldo.baseform
        - <token>:hunpos.pos
        - <token>:sensaldo.sentiment_label
```

## Corpus Config Wizard
The corpus config wizard is a tool designed to help you create a corpus config file by asking questions about your
corpus. Run `sparv wizard` in order to start the tool. A config file that was created with the wizard can of course be
edited manually afterwards.

**TODO**

## Default Values
Some config variables such as `metadata`, `classes`, `import`, `export` and `custom_annotations` are general and are
used by multiple Sparv modules, while others are specific to one particular annotation module (e.g. `hunpos.binary`
defines the name of the binary the hunpos module uses to run part-of-speech tagging). These module specific config
options usually have default values which are defined by the module itself.

When running Sparv your corpus config will be read and combined with Sparv's default config file (`config_default.yaml`
in the [Sparv data directory](#datadir)) and the default values defined by different Sparv modules. You can view the
resulting configuration by running `sparv config`. Using the `config` command you can also ask for specific config
values, e.g. `sparv config metadata.id`. All default values can be overridden in your own corpus config.

There are a couple of config options that must be set (either through the default config or the corpus config):
  - `metadata.id`
  - `metadata.language` (default: `swe`)
  - `import.importer` (default: `xml_import:parse`)
  - `classes.token` (default: `segment.token`)
  - `classes.sentence` (default: `segment.sentence`)
  - `classes.text`
  - `[export module].annotations`
  - **TODO** What more?


## Import Options
**TODO**
- Renaming elemets/attributes?
- source_dir
- importer
- document_element
- `skip`


## Export Options
The `export` section of your corpus config defines what the output data (or export) looks like. With the config option
`export.source_annotations` you can tell Sparv what elements and attributes present in your input data you would like to
keep in your output data (this only applies if your input data is XML). If you don't specify anything, everything will
be kept in the output. If you do list anything here, make sure that you include the root element (i.e. the element that
encloses all other included elements and text content) for each of your input files. If you don't, the resulting output
XML will be invalid and Sparv won't be able to produce XML files. If you only want to produce other output formats than
XML you don't need to worry about this.

It is possible to rename elements and attributes present in your input data. Let's say your documents contain elements
 like this `<article name="Scandinavian Furniture" date="2020-09-28">` and you would like them to look like this in the
 output `<text title="Scandinavian Furniture" date="2020-09-28">` (so you want to rename "article" and "name" to "text"
 and "title" respectively). For this you can use the following syntax:
```yaml
export:
    source_annotations:
        - article as text
        - name as title
        - ...
```
Please note that the dots (`...`) in the above example also carry meaning. You can use these to refer to all the
remaining elements and attributes in your input data. Without using the dots the "date" attribute in the example would
be lost. If you want to keep most of the markup of your input data but you want to exclude some elements or attributes
you can do this by using the `not` keyword:
```yaml
export:
    source_annotations:
        - not date
```
In the example above this would result in the following output: `<article name="Scandinavian Furniture">`.

The option `export.annotations` contains a list of automatic annotations you want Sparv to produce and include in the
output. You can run `sparv annotations` to see what annotations are available. You can also read the section about
[annotation presets](#annotation-presets) for more info about automatic annotations.

If you want to produce multiple output formats containing different annotations you can override the
`export.source_annotations` and `export.annotations` options for specific exporter modules. The annotations for the XML
export for example are set with `xml_export.source_annotations` and `xml_export.annotations`, the annotations for the
CSV export are set with `csv_export.source_annotations` and `csv_export.annotations` and so on.

**Hint:** If you want to produce multiple output formats with the same annotations you can use YAML
[anchors](https://docs.ansible.com/ansible/latest/user_guide/playbooks_advanced_syntax.html#yaml-anchors-and-aliases-sharing-variable-values)
to avoid copying and pasting the same settings.

The option `export.default` defines a list of export formats that will be produced when running `sparv run`. Per default
it only contains `xml_export:pretty`, the formatted XML export with one token per line. 

**TODO**
- export.word: <token>:some_annotation
- scramble_on: <sentence>
- remove_module_namespaces: true
- sparv_namespace: Null
- source_namespace: Null


## Headers
Sometimes corpus metadata can be stored in XML headers rather than in attributes belonging to text-enclosing elements.
Sparv can extract information from headers and store as annotations. These can then be used as input for different
analyses. Information from headers can be exported as attributes if you choose to.

Let's say we have a corpus file with the following contents:
```xml
<text id="1">
    <header>
        <author birth="1780" death="????">Anonym</author>
        <date>2020-09-08</date>
        <title>
            <main-title>A History of Corpora</main-title>
            <sub-title>A Masterpiece</sub-title>
        </title>
    </header>
    <another-header>
        <dummy>1</dummy>
    </another-header>
    Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do
    eiusmod tempor incididunt ut labore et dolore magna aliqua.
</text>
```
We want to keep the data in `<header>` but we don't want the contents to be analysed as corpus text. We want its
metadata to be attached to the `<text>` element. We want to get rid of `<another-header>` and its contents entirely.
This configuration will do the job:
```yaml
xml_import:
    header_elements:
        - header
        - another-header
    header_data:
        - header/author as text:author
        - header/author:birth as text:author-birth
        - header/author:death as text:author-death
        - header/title/main-title as text:title
        - header/title/sub-title as text:subtitle
        - header/date as text:date
export:
    header_annotations:
        - not header
        - not another-header
```
The output will look like this:
```xml
<text author="Anonym" author-birth="1780" author-death="????" date="2020-09-08"
      id="1" title="A History of Corpora" subtitle="A Masterpiece">
    <sentence id="13f">
      <token>Lorem</token>
      <token>ipsum</token>
      ...
    </sentence>
</text>
```
Of course it is possible to keep the headers in the output (without them being analysed as corpus text) by listing them
without the `not` in `export.header_annotations`. If you don't specify anything at all in `export.header_annotations`
all your headers will be kept.


## Annotation Classes
The `classes` config variable defines the annotation classes for your corpus. Annotation classes are used to create
abstract instances for common annotations such as tokens, sentences and text units. They simplify dependencies between
annotation modules and increase the flexibility of the annotation pipeline. Many annotations modules (such as
part-of-speech taggers and dependency parsers) need tokenised text as input but they might not care about what tokeniser
is being used. So instead of telling the part-of-speech tagger and the dependency parser that it needs input from a
specific module we can tell it to take the class `<token>` as input. So when setting `classes.token` to `segment.token`
we tell Sparv that tokens will be produced by the segment module. This way we can ask Sparv to perform part-of-speech
tagging and it will figure out automatically that tokenisation needs to be done first and that this is done with the
segment module. Classes may also be used in your export annotation lists. If you want to include part-of-speech tags
from hunpos you would include `segment.token:hunpos.pos` in the annotations, meaning that you want to have pos tags from
hunpos as attributes to the tokens prodcued by the segment module. Here is an example:
```yaml
export:
    annotations:
        - segment.token:hunpos.pos
        - segment.token:malt.deprel
        - segment.token:malt.dephead_ref
```
The disadvantage of this notation is that when you decide to exchange your token segmenter for a different one called
`my_new_segmenter` you would have to change all occurences of `segment.token` in your config to
`my_new_segmenter.token`. Instead of doing that you can just re-define your token class by setting `classes.token` to
`my_new_segmenter.token` and write your annotations list as follows:
```yaml
export:
    annotations:
        - <token>:hunpos.pos
        - <token>:malt.deprel
        - <token>:malt.dephead_ref
```

## Annotation Presets
When telling Sparv which automatic annotations should be included in a speficic output format you usually list them like
this:
```yaml
export:
    annotations:
        - <token>:saldo.baseform
        - <token>:saldo.lemgram
        - <token>:wsd.sense
        - <token>:saldo.compwf
        - <token>:saldo.complemgram
```

If you want to process many corpora and produce the same annotations for them it can be tedious to include the same
annotations list in every corpus config. Instead you can use annotation presets for a more compact representation:
```yaml
export:
    annotations:
        - SWE_DEFAULT.saldo
```

Here `SWE_DEFAULT.saldo` will expand to all the SALDO annotations. You can mix presets with annotations and you can
combine different presets with each other. You can find the presets in the [Sparv data directory](#datadir) (in the
`config/presets` folder) and here you can even add your own preset files if you like. You can list all available presets
for your corpus (and which annotations they include) with `sparv presets`.

It is possible to exclude specific annotations from a preset by using the `not` keyword. In the following example we are
including all SALDO annotations except for the compound analysis attributes:
```yaml
export:
    annotations:
        - SWE_DEFAULT.saldo
        - not <token>:saldo.compwf
        - not <token>:saldo.complemgram
```

**Note:** Preset files may define their own `class` default values. These will be set automatically when using a preset.
You can override these in your config files if you know what you are doing.

If you frequently run corpora through using the same annotations you can add your own presets. They will be accessible
by Sparv as soon as you store them in `config/presets` in the [Sparv data directory](#datadir).


## Custom Annotations
Custom annotations may be used to apply more customised, non-pre-defined annotations to your corpus. The different
usages of custom annotations are explained below.

### Built-in Custom Annotations
Sparv provides a couple of built-in custom annotations which need extra input from the user before they can be used.
These are listed under "Available custom annotation functions" when running `sparv annotations`. Please note that custom
annotations always result in new annotations, they do not modify existing ones. 

The `misc:affix` annotation for example can be used to add a prefix and/or a suffix string to another annotation. When
using this annotation function you must tell Sparv 1. what your output annotation should be called, 2. what annotation
you want to use as input (the chunk), and 3. the string that you want to use as prefix and/or the suffix. These things
are defined in the `custom_annotations` section in your corpus config. First you specify the annotator module
(`annotator`) and function you want to use and then you list the parameter names (`params`) and their values. In this
example we are using the word annotation as input and adding the string "|" as prefix and suffix.
```yaml
custom_annotations:
    - annotator: misc:affix
      params:
          out: <token>:misc.word.affixed
          chunk: <token:word>
          prefix: "|"
          suffix: "|"
```

In order to use this annotation you need to add `<token>:misc.word.affixed` to an annotations list in your corpus config
(e.g. `xml_export.annotations`). This example is applied in the standard-swe example corpus.

You can use the same custom annotation function multiple times as long as you name the outputs differently:
```yaml
custom_annotations:
    - annotator: misc:affix
      params:
          out: <token>:misc.word.affixed
          chunk: <token:word>
          prefix: "|"
          suffix: "|"
    - annotator: misc:affix
      params:
          out: <token>:misc.word.affixed2
          chunk: <token:word>
          prefix: "+"
          suffix: "+"
```

**Hint:** When using a regular expression as input for a custom rule (e.g. in `misc:find_replace_regex`), the expression
must be surrounded by single quotation marks. Regular expressions inside double quotation marks in YAML are not parsed
correctly.

### Modifying Annotators with Custom Annotations
Custom annotations may also be used to modify the parameters of existing annotation functions. This comes in handy when
you want to use the same annotator multiple times but with different models. In order to do this you specify the
annotator and its parameters in the `custom_annotations` section of your corpus config as explained in the section
above. You only need to specify the parameters you want to modify. In the example below we are re-using the
`hunpos:msdtag` function with a custom model and we are calling the output annotation
`<token>:hunpos.msd.myHunposModel`:
```yaml
custom_annotations:
    - annotator: hunpos:msdtag
      params:
          out: <token>:hunpos.msd.myHunposModel
          model: path/to/myHunposModel
```

### User-defined Custom Annotations
User-defined custom annotations are useful when you want to write your own python annotation function and plug it into
Sparv. Your annotation function must have one of the sparv decorators (usually `@annotator`) and your annotator must be
declared in the `custom_annotations` section of your corpus config. Place your python code inside your corpus directory
and Sparv will be able to find it. There is an example of a user-defined custom annotation in the standard-swe example
corpus. The code for a simple annotator that converts all tokens to upper case looks like this:

```python
from sparv import Annotation, Output, annotator

@annotator("Convert every word to uppercase.")
def uppercase(word: Annotation = Annotation("<token:word>"),
              out: Output = Output("<token>:custom.convert.upper")):
    """Convert to uppercase."""
    out.write([val.upper() for val in word.read()])
```

The custom rule is then declared in your corpus config using the prefix `custom` before the annotator name:
```yaml
custom_annotations:
    - annotator: custom.convert:uppercase
```

In this example all parameters in the annotator function have default values which means that you do not need to supply
any parameter values in your config. But of course you can override the default values:
```yaml
custom_annotations:
    - annotator: custom.convert:uppercase
      params:
          out: <token>:custom.convert.myUppercaseAnnotation
```

Now you can add the annotation name given by the `out` parameter value to an annotations list in your corpus config
(e.g. `xml_export.annotations`). Please note that when using custom annotations from your own code all output
annotations must be prefixed with `custom`.

If you need more information on how to write an annotation function please refer to the [developer's guide][4]. If you
have written a rater general annotation module you could consider writing a Sparv plugin. This way others will be able
to use your annotator. Read more about writing plugins in the [developer's guide][4].


# MISC
**TODO**
- List and explain the segmenters available in `segment.py`?
- Tipsa om att man kan konvertera strukturella attribut till ordattribut (till exempel NER). Det är praktiskt för csv-exporten!



<!-- Links -->
[1]: https://spraakbanken.gu.se/
[2]: http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html
[3]: https://github.com/spraakbanken/sparv-pipeline/releases/download/v4.0/example_corpora.zip
[4]: TODO: link to developer's guide
