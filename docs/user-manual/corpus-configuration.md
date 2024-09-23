# Corpus Configuration
To be able to annotate a corpus with Sparv you will need to create a corpus config file. A corpus config file is written
in [YAML](https://docs.ansible.com/ansible/latest/reference_appendices/YAMLSyntax.html), a fairly human-readable format
for creating structured data. This file contains information about your corpus (metadata) and instructions for Sparv on
how to process it. The [corpus config wizard](#corpus-config-wizard) can help you create one. If you want to see some
examples of config files you can download the [example
corpora](https://github.com/spraakbanken/sparv-pipeline/releases/latest/download/example_corpora.zip).

A minimal config file contains a list of (automatic) annotations you want to be included in the output.
Here is an example of a small config file:
```yaml
metadata:
    # Language of the source files
    language: swe
export:
    # Automatic annotations to be included in the export
    annotations:
        - <sentence>:misc.id
        - <token>:saldo.baseform
        - <token>:hunpos.pos
        - <token>:sensaldo.sentiment_label
```

> [!NOTE]
> In Sparv and this documentation, configuration keys are often referred to using dot notation, like this:
> `export.annotations`.
> This should be interpreted as the configuration key `annotations` nested under the section `export`, as shown in the
> example above.

> [!NOTE]
> Most annotators in Sparv have one or more options that can be fine-tuned using the configuration file. Each module
> has its own section in the file, like the `metadata` and `export` sections in the example above.
> By using the `sparv modules` command you can get a list of the available configuration keys and their descriptions.

## Config Schema
Running `sparv schema` will output a JSON schema which can be used in many text editors to validate your config file as
you are creating it, and in some editors can be used to provide autocompletion.

## Corpus Config Wizard
The corpus config wizard is a tool designed to help you create a corpus config file by asking questions about your
corpus and the annotations you would like Sparv to add to it. Run `sparv wizard` in order to start the tool. When
running this command in a directory where a corpus config file exists already, Sparv will read the config file and set
the wizard default values according to the existing configuration.

The wizard is an auxiliary tool to get you started with your corpus config file, and it does not cover all of Sparv's
advanced functionality. However, a config file that was created with the wizard can of course be edited manually
afterwards, e.g. for adding more advanced configuration details such as [custom annotations](#custom-annotations) or
[headers](#headers).


## Default Values
Some config variables such as `metadata`, `classes`, `import`, `export` and `custom_annotations` are general and are
used by multiple Sparv modules, while others are specific to one particular annotation module (e.g. `hunpos.binary`
defines the name of the binary the hunpos module uses to run part-of-speech tagging). These module specific config
options usually have default values which are defined by the module itself.

When running Sparv your corpus config will be read and combined with Sparv's default config file
(`config/config_default.yaml` in the [Sparv data directory](installation-and-setup.md#setting-up-sparv)) and
the default values defined by different Sparv modules. You can view the resulting configuration by running `sparv
config`. Using the `config` command you can also inspect specific config variables, e.g. `sparv config metadata` or
`sparv config metadata.language`. All default values can be overridden in your own corpus config.

There are a few config options that must be set (either through the default config or the corpus config):
  - `metadata.language` (default: `swe`)
  - `import.importer` (default: `xml_import:parse`)
  - `export.annotations`
  - `classes.token` (default: `segment.token`)
  - `classes.sentence` (default: `segment.sentence`)


## Metadata Options
The `metadata` section of your corpus config contains metadata about your corpus that may be used by any Sparv module.

- `metadata.id` defines the machine name of the corpus. It is required by some exporter modules. This string may contain
  ascii letters, digits and dashes.

- `metadata.name` is an optional human-readable name of the corpus. This option is split into two fields, `eng` and
  `swe` for defining a name in English and in Swedish.

- `metadata.language` defines the language of the source files in the corpus. This should be an ISO 639-3 code. If not
  specified it defaults to `swe`. Run `sparv languages` to list the supported languages along with their language codes.

- `metadata.variety` is an optional field containing the language variety of the source files (if applicable). Run
  `sparv languages` to list the supported varieties for each language.

- `metadata.description` is an optional description for the corpus. It may consist of multiple lines. This option is
  split into two fields, `eng` and `swe` for defining a name in English and in Swedish.


## Import Options
The `import` section of your corpus config is used to give Sparv some information about your input files (i.e. your
corpus).

- `import.source_dir` defines the location of your input files, and it defaults to `source`. Sparv will check the
  source directory recursively for valid input files to process.

- `import.importer` is used to tell Sparv which importer to use when processing your source files. The setting you
  want to choose depends on the format of your input files. If your corpus is in XML you should choose
  `xml_import:parse` (this is the default setting). If your corpus files are in plain text, you should choose
  `text_import:parse` instead.

- `import.text_annotation` specifies the annotation representing _one text_, and any automatic text-level
  annotations will be attached to this annotation. For XML source files this refers to one of the XML
  elements. For plain text source files a default `text` root annotation will be created automatically, and you won't
  have to change this setting.

    > [!NOTE]
    > This setting automatically sets the `text` [class](#annotation-classes). If you want to use an automatic
    > annotation as the text annotation, you should not use this setting, and instead set the `text` class directly.

- `import.encoding` specifies the encoding of the source files. It defaults to UTF-8.

- `import.normalize` lets you normalize unicode symbols in the input using any of the following forms: 'NFC', 'NFKC',
  'NFD', and 'NFKD'. It defaults to `NFC`.

- `import.keep_control_chars` may be set to `True` if control characters should not be removed from the text. You
  normally don't want to enable this, since it most likely will lead to problems.

Each importer may have additional options which can be listed with `sparv modules --importers`. The XML importer for
example has options that allow you to skip importing the contents of certain elements and options that give you
fine-grained control over importing XML headers. Run `sparv modules --importers xml_import` for more details.


## Export Options
The `export` section of your corpus config defines what the output data (or export) should look like. With the config
option `export.source_annotations` you can tell Sparv what elements and attributes present in your source files you
would like to keep in your output data (this only applies if your input data is XML). If you don't specify anything,
everything will be kept in the output. If you do not want any source annotations to be included in your output you
can set this option to `[]`. This will cause errors in the XML exports though because the root element must be
listed as a source annotation. If you do list anything here, make sure that you include the root element (i.e. the
element that encloses all other included elements and text content) for each of your input files. If you don't,
the resulting output XML will be invalid and Sparv won't be able to produce XML files. If you only want to produce
other output formats than XML, you don't need to worry about this.

It is possible to rename elements and attributes present in your input data. Let's say your files contain elements
 like this `<article name="Scandinavian Furniture" date="2020-09-28">` and you would like them to look like this in the
 output `<text title="Scandinavian Furniture" date="2020-09-28">` (so you want to rename the element "article" and the
 attribute "name" to "text" and "title" respectively). For this you can use the following syntax:
```yaml
export:
    source_annotations:
        - article as text
        - article:name as title
        - ...
```
Please note that the dots (`...`) in the above example also carry meaning. They are used to refer to all the
remaining elements and attributes in your input data. Without using the dots the "date" attribute in the example would
be lost.

If you want to keep most of the markup of your input data but you want to exclude some elements or attributes
you can do this by using the `not` keyword:
```yaml
export:
    source_annotations:
        - not date
```
In the example above this would result in the following output: `<article name="Scandinavian Furniture">`.

The option `export.annotations` contains a list of automatic annotations you want Sparv to produce and include in the
output. You can run `sparv modules --annotators` to see what annotations are available. Some annotations listed here
contain curly brackets, e.g. `{annotation}:misc.id`. This means that the annotation contains a wildcard (or in some
cases multiple wildcards) that must be replaced with a value when using the annotation in the `export.annotations` list
(e.g. `<sentence>:misc.id`). You can also read the section about [annotation presets](#annotation-presets) for more info
about automatic annotations.

If you want to produce multiple output formats containing different annotations you can override the
`export.source_annotations` and `export.annotations` options for specific exporter modules. The annotations for the XML
export for example are set with `xml_export.source_annotations` and `xml_export.annotations`, the annotations for the
CSV export are set with `csv_export.source_annotations` and `csv_export.annotations` and so on. Many of the `export`
options work this way, where the values from `export` will be used by default unless overridden on exporter module
level.

> [!TIP]
> If two or more sections of your config are identical, for example the list of annotations to include in
> different export formats, instead of copying and pasting you can use
> [YAML anchors](https://docs.ansible.com/ansible/latest/user_guide/playbooks_advanced_syntax.html#yaml-anchors-and-aliases-sharing-variable-values).

> [!TIP]
> It is possible to convert a structural attribute to a token attribute, which can be convenient for representing
> structural information (such as named entities or phrase structures) in non-structured formats (e.g. the CSV export).
> Use the annotation `<token>:misc.from_struct_{struct}_{attr}` where you replace `{struct}` and `{attr}` with the
> name of the structural annotation and the attribute name respectively (e.g.
> `<token>:misc.from_struct_swener.ne_swener.type`).

The option `export.default` defines a list of export formats that will be produced when running `sparv run`
without format arguments. By default, this list only contains `xml_export:pretty`, the formatted XML export with
one token per line. Use the command `sparv run --list` to see a list of available export formats.

There are a couple of export options concerning the naming of annotations and attributes. You can choose to prefix all
annotations produced by Sparv with a custom prefix with the `export.sparv_namespace` option. Likewise, you can add a
prefix to all annotations and attributes originating from your source files with the `export.source_namespace` option.

The option `export.remove_module_namespaces` is `true` by default, meaning that module name prefixes are removed
during export. Turning the option off will result in output like:
```xml
<segment.token stanza.pos="IN" saldo.baseform="|hej|">Hej</segment.token>
```
instead of the more compact:
```xml
<token pos="IN" baseform="|hej|">Hej</token>
```

`export.scramble_on` is a setting used by all the export formats that support scrambling. It controls which annotation
your corpus will be scrambled on. Typical settings are `export.scramble_on: <sentence>` or `export.scramble_on:
<paragraph>`. For example, setting this to `<paragraph>` would lead to all paragraphs being randomly shuffled in the
export, while the sentences and tokens within the paragraphs keep their original order.

The option `export.word` is used to define the strings to be output as tokens in the export. By default, this is set to
`<token:word>`. A useful application for this setting is anonymisation of texts. If you want to produce XML containing
only annotations but not the actual text, you could set `export.word: <token>:anonymised` to get output like this:
```xml
    <sentence id="b1ac">
      <token pos="IN">***</token>
      <token pos="MAD">*</token>
    </sentence>
```
> [!NOTE]
> For technical reasons the export `xml_export:preserved_format` does not respect this setting. The
> preserved format XML will always contain the original corpus text.

Each exporter may have additional options which can be listed with `sparv modules --exporters`.


## Headers
Sometimes corpus metadata in XML is stored in headers rather than in attributes belonging to text-enclosing elements.
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
We want to keep the data in `<header>` but we don't want the contents to be analysed as corpus text. Instead, we want
its metadata to be attached to the `<text>` element. We also want to get rid of `<another-header>` and its contents
entirely.
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
xml_export:
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
If you do want to keep the headers in the output (without them being analysed as corpus text), just list them without
the `not` prefix in `xml_export.header_annotations`. If you don't specify anything at all in
`xml_export.header_annotations` all your headers will be kept.


## XML Namespaces
If the source data is in XML and contains namespaces Sparv will try to keep these intact in the XML output.
There are, however, two limitations:
1. Namespace declarations are always placed in the root element in the output, regardless of where they are in the
   source data.
2. URIs and prefixes are assumed to be unique. A URI will automatically be associated with the first prefix that is
   declared for that URI in the source file.

When referring to elements or attributes containing namespaces in the corpus config file a special syntax is used. A
reference consists of the namespace prefix followed by `+`, followed by the tag or attribute name. E.g. the reference
for this element `<sparv:myelement xmlns:sparv="https://spraakbanken.gu.se/verktyg/sparv">` would be `sparv+myelement`.

Namespaces may be removed upon import by setting `xml_import.remove_namespaces` to `true` in the corpus config. This may
however result in collisions in attributes containing namespaces in the source data.


## Annotation Classes
Annotation classes are used to refer to annotations without having to explicitly point out which
module produces that annotation. Two examples we have already shown in examples above are `<token>` and `<sentence>`,
which by default refer to the annotations `segment.token` and `segment.sentence` respectively.

Annotation classes are used internally to simplify dependence relations between modules, and to
increase the flexibility of the pipeline. For example, a part-of-speech tagger that requires tokenised text as input
probably doesn't care about which tokeniser is used, so it simply asks for `<token>`.

Annotation classes are also useful for you as a user. In most places in the config file where you refer to
annotations, you can also use classes. To see what classes are available, use the command `sparv classes`.
Classes are referred to by enclosing the class name with angle brackets: `<token>`.

If a class can be produced by more than one module, you can use the `classes` section in your config file to select
which one to use. Sparv already comes with a few default class settings.

One example of a config section where you can use classes is the export annotations list. If you want to include
part-of-speech tags from Stanza you could include `segment.token:stanza.pos` in the annotations list, meaning that you
want to have POS tags from Stanza as attributes to the tokens produced by the segment module.
```yaml
export:
    annotations:
        - segment.token:stanza.pos
        - segment.token:malt.deprel
        - segment.token:malt.dephead_ref
```
The disadvantage of this notation is that if you decide to exchange your tokeniser for a different one called
`my_new_segmenter` you would have to change all occurrences of `segment.token` in your config to
`my_new_segmenter.token`. Instead of doing that you can just re-define your token class by setting `classes.token` to
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

Re-defining annotation classes may also be necessary when your corpus data contains annotations (such as sentences or
tokens) that should be used as input to annotators. For example, if you have done manual sentence segmentation and
enclosed each sentence in an `<s>` element, you can skip Sparv's automatic sentence segmentation by setting the sentence
class to this element:
```yaml
classes:
    sentence: s

xml_import:
    elements:
        - s
```
> [!ATTENTION]
> Please note that you need to tell Sparv that `s` is an annotation imported from your corpus data. This is
> done by listing `s` under `xml_import.elements` as is done in the above example.


## Annotation Presets
Annotation presets are collections of annotations which can be used instead of listing the contained annotations. For
example, instead of listing all the SALDO annotations in your list of automatic annotations like this:
```yaml
export:
    annotations:
        - <token>:saldo.baseform2 as baseform
        - <token>:saldo.lemgram
        - <token>:wsd.sense
        - <token>:saldo.compwf
        - <token>:saldo.complemgram
```
... you can use the `SWE_DEFAULT.saldo` preset:
```yaml
export:
    annotations:
        - SWE_DEFAULT.saldo
```

Here `SWE_DEFAULT.saldo` will expand to all the SALDO annotations. You can mix presets with annotations, and you can
combine different presets with each other.

Sparv comes with a set of default presets, and you can use the `sparv presets` command to see which are available for
your corpus, and which annotations they include.
Presets are defined in YAML files and can be found in the [Sparv data
directory](installation-and-setup.md#setting-up-sparv) under `config/presets`. You can also add your own
presets just by adding YAML files to this directory.

It is possible to exclude specific annotations from a preset by using the `not` keyword. In the following example we are
including all SALDO annotations except for the compound analysis attributes:
```yaml
export:
    annotations:
        - SWE_DEFAULT.saldo
        - not <token>:saldo.compwf
        - not <token>:saldo.complemgram
```

> [!NOTE]
> Preset files may define their own `class` default values. These will be set automatically when using a preset.
> You can override these in your config files if you know what you are doing.


## Parent Configuration
If you have multiple corpora with similar configurations where only some variables differ for each corpus (e.g. the
corpus ID), you may add a reference to a parent configuration file from your individual corpus config files. Specify the
path to the parent config file in the `parent` variable, and your corpus configuration will inherit all the parameters
from it that are not explicitly specified in the individual config file. Using a list, multiple parents can be
specified, each parent overriding any conflicting values from previous parents. Nested parents are also allowed, i.e.
parents referencing other parents.

```yaml
parent: ../parent-config.yaml
metadata:
    id: animals-foxes
    name:
        swe: 'Djurkorpus: Rävar'
```
The above configuration will contain everything specified inside `../parent-config.yaml` but the values for
`metadata.id` and `metadata.name.swe` will be overridden with `animals-foxes` and `Djurkorpus: Rävar` respectively.


## Custom Annotations
The `custom_annotations` section of the config file is used for three different purposes, each explained
separately below.

### Built-in Utility Annotations
Most annotators in Sparv can be customised by using configuration variables, but are still usable even without
changing their default configuration. Sparv also comes with another type of annotator, that _needs_ to be configured
to be used, and instead of configuration variables, they use parameters. We call these "utility annotators", and the
purpose of these utility annotators is often to modify other annotations. The `misc:affix` annotator for example,
can be used to add a prefix and/or a suffix string to another annotation.

To include a utility annotation in your corpus, it first needs to be configured in the `custom_annotations` section of
your config. If we use `misc:affix` as an example, it could look like this:

```yaml
custom_annotations:
    - annotator: misc:affix
      params:
          out: <token>:misc.word.affixed
          chunk: <token:word>
          prefix: "|"
          suffix: "|"
```

Here we are using the word annotation as input and add the string "|" as prefix and suffix.
First we specify the annotator we want to use (`annotator`), and then use the `params` section to set
values for the annotator's parameters. The `sparv modules` command will show you the list of parameters for each
utility annotator (and this is also how you recognise a utility annotator in that list).
For this particular annotator the parameters are as follows:
1. `out`: What your output annotation should be called. The output name must always include the module name as a prefix,
   in this case `misc`.
2. `chunk`: What annotation you want to use as input (the chunk).
3. `prefix` and `suffix`: The string that you want to use as prefix and/or suffix.

In order to include this annotation in your corpus, you then need to add `<token>:misc.word.affixed` to an annotations
list in your corpus config (e.g. `export.annotations`). This example is applied in the standard-swe [example
corpus](https://github.com/spraakbanken/sparv-pipeline/releases/latest/download/example_corpora.zip).

You can use the same annotator multiple times as long as you name the outputs differently:
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
> Custom annotations always result in new annotations; they do not modify existing ones.

> [!NOTE]
> When a parameter for a custom annotator requires a regular expression (e.g. in `misc:find_replace_regex`), the
> expression must be surrounded by single quotation marks. Regular expressions inside double quotation marks in
> YAML are not parsed correctly.

### Reusing Regular Annotations
Another use for `custom_annotations` is when you want to use a regular (non-utility) annotation more than once in
your corpus. One example is if you want to use the same part-of-speech tagger multiple times, but with different models.

In order to do this you specify the annotator in the `custom_annotations` section of your corpus config, and add a
`config` section, under which you add configuration for the annotator just like you would normally do in the root of
the configuration file.
To give this alternative annotation a unique name, you also have to add a `suffix` which will then be added to the
original annotation name.

In the example below we are reusing the `hunpos:msdtag` annotator with a custom model.
```yaml
custom_annotations:
    - annotator: hunpos:msdtag
      suffix: -mymodel
      config:
          hunpos:
              model: path/to/my_hunpos_model
```
The regular Hunpos annotation is named `<token>:hunpos.msd`, but with the specified suffix this new annotation
will be named `<token>:hunpos.msd-mymodel`, which can then be referred to in the list of annotations:

```yaml
export:
    annotations:
        - <token>:hunpos.msd
        - <token>:hunpos.msd-mymodel
```

### User-defined Custom Annotators
Extending Sparv with new annotators is typically done by creating a plugin, which when installed becomes available
to all your corpora. An alternative to creating a plugin is creating a user-defined custom annotator. It is very
similar to a plugin, but is available only to the corpus in the same directory.

The full documentation for how to write a Sparv annotator can be found in the [developer's
guide](../developers-guide/writing-sparv-plugins.md#module-code), but here is a quick example.

> [!TIP]
> The following example uses the `@annotator` decorator for creating an annotator, but it is possible to create
> your own importer, exporter, installer or model builder using the appropriate Sparv decorator. You can read more about
> decorators in the [developer's guide](../developers-guide/sparv-decorators.md).

Creating a user-defined custom annotator involves the following three steps:
1. Create a Python script with an annotator and place it in your corpus directory
2. Register the annotator in your corpus config
3. Use your custom annotation by referring to it in an annotations list

**Step 1**: Add your user-defined custom annotator by creating a Python script in your corpus directory, e.g.
`convert.py`:
```
mycorpus/
├── config.yaml
├── convert.py
└── source
    ├── document1.xml
    └── document2.xml
```

Sparv will automatically detect scripts placed here as long as your functions are registered in your
config (see Step 2). Your annotator function must use one of the Sparv decorators (usually `@annotator`). Here is a code example for a simple annotator that converts all tokens to upper case:
```python
from sparv.api import Annotation, Output, annotator

@annotator("Convert every word to uppercase.")
def uppercase(word: Annotation = Annotation("<token:word>"),
              out: Output = Output("<token>:custom.convert.upper")):
    """Convert to uppercase."""
    out.write([val.upper() for val in word.read()])
```

**Step 2**: Now register your custom annotator in your corpus config in the `custom_annotations` section so Sparv can
find it. The name of your annotator is composed of:
- the prefix `custom.`
- followed by the filename of the Python file without extension (`convert` in our example)
- followed by a colon
- and finally the annotator name (`uppercase`)

```yaml
custom_annotations:
    - annotator: custom.convert:uppercase
```

**Step 3**: Now you can go ahead and use the annotation created by your custom annotator. Just add the annotation
name given by the `out` parameter value to an annotations list in your corpus config:
```yaml
export:
    annotations:
        - <token>:custom.convert.upper
```

In this example all parameters in the annotator function have default values which means that you do not need to supply
any parameter values in your config. But of course you can override the default values:
```yaml
custom_annotations:
    - annotator: custom.convert:uppercase
      params:
          out: <token>:custom.convert.myUppercaseAnnotation
```

> [!NOTE]
> When using custom annotations from your own code all output annotations must be prefixed with `custom`.

There is an example of a user-defined custom annotator in the standard-swe
[example corpus](https://github.com/spraakbanken/sparv-pipeline/releases/latest/download/example_corpora.zip).

If you need more information on how to write an annotator function please refer to the [developer's
guide](../developers-guide/writing-sparv-plugins.md#module-code). If you have written a rather general annotator module, you
could consider making it into a Sparv plugin. This way other people will be able to use your annotator. Read more about
writing plugins in the [developer's guide](../developers-guide/writing-sparv-plugins.md).
