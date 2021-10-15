# Quick Start

This quick start guide will get you started with Sparv in just a few minutes, and will guide you through
annotating your first corpus. For a more comprehensive [installation](user-manual/installation-and-setup.md) and
user guide, please refer to the full documentation.

> [!INFO]
> Sparv is a command line application, and just like the
> [2004 Steven Spielberg movie](https://www.imdb.com/title/tt0362227/), this quick start guide takes place in a
> [terminal](https://en.wikipedia.org/wiki/Terminal_emulator).
>
> This guide should work both in a Unix-like environment and the Windows command line.

## Installation

Begin by making sure that you have [Python 3.6.2](http://python.org/) or newer installed by running the following
in your terminal:
```
python3 --version
```

> [!NOTE]
> On some systems, the command may be called `python` instead of `python3`.

Continue by [installing pipx](https://pipxproject.github.io/pipx/installation/) if you haven't already:
```
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

Once pipx is installed, run the following command to install the Sparv Pipeline:
```
pipx install sparv-pipeline
```

To verify that the installation was successful, try running Sparv which should print Sparv's command line help:
```
sparv
```

Finish the installation by running the [Sparv setup](user-manual/installation-and-setup.md#sparv-data-directory)
command, to select a location for Sparv to save its models and configuration:
```
sparv setup
```

## Creating a Corpus

Now that Sparv is installed and working, let's try it out on a small corpus.

Each corpus needs its own directory, so begin by creating one called `mycorpus`:
```
mkdir mycorpus
cd mycorpus
```

In this directory, create another directory called `source`, where we will put the corpus source files (the files
containing the text we want to annotate):
```
mkdir source
```

Next, use your favourite plain text editor (i.e. not Word) to create a source file in XML format, and put it in the
`source` directory. Make sure to save it in UTF-8 encoding.

`document.xml`
```xml
<text title="My first corpus document" author="me">
    Ord, ord, ord. Här kommer några fler ord.
</text>
```

> [!NOTE]
> The `source` directory may contain as many files as you want, but let's start with just this one.

## Creating the Config File

For Sparv to know what to do with your corpus, you first need to create a
[configuration file](user-manual/corpus-configuration.md). This can be accomplished
either by running the [corpus config wizard](corpus-configuration.md#corpus-config-wizard), or by writing it by hand.
Using the wizard is usually easier, but for now, let's get our hands dirty and write it by hand!

Use your text editor to create a file called `config.yaml` directly under your corpus directory. Remember to save it
in UTF-8 encoding.
The directory structure should now look like this:

```
mycorpus/
├── config.yaml
└── source/
    └── document.xml
```

Add the following to the configuration file and save it:

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

The configuration file consists of different sections, each containing configuration variables and their values. First,
we have told Sparv the language of our corpus (Swedish). Second, in the `import` section, we have specified which of
Sparv's importer modules to use (we want the one for XML). Finally, in the `export` section, we have listed what
automatic annotations we want Sparv to add. For this simple corpus we only ask for sentence segmentation and
tokenisation.

## Running Sparv

If you have followed the above steps, everything should now be ready. Make sure that you are in the `mycorpus` folder,
and then run Sparv by typing:
```
sparv run
```

After a short while, Sparv will tell you where the resulting files are saved. Let's have a look at one of them:

`export/xml_pretty/document_export.xml`
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

Try adding some more annotations to your corpus by extending the annotations list in the corpus configuration. To find
out what annotations are available, use the `sparv modules` command. You can also try out the corpus configuration
wizard by running `sparv wizard`.

It is also possible to annotate texts in other languages, e.g., English. Just change the line `language: swe` to
`language: eng` in the file `config.yaml`. Run `sparv languages` to see what languages are available in Sparv.

> [!NOTE]
> Some annotations may require
> [additional software to be installed](user-manual/installation-and-setup.md#installing-additional-third-party-software)
> before you can use them.
