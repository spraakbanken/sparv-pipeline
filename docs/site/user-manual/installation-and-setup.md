# Installation and Setup

This section walks you through setting up Sparv on your computer, including any additional software you may
need to fully utilize all of Sparv's analysis features.

## Prerequisites

To install Sparv, you'll need a Unix-like environment (e.g. Linux, macOS or [Windows Subsystem for
Linux](https://docs.microsoft.com/en-us/windows/wsl/about)) with [Python 3.11](https://python.org/) or later.

> [!NOTE]
>
> While most Sparv features may work in a Windows environment, Sparv is not regularly tested on Windows, so
> compatibility is not guaranteed. Feel free to [report any issues](https://github.com/spraakbanken/sparv/issues) you
> encounter.

## Installing Sparv

Sparv is available on [PyPI](https://pypi.org/project/sparv/) and can be installed via
[pip](https://pip.pypa.io/en/stable/installation/), [uv](https://docs.astral.sh/uv/), or
[pipx](https://pipx.pypa.io/stable/). We recommend using uv or pipx, as both install Sparv in an isolated environment
while allowing it to be run from any location.

=== "uv"

    Begin by [installing uv](https://docs.astral.sh/uv/getting-started/installation/):

    === "Linux or macOS"

        ```sh
        curl -LsSf https://astral.sh/uv/install.sh | sh
        ```

    === "Windows"

        ```powershell
        powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
        ```

    Refer to the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) for more details and
    alternative installation methods.

    Then, install Sparv:

    ```sh
    uv tool install sparv
    ```

    To verify that Sparv was installed successfully, run the command `sparv`. You should see the Sparv help information
    displayed.

=== "pipx"

    Begin by [installing pipx](https://pipx.pypa.io/stable/installation/):

    ```sh
    python3 -m pip install --user pipx
    python3 -m pipx ensurepath
    ```

    Then, install Sparv:

    ```sh
    pipx install sparv
    ```

    To verify that Sparv was installed successfully, run the command `sparv`. You should see the Sparv help information
    displayed.

    !!! note
    
        If pipx stops working after a Python upgrade, try running `pipx reinstall-all`. If that fails, you may need to
        manually delete pipx's local environment directory (usually `~/.local/pipx`) and reinstall Sparv.

## Setting Up Sparv

### Sparv Data Directory

Sparv requires a dedicated directory to store language models and configuration files. This is called the
**Sparv data directory**. Run `sparv setup` to choose this directory, which will also populate it with default
configurations and presets.

> [!TIP]
>
> For a non-interactive setup (e.g. in a Docker container), you can use the `--dir` flag to specify the data directory
> path and perform the setup in one command:
>
> ```sh
> sparv setup --dir /path/to/sparv-data
> ```

> [!TIP]
>
> Instead of (or in addition to) setting the data directory path using `sparv setup`, you can use the environment
> variable `SPARV_DATADIR`. This overrides any path you may have previously configured using the setup process. This is
> useful if you want to have multiple Sparv installations with different data directories on the same machine. Note that
> you still have to run the `setup` command at least once to populate the selected directory, even when using the
> environment variable.

### Optional: Pre-build Models

Sparv will automatically download and build the models needed for the analyses you want to perform. Optionally, you can
also pre-build the models to speed up the annotation of your first corpus. This step is not required, and unless you
have a specific reason to do so, we recommend skipping it, as it may download models that you won't use.

To pre-build the models, use the following command:

```sh
sparv build-models --all
```

If you run this command in a directory without a [corpus config](corpus-configuration.md), you need to specify the
language for which the models should be built. Use the `--language` flag followed by the three-letter language code (you
can use the `sparv languages` command to see a list of available languages and their codes). For example, to build all
Swedish models, run:

```sh
sparv build-models --all --language swe
```

## Installing Additional Third-party Software

Sparv can be used together with several plugins and third-party software. The installation of the software
listed below is optional and depends on the analyses you wish to perform with Sparv. Please note that different licenses
may apply to different software.

Unless otherwise specified in the instructions, you won’t need to download any additional language models. If the
software is installed correctly, Sparv will automatically download and install the necessary model files for you.

### Sparv wsd

|    |           |
|:---|:----------|
|**Purpose**                       |Swedish word-sense disambiguation. Recommended for standard Swedish annotations.|
|**Download**                      |[Sparv wsd](https://github.com/spraakbanken/sparv-wsd/raw/master/bin/saldowsd.jar)|
|**License**                       |[MIT](https://opensource.org/licenses/MIT)|
|**Dependencies**                  |[Java](https://www.java.com/en/download/)|

[Sparv wsd](https://github.com/spraakbanken/sparv-wsd) is developed by Språkbanken Text and is licensed under the same
terms as Sparv. To use it within Sparv, simply download the `saldowsd.jar` file from the provided GitHub link and place
it in the `bin/wsd` directory inside your [Sparv data directory](#setting-up-sparv).

### hfst-SweNER

|    |           |
|:---|:----------|
|**Purpose**                       |Swedish named-entity recognition. Recommended for standard Swedish annotations.|
|**Download**                      |[hfst-SweNER](https://urn.fi/urn%3Anbn%3Afi%3Alb-2021101202)|
|**Version compatible with Sparv** |0.9.3|

> [!NOTE]
>
> hfst-SweNER requires a Unix-like environment.

The current version of hfst-SweNER is written for Python 2, while Sparv uses Python 3. Therefore, it needs to be patched before installation. After extracting the archive, navigate to the `hfst-swener-0.9.3/scripts` directory and create a file named `swener.patch` with the following contents:

```diff
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

Run the following command to apply the patch:

```sh
patch < swener.patch
```

After applying the patch, follow the installation instructions provided by hfst-SweNER.

### Hunpos

|    |           |
|:---|:----------|
|**Purpose**                       |Alternative Swedish part-of-speech tagger (if you prefer not to use Stanza)|
|**Download**                      |[Hunpos on Google Code](https://code.google.com/archive/p/hunpos/downloads)|
|**License**                       |[BSD-3-Clause](https://opensource.org/licenses/BSD-3-Clause)|
|**Version compatible with Sparv** |latest (1.0)|

To install Hunpos, unpack the downloaded files and add the executables to your system path (you will need at least `hunpos-tag`). Alternatively, you can place the binaries inside the `bin` directory of your [Sparv data directory](#setting-up-sparv).

If you are using a 64-bit operating system, you might need to install 32-bit compatibility libraries if Hunpos does not run:

```sh
sudo apt install lib32z1
```

For newer macOS versions, you may need to compile Hunpos from source. Instructions can be found in [this GitHub repository](https://github.com/mivoq/hunpos).

When using Sparv with Hunpos on Windows, set the configuration variable `hunpos.binary: hunpos-tag.exe` in your [corpus configuration](corpus-configuration.md). Additionally, ensure the `cygwin1.dll` file that comes with Hunpos is in your system path or copied into your `bin` directory within the Sparv data directory along with the Hunpos binaries.

### MaltParser

|    |           |
|:---|:----------|
|**Purpose**                       |Alternative Swedish dependency parser (if you prefer not to use Stanza)|
|**Download**                      |[MaltParser webpage](https://www.maltparser.org/download.html)|
|**License**                       |[MaltParser license](https://www.maltparser.org/license.html) (open source)|
|**Version compatible with Sparv** |1.7.2|
|**Dependencies**                  |[Java](https://www.java.com/en/download/)|

Download and unpack the zip file from the [MaltParser webpage](https://www.maltparser.org/download.html) and place the
`maltparser-1.7.2` directory inside the `bin` directory of your [Sparv data directory](#setting-up-sparv).

### Corpus Workbench

|    |           |
|:---|:----------|
|**Purpose**                       |Creating Corpus Workbench binary files. Required if you want to search corpora using this tool.|
|**Download**                      |[Corpus Workbench on SourceForge](https://cwb.sourceforge.io/install.php)|
|**License**                       |[GPL-3.0](https://www.gnu.org/licenses/gpl-3.0.html)|
|**Version compatible with Sparv** |beta 3.4.21 (likely compatible with newer versions)|

Refer to the INSTALL text file for detailed instructions on how to build and install Corpus Workbench on your system.

### Analyzing Languages Other Than Swedish

Sparv supports the analysis of corpora in multiple languages using various third-party tools. Below is a list of
supported languages, their ISO 639-3 codes, and the tools Sparv can use for their analysis:

|Language         |ISO 639-3 Code |Analysis Tool|
|:----------------|:--------------|:-------------|
|Asturian         |ast            |FreeLing|
|Bulgarian        |bul            |TreeTagger|
|Catalan          |cat            |FreeLing|
|Dutch            |nld            |TreeTagger|
|Estonian         |est            |TreeTagger|
|English          |eng            |FreeLing, Stanford Parser, TreeTagger|
|French           |fra            |FreeLing, TreeTagger|
|Finnish          |fin            |TreeTagger|
|Galician         |glg            |FreeLing|
|German           |deu            |FreeLing, TreeTagger|
|Italian          |ita            |FreeLing, TreeTagger|
|Latin            |lat            |TreeTagger|
|Norwegian Bokmål |nob            |FreeLing|
|Polish           |pol            |TreeTagger|
|Portuguese       |por            |FreeLing|
|Romanian         |ron            |TreeTagger|
|Russian          |rus            |FreeLing, TreeTagger|
|Slovak           |slk            |TreeTagger|
|Slovenian        |slv            |FreeLing|
|Spanish          |spa            |FreeLing, TreeTagger|
|Swedish          |swe            |Sparv|

<!-- Swedish 1800's |sv-1800       |Sparv) -->
<!-- Swedish development mode |sv-dev        |Sparv) -->

#### TreeTagger

|    |           |
|:---|:----------|
|**Purpose**                       |POS-tagging and lemmatization for [various languages](#analyzing-languages-other-than-swedish)|
|**Download**                      |[TreeTagger webpage](https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/)|
|**License**                       |[TreeTagger license](https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/Tagger-Licence) (freely available for research, education, and evaluation)|
|**Version compatible with Sparv** |3.2.3 (may work with newer versions)|

After downloading TreeTagger, ensure the `tree-tagger` binary is in your system path. Alternatively, you can place the
`tree-tagger` binary in the `bin` directory within your [Sparv data directory](#setting-up-sparv).

#### Stanford Parser

|    |           |
|:---|:----------|
|**Purpose**                       |Various analyses for English|
|**Download**                      |[Stanford CoreNLP webpage](https://stanfordnlp.github.io/CoreNLP/history.html)|
|**License**                       |[GPL-2.0](https://www.gnu.org/licenses/old-licenses/gpl-2.0.html)|
|**Version compatible with Sparv** |4.0.0 (may work with newer versions)|
|**Dependencies**                  |[Java](https://www.java.com/en/download/)|

To use the Stanford Parser with Sparv, download and unzip the package from the Stanford CoreNLP webpage. Place the
contents in the `bin/stanford_parser` directory within your [Sparv data directory](#setting-up-sparv).

#### FreeLing

|    |           |
|:---|:----------|
|**Purpose**                       |Tokenization, POS-tagging, lemmatization and named entity recognition for [various languages](#analyzing-languages-other-than-swedish)|
|**Download**                      |[FreeLing on GitHub](https://github.com/TALP-UPC/FreeLing/releases/tag/4.2)|
|**License**                       |[AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.en.html)|
|**Version compatible with Sparv** |4.2|

To install FreeLing, follow the instructions provided on their website. Ensure you download both the source and
language data files and uncompress them in the same directory before compiling. Additionally, you will need to install
the [sparv-sbx-freeling plugin](https://github.com/spraakbanken/sparv-sbx-freeling). Follow the setup instructions on
the plugin's GitHub page to correctly configure it for use with Sparv.

<!-- #### fast_align
|    |           |
|:---|:----------|
|**Purpose**                       |word-linking on parallel corpora
|**Download**                      |[fast_align on GitHub](https://github.com/clab/fast_align)
|**License**                       |[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)

Please follow the installation instructions given in the fast_align repository and make sure to have the binaries
`atools` and `fast_align` in your path. Alternatively you can place them in the [Sparv data directory](#setting-up-sparv) under
`bin/word_alignment`. -->

## Installing and Uninstalling Plugins

Sparv plugins are managed using the `sparv plugins` command. This command allows you to **install**, **uninstall**, and
**list** plugins. Under the hood, plugins are standard Python packages, so Sparv relies on `pip` to handle
installations. This means you can install plugins from any source supported by `pip`, such as PyPI, remote repositories,
or local directories.

### Installing Plugins

To install a plugin, use the following command:

```sh
sparv plugins install [plugin-source]
```

The `[plugin-source]` can refer to different locations:

#### Install from PyPI

To install a plugin published on the [Python Package Index (PyPI)](https://pypi.org/), use its name, e.g.:

```sh
sparv plugins install sparv-sbx-uppercase
```

#### Install from a Remote Repository

To install a plugin from a remote repository (e.g., GitHub), provide the repository URL or archive link:

```sh
sparv plugins install https://github.com/spraakbanken/sparv-plugin-template/archive/main.zip
```

#### Install from a Local Directory

To install a plugin from a local directory, use the path to the directory:

```sh
sparv plugins install ./sparv-sbx-uppercase
```

Using the `-e` flag when installing from a local directory will install the plugin in **editable mode**, meaning that
changes to the plugin code will immediately be available to Sparv without having to reinstall the plugin:

```sh
sparv plugins install -e ./sparv-sbx-uppercase
```

### Listing Installed Plugins

To view all installed plugins, run:

```sh
sparv plugins list
```

### Uninstalling Plugins

To uninstall a plugin, use the following command:

```sh
sparv plugins uninstall [plugin-name]
```

The `[plugin-name]` can be either the distribution name (e.g. `sparv-sbx-uppercase`), or the plugin name used within
Sparv (e.g. `sbx_uppercase`).

For example:

```sh
sparv plugins uninstall sbx_uppercase
```

## Uninstalling Sparv

To uninstall Sparv completely, follow these steps:

1. Run `sparv setup --reset` to unset [Sparv's data directory](#setting-up-sparv). The directory itself will not be
   removed, but its location (if available) will be printed.
2. Manually delete the data directory.
3. Run one of the following commands, depending on whether you installed Sparv using uv, pipx, or pip:

    === "uv"

        ```sh
        uv tool uninstall sparv
        ```

    === "pipx"

        ```sh
        pipx uninstall sparv
        ```

    === "pip"

        ```sh
        pip uninstall sparv
        ```
