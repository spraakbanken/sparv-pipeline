# Corpus Configuration

To process a corpus with Sparv, you need to create a *corpus configuration file*. This file, written in
[YAML](https://docs.ansible.com/ansible/latest/reference_appendices/YAMLSyntax.html), provides essential information
about your corpus and instructs Sparv on how to process it. The [corpus config wizard](#corpus-config-wizard) can assist
you in generating this file. Alternatively, you can refer to the [example
corpora](https://github.com/spraakbanken/sparv/releases/latest/download/example_corpora.zip) for inspiration.

A minimal config file contains a list of automatic annotations you want to be included in the output.
Below is an example of a small config file:

```yaml
metadata:
    # Language of the source files
    language: swe
export:
    # Automatic annotations to include in the export
    annotations:
        - <sentence>:misc.id
        - <token>:saldo.baseform
        - <token>:hunpos.pos
        - <token>:sensaldo.sentiment_label
```

> [!NOTE]
>
> In Sparv and throughout this documentation, configuration keys are often written in dot notation (e.g.,
> `export.annotations`). This notation indicates that `annotations` is a key nested within the `export` section, as
> seen in the example above.

> [!NOTE]
>
> Most processors (like annotators or importers) in Sparv have adjustable options that can be fine-tuned within
> the configuration file. Each module has its own dedicated section, like `metadata` and `export` in the example above.
> To view all available configuration keys and their descriptions, use the `sparv modules` command.

## Config Schema

Running `sparv schema` will generate a JSON schema that in many text editors can be used to validate your config file as
you are creating it. In some editors, this schema also enables autocompletion for configuration options.

The schema is printed to the console, but you can save it to a file by running `sparv schema > schema.json`.

## Corpus Config Wizard

The corpus config wizard is a tool that helps you create a config file by guiding you through questions about your
corpus and desired annotations. Run `sparv wizard` to start the tool. If a config file already exists in the directory,
the wizard will read it and set default values based on the current configuration.

The wizard is a helpful starting point for creating a config file but does not cover all of Sparv's advanced features.
However, you can of course manually edit a wizard-generated config file to add advanced configurations, such as
[custom annotations](#custom-annotations) or [headers](#headers).

## Default Values

Some configuration variables, like `metadata`, `classes`, `import`, `export`, and `custom_annotations`, are general and
used across multiple Sparv modules. Others are specific to individual annotation modules (e.g., `hunpos.binary`
specifies the binary used by the Hunpos module to perform part-of-speech tagging). These module-specific options
typically have default values defined within each module.

When you run Sparv, it reads your corpus configuration file and combines it with both Sparv's default configuration
file (`config/config_default.yaml` in the [Sparv data directory](installation-and-setup.md#setting-up-sparv)) and the
module-specific default values. To view the final, combined configuration, you can use the command `sparv config`. This
command also allows you to check individual config variables or sections, such as `sparv config metadata.language` or
`sparv config metadata`. All default values can be overridden in your corpus configuration file.

Certain configuration options must be defined, either by Sparv's default config file or your corpus config:

- `metadata.language` (default: `swe`)
- `import.importer` (default: `xml_import:parse`)
- `export.annotations`
- `classes.token` (default: `segment.token`)
- `classes.sentence` (default: `segment.sentence`)

## Metadata Options

The `metadata` section in your corpus configuration file provides metadata about your corpus, which may be utilized by
various Sparv modules.

- `metadata.id`: Specifies a machine-readable name for the corpus, required by some export modules. This string may
  contain ASCII letters, digits, and dashes.

- `metadata.name`: An optional human-readable name for the corpus. This field is divided into one or more subsections
  to specify the name in different languages. Use ISO 639-3 language codes to indicate the language, e.g.,
  `metadata.name.eng` for the English name of the corpus.

- `metadata.language`: Indicates the language of the source files in the corpus, using an ISO 639-3 code. If omitted,
  it defaults to `swe`. Run `sparv languages` to see a list of supported languages and their corresponding codes.

- `metadata.variety`: An optional field to specify the language variety of the source files, if applicable.
  Run `sparv languages` to view supported language varieties.

- `metadata.description`: An optional description of the corpus, which may span multiple lines. Like `metadata.name`,
  this field is divided into language-specific subsections using ISO 639-3 language codes.

- `metadata.short_description`: An optional short description of the corpus, spanning one line. Like `metadata.name`,
  this field is divided into language-specific subsections using ISO 639-3 language codes.

## Import Options

The `import` section of your corpus config provides Sparv with details about your source files (i.e., your corpus).

- `import.source_dir`: Specifies the location of your source files and defaults to `source`. Sparv will search this
  directory recursively for valid files to process.

- `import.importer`: Defines which importer Sparv should use when processing your files. Which importer you should use
  depends on the format of your source files. For XML files, use `xml_import:parse` (the default setting), and for
  plain text files, use `text_import:parse`. Run `sparv modules` to see what other importers are available.

- `import.text_annotation`: Identifies the existing annotation representing *one text*. Any automatic text-level
  annotations will be attached to this annotation. For XML files, this corresponds to an XML element in your source
  files; for unstructured import formats, like plain text and PDF, a default `text` root annotation is created
  automatically, so no further configuration is needed.

    !!! note

        This setting automatically sets the `text` [class](#annotation-classes). If you want to use an automatic
        annotation as the text annotation, you should not use this setting, and instead set the `text` class directly.

- `import.encoding`: Specifies the source file encoding, with a default of UTF-8.

- `import.normalize`: Normalizes Unicode symbols in the input, using any of the following forms: `NFC`, `NFKC`, `NFD`,
  or `NFKD`. Defaults to `NFC`.

- `import.keep_control_chars`: Set to `true` to retain control characters in the text. Generally, this should remain
  disabled (the default setting) to avoid potential issues.

Each importer may have additional options. Use `sparv modules --importers` to view these. For instance, the XML importer
offers options to skip the content of specific elements and provides fine-grained control over XML header imports. For
more details about XML-specific options, run `sparv modules xml_import`. See also the section on [headers](#headers)
and [XML namespaces](#xml-namespaces) further down.

## Export Options

The `export` section of your corpus config specifies how the output data should be structured and what it should
contain.

### Annotations from the Source Data

The `export.source_annotations` option allows you to select which existing annotations in your source files should be
included in the output (only applicable if your input is in a format that supports structured data, such as XML). By
default, all existing annotations, such as XML elements and attributes, are included in the output.

- When specifying elements using this option, ensure the root element (i.e., the element that encompasses all other
  elements and text content) is included. Omitting the root element will result in invalid XML output, preventing Sparv
  from generating XML files.

- To exclude all source annotations, set this option to `[]`. Note that this may cause XML export errors, as a root
  element is required.

You can rename elements and attributes present in your input data. For example, if your files contain elements like
`<article name="Scandinavian Furniture" date="2020-09-28">` and you want them to appear as `<text title="Scandinavian
Furniture" date="2020-09-28">` in the output, you can use the following syntax:

```yaml
export:
    source_annotations:
        - article as text
        - article:name as title
        - ...
```

The ellipsis (`...`) in the example above represents all other elements and attributes in your input data that are not
explicitly listed. Omitting the ellipsis would result in the "date" attribute being excluded from the output.

If you want to keep most of the markup of your input data but exclude some elements or attributes, you can use the `not`
keyword:

```yaml
export:
    source_annotations:
        - not date
```

In the example above, this configuration would produce the following output: `<article name="Scandinavian Furniture">`.
If `source_annotations` contains *only* annotations prefixed with `not`, all other annotations are automatically
included by default, without needing to use the ellipsis described above.

### Automatic Annotations Generated by Sparv

The `export.annotations` option specifies the list of automatic annotations that Sparv should generate and include in
the output. To see which annotations are available, run `sparv modules --annotators`. Some annotations use curly
brackets, such as `{annotation}:misc.id`, indicating a wildcard that must be replaced with a specific value in the
`export.annotations` list (e.g., `<sentence>:misc.id`). You may also use [annotation presets](#annotation-presets).

If you need to produce multiple output formats with different annotations, you can override the
`export.source_annotations` and `export.annotations` options for specific exporter modules. For instance, use
`xml_export.source_annotations` and `xml_export.annotations` for XML export, and `csv_export.source_annotations` and
`csv_export.annotations` for CSV export. Generally, the values from the `export` section are used by default unless
overridden at the exporter module level.

> [!TIP]
>
> If two or more sections of your configuration are identical, such as the list of annotations to include in
> different export formats, instead of copying and pasting, you can use [YAML
> anchors](https://docs.ansible.com/ansible/latest/user_guide/playbooks_advanced_syntax.html#yaml-anchors-and-aliases-sharing-variable-values).

> [!TIP]
>
> You can convert a structural attribute to a token attribute, which is useful for representing structural
> information (like named entities or phrase structures) in non-structured formats (e.g., CSV export). Use the
> annotation `<token>:misc.from_struct_{struct}_{attr}`, replacing `{struct}` and `{attr}` with the structural
> annotation and attribute names respectively (e.g., `<token>:misc.from_struct_swener.ne_swener.type`).

### Default Export Formats

The `export.default` option specifies the list of export formats produced when running `sparv run` without format
arguments. By default, this list includes only `xml_export:pretty`, which is the formatted XML export with one token per
line. Use `sparv run --list` to see all available export formats.

### Naming Options

Several export options relate to the naming of annotations and attributes. You can prefix all annotations produced by
Sparv with a custom prefix using the `export.sparv_namespace` option. Similarly, you can add a prefix to all annotations
and attributes from your source files using the `export.source_namespace` option.

> [!NOTE]
>
> Despite the name of the options, these are not real XML namespaces but merely prefixes added to annotation names.

The `export.remove_module_namespaces` option is `true` by default, meaning module name prefixes are removed during
export. Turning this option off will result in output like:

```xml
<segment.token stanza.pos="IN" saldo.baseform="|hej|">Hej</segment.token>
```

instead of the more compact:

```xml
<token pos="IN" baseform="|hej|">Hej</token>
```

### Scrambling and Anonymisation

The `export.scramble_on` setting is used by all export formats that support scrambling. It controls which annotation
your corpus will be scrambled on (by default, no scrambling is performed). Typical settings are `export.scramble_on:
<sentence>` or `export.scramble_on: <paragraph>`. For example, setting this to `<paragraph>` would lead to all
paragraphs being randomly shuffled in the export, while the sentences and tokens within the paragraphs keep their
original order.

The `export.word` option defines the strings to be output as tokens in the export. By default, this is set to
`<token:word>`. A useful application for this setting is anonymisation of texts. If you want to produce XML containing
only annotations but not the actual text, you could set `export.word: <token>:anonymized` to get output like this:

```xml
<sentence id="b1ac">
    <token pos="IN">***</token>
    <token pos="MAD">*</token>
</sentence>
```

> [!NOTE]
>
> For technical reasons, the `xml_export:preserved_format` export does not respect this setting. The preserved
> format XML will always contain the original corpus text.

Each exporter may have additional options which can be listed with `sparv modules --exporters`.

## Headers

In some cases, corpus metadata in XML is stored within header elements rather than as attributes of text-enclosing
elements. Sparv can extract this information from headers and store it as annotations, which can then be used as input
for various analyses. Additionally, header information can be exported as attributes if desired.

Consider the following example of a corpus file:

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

In this example, we want to retain the data within the `<header>` element but exclude its contents from being analyzed
as corpus text. Instead, we want to attach this metadata to the `<text>` element. Additionally, we want to completely
remove the `<another-header>` element and its contents.

The following configuration achieves this:

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
xml_export:
    header_annotations:
        - not header
        - not another-header
```

With this configuration, the output will look like this:

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

If you want to keep the headers in the output without analyzing them as corpus text, simply list them without the `not`
prefix in `xml_export.header_annotations`. If you don't specify anything in `xml_export.header_annotations`, all headers
will be retained by default.

## XML Namespaces

When working with XML source data that includes namespaces, Sparv attempts to preserve these namespaces in the XML
output. However, there are two key limitations to be aware of:

1. Namespace declarations are always placed in the root element of the output, regardless of their location in the
   source data.
2. URIs and prefixes are assumed to be unique. A URI will be associated with the first prefix declared for that URI in
   the source file.

To refer to elements or attributes with namespaces in the corpus configuration file, use a special syntax. This syntax
consists of the namespace prefix followed by a `+`, and then the tag or attribute name. For example, the reference for
the element `<sparv:myelement xmlns:sparv="https://spraakbanken.gu.se/verktyg/sparv">` would be `sparv+myelement`.

If you prefer to remove namespaces during import, set `xml_import.remove_namespaces` to `true` in the corpus
configuration. Be cautious, as this may lead to collisions between attributes with the same name but different
namespaces.

## Annotation Classes

Annotation classes allow you to refer to annotations without specifying the module that produces them. For example,
`<token>` and `<sentence>` are annotation classes that by default refer to `segment.token` and `segment.sentence`,
respectively.

These classes simplify dependency management between modules and enhance the pipeline's flexibility. For instance, a
part-of-speech tagger that requires tokenized text as input probably doesn't care which tokenizer produced the tokens,
so it can simply request `<token>` as input.

As a user, you can also benefit from annotation classes. In most parts of the config file where annotations are
referenced, you can use classes instead. To see the available classes, run the command `sparv classes`. Classes are
denoted by enclosing the class name in angle brackets, like `<token>`.

If multiple modules can produce annotations of the same class, you can specify which one to use in the `classes` section
of your config file. Sparv provides default class settings, but you can override them as needed.

To illustrate how you can use classes in your configuration file, consider the following example:

If you want to include part-of-speech tags from Stanza, you could add `segment.token:stanza.pos` to the export
annotations list. This indicates that you want part-of-speech tags from Stanza as attributes for the tokens produced by
the `segment` module.

```yaml
export:
    annotations:
        - segment.token:stanza.pos
        - segment.token:malt.deprel
        - segment.token:malt.dephead_ref
```

The drawback of this notation is that if you decide to switch your tokenizer to a different one called
`my_new_segmenter`, you would need to update all instances of `segment.token` in your configuration to
`my_new_segmenter.token`. Instead of doing this, you can redefine your token class by setting `classes.token` to
`my_new_segmenter.token` and use the `<token>` class in your annotations list:

```yaml
classes:
    token: my_new_segmenter.token

export:
    annotations:
        - <token>:stanza.pos
        - <token>:malt.deprel
        - <token>:malt.dephead_ref
```

Another instance where you might need to explicitly redefine classes is when your source files include annotations (such
as sentences or tokens) that should be used as input for annotators. For instance, if you have manually segmented
sentences and enclosed each sentence in an `<s>` element, you can bypass Sparv's automatic sentence segmentation by
setting the sentence class to this element:

```yaml
classes:
    sentence: s

xml_import:
    elements:
        - s
```

This works because annotators requiring sentence annotations as input rely on the `<sentence>` class, rather than being
tied to a specific module's sentence annotation.

> [!NOTE]
>
> To be able to use annotations from your source data as input for annotators, Sparv first needs to be informed about
> their existence. For XML data, this is achieved by listing the relevant elements in the `xml_import.elements` section
> of your configuration file, as shown in the example above.
>
> Note that only annotations intended as input for annotators need to be listed in `xml_import.elements`, not when
> merely passing them through to the output.

## Annotation Presets

Annotation presets are predefined collections of annotations that can simplify your configuration. Instead of listing
each annotation individually, you can use a preset to include all related annotations at once. For example, instead of
specifying each SALDO annotation separately like this:

```yaml
export:
    annotations:
        - <token>:saldo.baseform2 as baseform
        - <token>:saldo.lemgram
        - <token>:wsd.sense
        - <token>:saldo.compwf
        - <token>:saldo.complemgram
```

You can use the `SWE_DEFAULT.saldo` preset to include all SALDO annotations with a single line:

```yaml
export:
    annotations:
        - SWE_DEFAULT.saldo
```

Here, `SWE_DEFAULT.saldo` will expand to include all the SALDO annotations. You can mix presets with individual
annotations and combine different presets as needed.

Sparv comes with a set of default presets. To see which presets are available for your corpus and the annotations they
include, run the `sparv presets` command. Presets are defined in YAML files located in the [Sparv data
directory](installation-and-setup.md#setting-up-sparv) under `config/presets`. You can add your own presets by
adding YAML files to this directory.

It is possible to exclude specific annotations from a preset using the `not` keyword. In the following example, all
SALDO annotations are included except for the compound analysis attributes:

```yaml
export:
    annotations:
        - SWE_DEFAULT.saldo
        - not <token>:saldo.compwf
        - not <token>:saldo.complemgram
```

> [!NOTE]
>
> Preset files may define their own default `class` values. These will be set automatically when using a preset. You can
> override these in your config files if necessary.

## Parent Configuration

When managing multiple corpora with similar configurations, you can streamline the process by using a parent
configuration file. This is particularly useful when only a few variables, such as the corpus ID, differ between
corpora. To do this, specify the path to the parent configuration file in the `parent` variable of your individual
corpus config files. Your corpus configuration will then inherit all parameters from the parent file, except those
explicitly defined in the individual config file.

```yaml
parent: ../parent-config.yaml
metadata:
    id: animals-foxes
    name:
        swe: 'Djurkorpus: Rävar'
```

In this example, the configuration will include everything from `../parent-config.yaml`, but the values for
`metadata.id` and `metadata.name.swe` will be overridden with `animals-foxes` and `Djurkorpus: Rävar`, respectively.

You can also specify multiple parent files in a list, with each subsequent parent overriding any conflicting values from
the previous ones:

```yaml
parent:
    - ../parent-config.yaml
    - ../another-parent-config.yaml
```

Nested parents, where a parent references another parent, are also supported.

## Custom Annotations

The `custom_annotations` section of the configuration file serves three distinct purposes, each detailed below.

### Built-in Utility Annotations

Sparv includes a special type of annotator called "utility annotators". Unlike regular annotators which usually have
default settings but can be customized with configuration variables, utility annotators have no or few default settings,
and need to be configured using the `custom_annotations` section. They can be used multiple times, and their purpose is
often to create new annotations by modifying the output of other annotators. Examples of utility annotators include
`misc:affix` which adds a prefix and/or suffix to another annotation, and `misc:find_replace_regex` which replaces text
in an annotation using a regular expression.

To use a utility annotator in your corpus, you need to configure it in the `custom_annotations` section of your config
file. Utility annotators have no configuration variables, and instead use parameters. Here is an example configuration
for the `misc:affix` annotator:

```yaml
custom_annotations:
    - annotator: misc:affix
      params:
          out: <token>:misc.word.affixed
          chunk: <token:word>
          prefix: "|"
          suffix: "|"
```

In this example, the word annotation is used as input, and the string "|" is added as both a prefix and suffix. The
configuration specifies the annotator (`annotator`) and sets the values for its parameters in the `params` section. The
`sparv modules` command lists the parameters for each utility annotator, helping you identify them.

For the `misc:affix` annotator, the parameters are:

1. `out`: The name of the output annotation, which must include the module name as a prefix (e.g., `misc`).
2. `chunk`: The input annotation to be modified.
3. `prefix` and `suffix`: The strings to be added as a prefix and/or suffix.

To include this annotation in your corpus, add `<token>:misc.word.affixed` to an annotations list in your corpus config
(e.g., `export.annotations`). This example is applied in the standard-swe [example
corpus](https://github.com/spraakbanken/sparv/releases/latest/download/example_corpora.zip).

You can use the same annotator multiple times with different output names:

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

> [!NOTE]
>
> Custom annotations always create new annotations; they do not modify existing ones.

> [!NOTE]
>
> When a parameter for a custom annotator requires a regular expression (e.g., in `misc:find_replace_regex`),
> the expression must be enclosed in single quotation marks. Regular expressions inside double quotation marks in YAML
> are not parsed correctly.

### Reusing Regular Annotations

You can also use the `custom_annotations` section to reuse a regular (non-utility) annotation multiple times within your
corpus. For instance, if you want to apply the same part-of-speech tagger with different models, you can achieve this by
configuring the annotator in the `custom_annotations` section.

To do this, specify the annotator and add a `config` section with the necessary configuration, just as you would in the
root of the configuration file. Additionally, you must provide a `suffix` to give the new annotation a unique name.

In the example below, we reuse the `hunpos:msdtag` annotator with a custom model:

```yaml
custom_annotations:
    - annotator: hunpos:msdtag
      suffix: -mymodel
      config:
          hunpos:
              model: path/to/my_hunpos_model
```

The original Hunpos annotation is named `<token>:hunpos.msd`. With the specified suffix, the new annotation will be
named `<token>:hunpos.msd-mymodel`, which can then be included in the list of annotations:

```yaml
export:
    annotations:
        - <token>:hunpos.msd
        - <token>:hunpos.msd-mymodel
```

### User-defined Custom Annotators

Typically, you extend Sparv with new annotators by creating a plugin, which makes the annotator available to all your
corpora. However, in special cases, you might want to create a user-defined custom annotator, which is available only to
the corpus in the same directory. Code-wise, plugins and custom annotators are essentially the same. The main difference
lies in their packaging and usage.

For detailed instructions on writing a Sparv annotator, refer to the [developer's
guide](../developers-guide/writing-sparv-plugins.md#module-code). Below is a quick example.

> [!TIP]
>
> The example uses the `@annotator` decorator to create an annotator. You can also create your own importer,
> exporter, installer, or model builder using the appropriate Sparv decorator. More information on decorators can be
> found in the [developer's guide](../developers-guide/sparv-decorators.md).

Creating a user-defined custom annotator involves three steps:

1. Create a Python script with an annotator and place it in your corpus directory.
2. Register the annotator in your corpus config.
3. Use your custom annotation by referring to it in an annotations list.

**Step 1**: Create a Python script in your corpus directory, for example, `convert.py`:

```text
my_corpus/
├── config.yaml
├── convert.py
└── source
    ├── document1.xml
    └── document2.xml
```

Sparv will automatically detect scripts placed here, provided that your functions are registered in your
configuration file (see Step 2). Your annotator function must use one of the Sparv decorators (typically `@annotator`).
Below is an example of a simple annotator that converts all tokens to uppercase:

```python
from sparv.api import Annotation, Output, annotator

@annotator("Convert every word to uppercase.")
def uppercase(word: Annotation = Annotation("<token:word>"),
              out: Output = Output("<token>:custom.convert.upper")):
    """Convert to uppercase."""
    out.write([val.upper() for val in word.read()])
```

**Step 2**: Register your custom annotator in your corpus configuration file under the `custom_annotations` section.
This allows Sparv to locate and use it. The name of your annotator is constructed by concatenating the following four
parts:

- the prefix `custom.`
- the filename of the Python file without extension (`convert` in our example)
- a colon
- the annotator name (`uppercase`)

```yaml
custom_annotations:
    - annotator: custom.convert:uppercase
```

**Step 3**: Use the annotation created by your custom annotator by adding the output annotation name (in this example
specified by the `out` parameter value) to an annotations list in your corpus config:

```yaml
export:
    annotations:
        - <token>:custom.convert.upper
```

In this example, all parameters in the annotator function have default values, so you do not need to supply any
parameter values in your config. However, you can override the default values if needed:

```yaml
custom_annotations:
    - annotator: custom.convert:uppercase
      params:
          out: <token>:custom.convert.myUppercaseAnnotation
```

> [!NOTE]
>
> When using custom annotations from your own code, all output annotations must be prefixed with `custom`.

An example of a user-defined custom annotator can be found in the standard-swe [example
corpus](https://github.com/spraakbanken/sparv/releases/latest/download/example_corpora.zip).

For more information on writing an annotator function, refer to the [developer's
guide](../developers-guide/writing-sparv-plugins.md#module-code). If you have written a general annotator module,
consider making it into a Sparv plugin so others can use it. Read more about writing plugins in the [developer's
guide](../developers-guide/writing-sparv-plugins.md).
