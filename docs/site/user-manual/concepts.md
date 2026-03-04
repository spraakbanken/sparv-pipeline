# Sparv Concepts

This section provides an overview of the key concepts and components of Sparv, including the corpus directory structure,
configuration files, annotations, annotators, modules, and plugins. Some of these concepts are explained in more detail
in other sections of the user manual.

## Corpus Directory

Each corpus that you want to process with Sparv needs to be stored in a separate directory. This directory is referred
to as a *corpus directory*. A corpus directory contains a corpus configuration file (`config.yaml`) and a directory with
source files. The source files are the documents to be annotated, in a format that Sparv can process, such as XML or
plain text.

The corpus directory structure and source file requirements are described in more detail in the [Preparing Your
Corpus](preparing-your-corpus.md) section.

## Configuration File

The configuration file (`config.yaml`) specifies the desired annotations, export formats, and other processing
instructions for Sparv. The existence of a configuration file is what makes a directory a corpus directory, and most
Sparv commands won't work without it.

The configuration file is written in YAML format. For a detailed guide on creating corpus configuration files, refer to
the [Corpus Configuration](corpus-configuration.md) section.

## Modules and Plugins

Modules are the building blocks of Sparv, each responsible for a specific part of the annotation process. Modules
contain one or more *processors*, of which there are several types: *importers* for reading source files, *annotators*
for analyzing the text and adding annotations, *exporters* for saving the results, and more.

Sparv comes with a set of built-in modules that cover the entire workflow from importing text data, annotating it with
linguistic features, exporting the results in different formats, to deploying the annotated corpus.

Plugins are external modules that extend Sparv's functionality. They can be used to add support for additional
third-party tools, custom annotations, or other features that are not part of the Sparv core. Writing plugins
is covered in the [Developer's Guide](../developers-guide/writing-sparv-plugins.md).

## Annotations and Annotators

*Annotations* are the linguistic features that Sparv adds to the text. *Annotators* are a type of processor that adds
annotations to the text. Examples of annotations include part-of-speech tags, lemmas, named entities, and syntactic
structures.

How to specify which annotations to add to your corpus is described in the [Corpus
Configuration](corpus-configuration.md) section. For a list of available annotations and annotators, run the `sparv
modules` command, as described in the [Running Sparv](running-sparv.md) section. You can also find a list of available
annotations in the [Available Analyses](available-analyses.md) section in the documentation.
