# Installation and Setup
This section describes how to get the Sparv corpus pipeline developed by [Språkbanken](https://spraakbanken.gu.se/) up
and running on your own machine. It also describes additional software that you may need to install in order to run all
the analyses provided through Sparv.

## Installing Sparv
In order to install Sparv you will need a Unix-like environment (e.g. Linux, OS X) with
[Python 3.6.1](http://python.org/) or newer installed on it.

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

Sparv needs access to a directory on your system where it can store data, such as language models and configuration
files. This is called the **Sparv data directory**. By running `sparv setup` you can tell Sparv
where to set up its data directory.

If you like you can pre-build the model files. This step is optional and the only advantage is that annotating corpora
will be quicker once all the models are set up. If you skip this step, models will be downloaded and built automatically
on demand when annotating your first corpus. Pre-building models can be done by running `sparv build-models`. If you do
this in a directory where there is no [corpus config](user-manual/corpus-configuration.md) you
have to tell Sparv what language the models should be built for (otherwise the language of the corpus config is chosen
automatically). The language is provided as a three-letter code with the `--language` flag (check [this
table](#software-for-analysing-other-languages) for available languages and their codes). For example, if you would like
to build all the Swedish models you can run `sparv build-models --language swe`.

## Installing Additional Third-party Software
The Sparv Pipeline is typically used together with several plugins and third-party software. Which of these you will
need to install depends on what analyses you want to run with Sparv. Please note that different licenses may apply for
different software.

Unless stated otherwise in the instructions below, you won't have to download any additional language models or
parameter files. If the software is installed correctly, Sparv will download and install the necessary model files for
you prior to annotating data.

### Hunpos
|    |           |
|:---|:----------|
|**Purpose**                       |Swedish part-of-speech tagging (prerequisite for many other annotations, such as all of the SALDO annotations)
|**Download**                      |[Hunpos on Google Code](https://code.google.com/archive/p/hunpos/downloads)
|**License**                       |[BSD-3](https://opensource.org/licenses/BSD-3-Clause)
|**Version compatible with Sparv** |latest (1.0)

Installation is done by unpacking and then adding the executables to your path (you will need at least `hunpos-tag`).
Alternatively you can place the binaries inside your [Sparv data directory](#setting-up-sparv) under `bin`.

If you are running a 64-bit OS, you might also have to install 32-bit compatibility libraries if Hunpos won't run:
```bash
sudo apt install ia32-libs
```
On Arch Linux, activate the `multilib` repository and install `lib32-gcc-libs`. If that doesn't work, you might have to
compile Hunpos from source.

### MaltParser
|    |           |
|:---|:----------|
|**Purpose**                       |Swedish dependency parsing
|**Download**                      |[MaltParser webpage](http://www.maltparser.org/download.html)
|**License**                       |[MaltParser license](http://www.maltparser.org/license.html) (open source)
|**Version compatible with Sparv** |1.7.2
|**Dependencies**          		   |[Java](http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html)

Download and unpack the zip-file from the [MaltParser webpage](http://www.maltparser.org/download.html) and place the
`maltparser-1.7.2` folder inside the `bin` folder of the [Sparv data directory](#setting-up-sparv).

### Sparv wsd
|    |           |
|:---|:----------|
|**Purpose**                       |Swedish word-sense disambiguation
|**Download**                      |[Sparv wsd](https://github.com/spraakbanken/sparv-wsd/raw/master/bin/saldowsd.jar)
|**License**                       |[MIT](https://opensource.org/licenses/MIT)
|**Dependencies**          		   |[Java](http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html)

[Sparv wsd](https://github.com/spraakbanken/sparv-wsd) is developed at Språkbanken and runs under the same license as
the Sparv pipeline. In order to use it within the Sparv Pipeline it is enough to download the saldowsd.jar from GitHub
(see downloadlink above) and place it inside your [Sparv data directory](#setting-up-sparv) under `bin/wsd`.

### hfst-SweNER
|    |           |
|:---|:----------|
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
|    |           |
|:---|:----------|
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

The following is a list over the languages currently supported by the corpus pipeline, their language codes (ISO 639-3)
and which tools Sparv can use to analyze them:

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
|    |           |
|:---|:----------|
|**Purpose**                       |POS-tagging and lemmatisation for [some languages](#software-for-analysing-other-languages)
|**Download**                      |[TreeTagger webpage](http://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/)
|**License**                       |[TreeTagger license](https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/Tagger-Licence) (freely available for research, education and evaluation)
|**Version compatible with Sparv** |3.2.3 (may work with newer versions)

After downloading the software you need to have the `tree-tagger` binary in your path. Alternatively you can place the
`tree-tagger` binary file in the [Sparv data directory](#setting-up-sparv) under `bin`.

#### Stanford Parser
|    |           |
|:---|:----------|
|**Purpose**                       |Various analyses for English
|**Download**                      |[Stanford CoreNLP webpage](https://stanfordnlp.github.io/CoreNLP/history.html)
|**Version compatible with Sparv** |4.0.0 (may work with newer versions)
|**License**                       |[GPL-2.0](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
|**Dependencies**          		   |[Java](http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html)

Please download, unzip and place contents inside the [Sparv data directory](#setting-up-sparv) under `bin/stanford_parser`.

#### FreeLing
|    |           |
|:---|:----------|
|**Purpose**                       |Tokenisation, POS-tagging, lemmatisation and named entity recognition for [some languages](#software-for-analysing-other-languages)
|**Download**                      |[FreeLing on GitHub](https://github.com/TALP-UPC/FreeLing/releases/tag/4.2)
|**Version compatible with Sparv** |4.2
|**License**                       |[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.en.html)

Please install the software (including the additional language data) according to the instructions provided by FreeLing.
You will also need to install the [sparv-freeling plugin](https://github.com/spraakbanken/sparv-freeling). Please follow
the installation instructions for the sparv-freeling module on [GitHub](https://github.com/spraakbanken/sparv-freeling)
in order to set up the plugin correctly.

<!-- #### fast_align
|    |           |
|:---|:----------|
|**Purpose**                       |word-linking on parallel corpora
|**Download**                      |[fast_align on GitHub](https://github.com/clab/fast_align)
|**License**                       |[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)

Please follow the installation instructions given in the fast_align repository and make sure to have the binaries
`atools` and `fast_align` in your path. Alternatively you can place them in the [Sparv data directory](#setting-up-sparv) under
`bin/word_alignment`. -->


## Plugins
The only available plugin for Sparv available so far is [the sparv-freeling
plugin](https://github.com/spraakbanken/sparv-freeling). Please refer to its GitHub page for installation instructions.
