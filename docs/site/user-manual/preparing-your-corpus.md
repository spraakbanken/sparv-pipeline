# Preparing Your Corpus

This section provides guidelines for preparing your corpus for processing by Sparv. It covers the structure
of the source directory, requirements for source files, and guidelines for XML files.

## The Corpus Directory

Each corpus that you want to process with Sparv should be stored in a separate directory. This directory is referred to
as the *corpus directory*. The corpus directory should contain a corpus configuration file, named `config.yaml`, and a
directory with source files. The source files are the documents to be annotated, in a format that Sparv can process,
such as XML or plain text.

The source directory may contain one or more files, and they may be organized in any level of subdirectories. Exporters
that generate one file per source file will mirror the directory structure of the source files.

A typical corpus directory structure might look like this:

```text
my_corpus/
├── config.yaml
└── source
   ├── document1.xml
   ├── document2.xml
   └── document3.xml
```

If you're trying Sparv for the first time, we recommend downloading and test-running some of the [example
corpora](https://github.com/spraakbanken/sparv/releases/latest/download/example_corpora.zip). These corpora
come with pre-configured `config.yaml` files and source files.

> [!NOTE]
>
> The default name for the source directory is `source`. If you use a different name, you have to specify the name of
> the source directory in your corpus configuration file, using the `import.source_dir` setting.

## Requirements for Source Files

Before you can run Sparv on your corpus, you need to ensure that your source files meet the requirements for processing
by Sparv. The exact requirements depend on the file format, but there are some general guidelines that
apply to all source files:

- All source files must use the same file format, file extension, and (if applicable) the same markup.

- The optimal size per file depends on various factors. Sparv can process multiple files in parallel, so having several
  files is generally better than having one or two large files. Additionally, very large files can cause memory issues,
  especially when processing multiple files simultaneously. On the other hand, having too many small files can slow down
  processing due to the overhead required for each file, such as loading models. While it is difficult to
  specify an exact optimal file size, as it depends on your hardware, we recommend keeping files between 1-10 MB.

- If your corpus is in XML format, ensure your **XML is valid**. Further guidelines for XML files are provided in the
  next section.

> [!NOTE]
>
> The directories `sparv-workdir` and `export` within your corpus directory are reserved for Sparv. Do not
> manually create directories with these names, as their contents may be overwritten or deleted.

## XML Guidelines

The recommended source format for Sparv is XML. While Sparv supports other formats, XML is the most versatile and
enables the most advanced processing. Sparv can handle XML files with almost any structure, but there are some general
guidelines to follow, as outlined below.

### Valid XML

The most important requirement is that your XML must be valid. This means that it must adhere to the [rules of the XML
specification](https://www.w3schools.com/xml/xml_syntax.asp). You can check the validity of your XML using an XML
validator, such as the command-line tool `xmllint`, or an online validator.

### Element Names

Sparv does not care about the names of your XML elements, and doesn't automatically handle any specific element
in a special way. Any special handling of elements is done through the corpus configuration file, for example by
specifying that a certain element should be treated as a sentence, if your corpus is already sentence-segmented.

### Text Content

The *text content* of your XML files needs to be stored in elements, not attributes, as only text stored in elements
will be annotated by Sparv. For example, the following XML would *not* be possible to analyze with Sparv, as all text is
stored in attributes:

```xml
<text>
  <word text="Hello" />
  <word text="world" />
</text>
```

### Multiple Documents in One File

You can store multiple documents in one XML file. Each document should be enclosed in a separate element, such as
`<document>`. You then need to specify the document element in the corpus configuration file using the
`import.text_annotation` setting. This affects any automatic document-level annotations. Make sure that all documents
are enclosed within a single root element, for the XML to be valid. This root element can be named anything.

Example:

```xml
<corpus>
  <document>
    This is the first document.
  </document>
  <document>
     This is the second document.
  </document>
</corpus>
```

### Metadata

Your XML files may contain metadata, such as author, title, or publication date. Metadata can be stored as attributes on
any element. Sparv will not by default process this metadata, but it will be preserved in the output files.

Including metadata in your XML files can be useful, especially if you plan to use your finished corpus in a corpus
search tool like Korp. Metadata such as author, title, and publication date can help filter search results and provide
additional context about the documents in your corpus.

Example:

```xml
<document author="August Mustermann" title="My Document">
  <chapter name="Introduction">
    This is the text of the document.
  </chapter>
</document>
```

Metadata may also be stored in header elements, where both attributes and elements with text can be used. This is
described in more detail in the [Corpus Configuration](corpus-configuration.md#headers) section.

### Existing Annotations

All existing annotations in your XML files will by default be preserved in the output files. If you have existing
annotations that you would like to use *instead* of Sparv's annotations, such as pre-existing tokenization, you have to
specify this in the corpus configuration file. Since Sparv does not automatically handle any specific element in a
special way, you need to specify which elements should be treated as tokens, sentences, etc. This is described in more
detail in the [Corpus Configuration](corpus-configuration.md#annotation-classes) section.

### Example XML

Here are some examples of valid XML files that can be processed by Sparv:

```xml
<text>
  <sentence>
    <token pos="PS">Min</token>
    <token pos="NN">katt</token>
    <token pos="VB">sprang</token>
    <token pos="PL">bort</token>
    <token pos="MAD">.</token>
  </sentence>
</text>
```

```xml
<document>
  <header>
    <title>My Document</title>
    <author>August Mustermann</author>
  </header>
  <chapter name="Introduction">
    <sentence>
      My day is going well.
    </sentence>
  </chapter>
</document>
```

```xml
<text>
  A very simple &amp; short text.
</text>
```
