# Quick Start

This guide will help you get started with Sparv in just a few minutes, and walk you through the process of annotating
your first corpus. For a more detailed [installation guide](installation-and-setup.md) and
user manual, please refer to the other sections of this documentation.

> [!NOTE]
>
> Sparv is a command line application and all interaction in this quick start guide takes place in a
> [terminal](https://en.wikipedia.org/wiki/Terminal_emulator).
>
> This guide should work both in a Unix-like environment and the Windows command line.

## Installation

Sparv is best installed using [uv](https://docs.astral.sh/uv/), which creates an isolated environment for Sparv
and its dependencies. This keeps Sparv separate from your system Python, avoids version conflicts, and lets you run
Sparv from any location. As a bonus, uv will automatically install the correct Python version if you don't already have
it.

Begin by installing [uv](https://docs.astral.sh/uv/getting-started/installation/) if you don't have it already, by
running the following command:

=== "Linux or macOS"

    ```sh
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

=== "Windows"

    ```powershell
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ```

Once uv is installed, run the following command to install Sparv:

```sh
uv tool install sparv
```

Verify that the installation was successful by running `sparv`, which should display Sparv's command-line help:

```sh
sparv
```

Finally, complete the setup by running the [`sparv setup`](installation-and-setup.md#sparv-data-directory) command to
choose where Sparv will save its models and configuration:

```sh
sparv setup
```

## Creating a Corpus

With Sparv installed, let's try it out on a small corpus.

Each corpus needs its own directory, so start by creating one called `my_corpus`:

```sh
mkdir my_corpus
cd my_corpus
```

Inside this directory, create another directory called `source`, where we will put the corpus source files (the files
containing the text we want to annotate):

```sh
mkdir source
```

Using your favourite plain text editor (i.e. not Word), create a source file in XML format and place it in the `source`
directory. Make sure to save it with UTF-8 encoding.

`document.xml`

```xml
<text title="My first corpus document" author="me">
    Ord, ord, ord. Här kommer några fler ord.
</text>
```

> [!NOTE]
>
> The `source` directory may contain as many files as you want, but let's start with just this one.

## Creating the Config File

For Sparv to know what to do with your corpus, you need to create a [configuration file](corpus-configuration.md).
You can use the [corpus config wizard](corpus-configuration.md#corpus-config-wizard) or write it manually. For this
guide, we'll write it by hand.

Create a file called `config.yaml` directly in your corpus directory and save it with UTF-8 encoding. Your directory
structure should now look like this:

```text
my_corpus/
├── config.yaml
└── source/
    └── document.xml
```

Add the following content to the configuration file and save it:

```yaml
metadata:
    language: swe
import:
    importer: xml_import:parse
export:
    annotations:
        - <sentence>
        - <token>
```

The configuration file consists of several sections, each containing configuration variables and their values. First,
we specify the corpus language (Swedish). Second, in the `import` section, we specify which of
Sparv's importer modules to use (we want the one for XML). Finally, in the `export` section, we list what
automatic annotations we want Sparv to add. For this simple corpus we only ask for sentence segmentation and
tokenization.

## Running Sparv

If you have followed the steps above, everything should now be ready. Make sure that you are in the `my_corpus` folder,
and then run Sparv:

```sh
sparv run
```

After a short while, Sparv will tell you where the resulting files are saved. Let's have a look at one of them:

`export/xml_export.pretty/document_export.xml`

```xml
<?xml version='1.0' encoding='UTF-8'?>
<text author="me" title="My first corpus document">
  <sentence>
    <token>Ord</token>
    <token>,</token>
    <token>ord</token>
    <token>,</token>
    <token>ord</token>
    <token>.</token>
  </sentence>
  <sentence>
    <token>Här</token>
    <token>kommer</token>
    <token>några</token>
    <token>fler</token>
    <token>ord</token>
    <token>.</token>
  </sentence>
</text>
```

## What's Next?

Try adding some more annotations to your corpus by extending the annotations list in the corpus configuration file. To
explore available annotations, use the `sparv modules` command, or see the [Available Analyses](available-analyses.md)
section in the documentation. You can also try out the corpus configuration wizard by running `sparv wizard`.

It is also possible to annotate texts in other languages, such as English. Just change `language: swe` to
`language: eng` in the configuration file. Run `sparv languages` to see all supported languages.

> [!NOTE]
>
> Some annotations may require
> [additional software to be installed](installation-and-setup.md#installing-additional-third-party-software)
> before you can use them.
