# Installation and Setup
This section describes how to get the Sparv Pipeline up and running on your own machine. It also describes
additional software that you may need to install in order to run all the analyses provided through Sparv.

## Prerequisites
In order to install Sparv you will need a Unix-like environment (e.g. Linux, macOS or [Windows Subsystem for
Linux](https://docs.microsoft.com/en-us/windows/wsl/about)) with [Python 3.6.2](http://python.org/) or newer.

> [!NOTE]
> Most of Sparv's features should work in a Windows environment as well, but since we don't do any testing on Windows
> we cannot guarantee anything.

## Installing Sparv
Sparv is available on [PyPI](https://pypi.org/project/sparv-pipeline/) and can be installed using
[pip](https://pip.pypa.io/en/stable/installing) or [pipx](https://pipxproject.github.io/pipx/).
We recommend using pipx, which will install Sparv in an isolated environment while still making it available to be run
from anywhere.

Begin by [installing pipx](https://pipxproject.github.io/pipx/installation/) if you haven't already:
```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Once pipx is installed, run the following command to install the Sparv Pipeline:
```
pipx install sparv-pipeline
```

To verify that your installation of Sparv was successful, run the command `sparv`. The Sparv help should now be
displayed.

## Setting Up Sparv

### Sparv Data Directory
Sparv needs access to a directory on your system where it can store data, such as language models and configuration
files. This is called the **Sparv data directory**. By running `sparv setup` you can tell Sparv
where to set up its data directory. This will also populate the data directory with default configurations and presets.

> [!TIP]
> Instead of setting the data directory path using `sparv setup`, you may use the environment variable `SPARV_DATADIR`.
> This will ignore any path you have previously configured using the setup process. Note that you still have to run
> the setup command at least once to populate the directory, even when using the environment variable.

### Optional: Pre-build Models
If you like, you can pre-build the model files. This step is optional, and the only advantage is that annotating your
first corpus will be quicker since all the models are already set up. If you skip this step, models will be downloaded
and built automatically on demand when annotating your first corpus. Pre-building models can be done by using the
command `sparv build-models`. If you do this in a directory where there is no
[corpus config](user-manual/corpus-configuration.md) you
have to tell Sparv what language the models should be built for (otherwise the language of the corpus config is used).
The language is provided as a three-letter code with the `--language` flag (use the `sparv languages` command for
a list of available languages and their codes). For example, if you would like to build all the Swedish models you
can run `sparv build-models --language swe`.

## Installing Additional Third-party Software
The Sparv Pipeline can be used together with several plugins and third-party software. Installation of the software
listed below is optional. Which of these you will need to install depends on what analyses you want to run with Sparv.
Please note that different licenses may apply for different software.

Unless stated otherwise in the instructions below, you won't have to download any additional language models or
parameter files. If the software is installed correctly, Sparv will download and install the necessary model files for
you prior to annotating data.

### Sparv wsd
|    |           |
|:---|:----------|
|**Purpose**                       |Swedish word-sense disambiguation. Recommended for standard Swedish annotations.
|**Download**                      |[Sparv wsd](https://github.com/spraakbanken/sparv-wsd/raw/master/bin/saldowsd.jar)
|**License**                       |[MIT](https://opensource.org/licenses/MIT)
|**Dependencies**          		   |[Java](http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html)

[Sparv wsd](https://github.com/spraakbanken/sparv-wsd) is developed at Språkbanken and runs under the same license as
the Sparv Pipeline. In order to use it within the Sparv Pipeline it is enough to download the saldowsd.jar from GitHub
(see download link above) and place it inside your [Sparv data directory](#setting-up-sparv) under `bin/wsd`.

### hfst-SweNER
|    |           |
|:---|:----------|
|**Purpose**                       |Swedish named-entity recognition. Recommended for standard Swedish annotations.
|**Download**                      |[hfst-SweNER](http://urn.fi/urn%3Anbn%3Afi%3Alb-2021101202)
|**Version compatible with Sparv** |0.9.3

> [!NOTE]
> hfst-SweNER requires a Unix-like environment.

The current version of hfst-SweNER is written for Python 2 while Sparv uses Python 3, so before installing it needs to
be patched. After extracting the archive, go to the `hfst-swener-0.9.3/scripts` directory and create the file
`swener.patch` with the following contents:

```
--- convert-namex-tags.py
+++ convert-namex-tags.py
@@ -1 +1 @@
-#! /usr/bin/env python
+#! /usr/bin/env python3
@@ -34 +34 @@
-        elif isinstance(files, basestring):
+        elif isinstance(files, str):
@@ -73 +73 @@
-        return [s[start:start+partlen] for start in xrange(0, len(s), partlen)]
+        return [s[start:start+partlen] for start in range(0, len(s), partlen)]
@@ -132,3 +131,0 @@
-    sys.stdin = codecs.getreader('utf-8')(sys.stdin)
-    sys.stdout = codecs.getwriter('utf-8')(sys.stdout)
-    sys.stderr = codecs.getwriter('utf-8')(sys.stderr)
```

Then simply run the command `patch < swener.patch`, which will make the necessary changes.

After applying the patch, please follow the installation instructions provided by hfst-SweNER.

### Hunpos
|    |           |
|:---|:----------|
|**Purpose**                       |Alternative Swedish part-of-speech tagger (if you don't want to use Stanza)
|**Download**                      |[Hunpos on Google Code](https://code.google.com/archive/p/hunpos/downloads)
|**License**                       |[BSD-3](https://opensource.org/licenses/BSD-3-Clause)
|**Version compatible with Sparv** |latest (1.0)

Installation is done by unpacking and then adding the executables to your path (you will need at least `hunpos-tag`).
Alternatively you can place the binaries inside your [Sparv data directory](#setting-up-sparv) under `bin`.

If you are running a 64-bit OS, you might also have to install 32-bit compatibility libraries if Hunpos won't run:
```
sudo apt install lib32z1
```

On newer macOS you probably have to compile Hunpos from source. [This GitHub repo](https://github.com/mivoq/hunpos) has
instructions that should work.

When using Sparv with Hunpos on Windows you will have to set the config variable `hunpos.binary: hunpos-tag.exe` in your
[corpus configuration](user-manual/corpus-configuration.md). You will also have to add the `cygwin1.dll` file that comes
with Hunpos to your path or copy it into your [Sparv data directory](#setting-up-sparv) along with the Hunpos binaries.

### MaltParser
|    |           |
|:---|:----------|
|**Purpose**                       |Alternative Swedish dependency parser (if you don't want to use Stanza)
|**Download**                      |[MaltParser webpage](http://www.maltparser.org/download.html)
|**License**                       |[MaltParser license](http://www.maltparser.org/license.html) (open source)
|**Version compatible with Sparv** |1.7.2
|**Dependencies**          		   |[Java](http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html)

Download and unpack the zip-file from the [MaltParser webpage](http://www.maltparser.org/download.html) and place the
`maltparser-1.7.2` directory inside the `bin` directory of the [Sparv data directory](#setting-up-sparv).

### Corpus Workbench
|    |           |
|:---|:----------|
|**Purpose**                       |Creating Corpus Workbench binary files. Only needed if you want to be able to search corpora with this tool.
|**Download**                      |[Corpus Workbench on SourceForge](https://cwb.sourceforge.io/download.php)
|**License**                       |[GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html)
|**Version compatible with Sparv** |beta 3.4.21 (most likely works with newer versions)

Refer to the INSTALL text file for instructions on how to build and install on your system.

### Software for Analysing Other Languages than Swedish
Sparv can use different third-party tools for analyzing corpora in other languages than Swedish.

The following is a list of the languages currently supported by Sparv, their language codes (ISO 639-3)
and which tools Sparv can use to analyse them:

Language       |ISO 639-3 Code |Analysis Tool
:--------------|:--------------|:-------------
Asturian       |ast            |FreeLing
Bulgarian      |bul            |TreeTagger
Catalan        |cat            |FreeLing
Dutch          |nld            |TreeTagger
Estonian       |est            |TreeTagger
English        |eng            |FreeLing, Stanford Parser, TreeTagger
French         |fra            |FreeLing, TreeTagger
Finnish        |fin            |TreeTagger
Galician       |glg            |FreeLing
German         |deu            |FreeLing, TreeTagger
Italian        |ita            |FreeLing, TreeTagger
Latin          |lat            |TreeTagger
Norwegian      |nob            |FreeLing
Polish         |pol            |TreeTagger
Portuguese     |por            |FreeLing
Romanian       |ron            |TreeTagger
Russian        |rus            |FreeLing, TreeTagger
Slovak         |slk            |TreeTagger
Slovenian      |slv            |FreeLing
Spanish        |spa            |FreeLing, TreeTagger
Swedish        |swe            |Sparv

<!-- Swedish 1800's |sv-1800       |Sparv) -->
<!-- Swedish development mode |sv-dev        |Sparv) -->

#### TreeTagger
|    |           |
|:---|:----------|
|**Purpose**                       |POS-tagging and lemmatisation for [some languages](#software-for-analysing-other-languages-than-swedish)
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
|**License**                       |[GPL-2.0](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)
|**Version compatible with Sparv** |4.0.0 (may work with newer versions)
|**Dependencies**          		  |[Java](http://www.oracle.com/technetwork/java/javase/downloads/jdk8-downloads-2133151.html)

Please download, unzip and place contents inside the [Sparv data directory](#setting-up-sparv) under `bin/stanford_parser`.

#### FreeLing
|    |           |
|:---|:----------|
|**Purpose**                       |Tokenisation, POS-tagging, lemmatisation and named entity recognition for [some languages](#software-for-analysing-other-languages-than-swedish)
|**Download**                      |[FreeLing on GitHub](https://github.com/TALP-UPC/FreeLing/releases/tag/4.2)
|**License**                       |[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.en.html)
|**Version compatible with Sparv** |4.2

Please install the software (including the additional language data) according to the instructions provided by FreeLing.
Note that you will need to uncompress the source and language files in the same folder before compiling.
You will also need to install the [sparv-sbx-freeling plugin](https://github.com/spraakbanken/sparv-sbx-freeling). Please follow
the installation instructions for the sparv-sbx-freeling module on [GitHub](https://github.com/spraakbanken/sparv-sbx-freeling)
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

If you have the Sparv Pipeline installed on your machine, you can install plugins by injecting them into the Sparv
Pipeline code using pipx:
```
pipx inject sparv-pipeline [pointer-to-sparv-plugin]
```

The `pointer-to-sparv-plugin` can be a package available on the [Python Package Index (PyPI)](https://pypi.org/), a
remote public repository, or a local directory on your machine.

For now there are two plugins available for Sparv:
[sparv-sbx-freeling](https://github.com/spraakbanken/sparv-sbx-freeling) and
[sparv-sbx-metadata](https://github.com/spraakbanken/sparv-sbx-metadata). Please refer to their GitHub page for more
information.

Plugins can be uninstalled by running:
```
pipx runpip sparv-pipeline uninstall [name-of-sparv-plugin]
```

## Uninstalling Sparv

To uninstall Sparv completely, follow these steps:

1. Run `sparv setup --reset` to unset [Sparv's data directory](#setting-up-sparv). The directory itself will not be
   removed, but its location (if available) will be printed.
2. Manually delete the data directory.
3. Run one of the following commands, depending on whether you installed Sparv using pipx or pip:

    ```
    pipx uninstall sparv-pipeline
    ```

    ```
    pip uninstall sparv-pipeline
    ```
