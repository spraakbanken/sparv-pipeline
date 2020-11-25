# Corpus Configuration
To be able to annotate a corpus with Sparv you will need to create a corpus config file. A corpus config file is written
in [YAML](https://docs.ansible.com/ansible/latest/reference_appendices/YAMLSyntax.html), a fairly human-readable format
for creating structured data. This file contains information about your corpus (metadata) and instructions for Sparv on
how to process it. The [corpus config wizard](#corpus-config-wizard) can help you create one. If you want to see some
examples of config files you can download the [example
corpora](https://github.com/spraakbanken/sparv-pipeline/releases/download/v4.0/example_corpora.zip).

A minimal config file contains a corpus ID, information about which annotation represents a document (for XML input this
would refer to an XML element, and if your input documents are plain text each document will be regarded as a document
annotation) and a list of (automatic) annotations you want to be included in the output. Here is an example of a small
config file:
```yaml
metadata:
    # Corpus ID (Machine name, only lower case ASCII letters (a-z) and "-" allowed. No white spaces.)
    id: mini-swe
import:
    # The annotation representing one text document. Any text-level annotations will be attached to this annotation.
    document_annotation: text
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
corpus and the annotations you would like Sparv to add to it. Run `sparv wizard` in order to start the tool. When
running this command in a folder where a corpus config file exists already, Sparv will read the config file and set the
wizard default values according to the existing configuration.

The wizard is an auxiliary tool to get you started with your corpus config file and it does not cover all of Sparv's
advanced functionality. However, a config file that was created with the wizard can of course be edited manually
afterwards, e.g. for adding more advanced configuration details such as [custom annotations](#custom-annotations) and
[headers](#headers).


## Default Values
Some config variables such as `metadata`, `classes`, `import`, `export` and `custom_annotations` are general and are
used by multiple Sparv modules, while others are specific to one particular annotation module (e.g. `hunpos.binary`
defines the name of the binary the hunpos module uses to run part-of-speech tagging). These module specific config
options usually have default values which are defined by the module itself.

When running Sparv your corpus config will be read and combined with Sparv's default config file (`config_default.yaml`
in the [Sparv data directory](user-manual/installation-and-setup.md#setting-up-sparv)) and the default values defined by
different Sparv modules. You can view the resulting configuration by running `sparv config`. Using the `config` command
you can also ask for specific config values, e.g. `sparv config metadata.id`. All default values can be overridden in
your own corpus config.

There are a few config options that must be set (either through the default config or the corpus config):
  - `metadata.id`
  - `metadata.language` (default: `swe`)
  - `import.importer` (default: `xml_import:parse`)
  - `export.annotations`
  - `classes.token` (default: `segment.token`)
  - `classes.sentence` (default: `segment.sentence`)
  - **TODO** What more?


## Import Options
The `import` section of your corpus config is used to give Sparv some information about your input documents (i.e. your
corpus). 

- `import.source_dir` defines the location of your input documents and it defaults to `source`. Sparv will check the
  source directory recursively for valid input documents to process.

- `import.importer` is used to tell Sparv which importer to use to process your corpus documents. The setting you want
  to choose depends on the format of your input documents. If your corpus is in XML you should choose `xml_import:parse`
  (this is the default setting), if your corpus documents are in plain text, you should choose `text_import:parse`
  instead.

- `import.document_annotation` specifies the annotation representing one text document. Any text-level annotations will
  be attached to this annotation. For XML input this refers to an XML element. For plain text input a default `text`
  root annotation will be created automatically and you won't have to change this setting.

- `import.encoding` specifies the encoding of the source documents. It defaults to UTF-8.

- `import.normalize` lets you normalize unicode symbols in the input using any of the following forms: 'NFC', 'NFKC',
  'NFD', and 'NFKD'. It defaults to `NFC`.

- `import.keep_control_chars` may be set to `True` if control characters should not be removed from the text. This
  should normally not be done.

Each importer may have additional options which can be listed with `sparv modules --importers`. The XML importer for
example has an option that lets you rename elements and attributes from your source files using the `as` syntax:
```yaml
xml_import:
    elements:
        - paragraph as p
        - paragraph:n as id
```
There is also an option that allows you to skip importing the contents of certain elements and options that give you
fine-grained control over importing XML headers. Run `sparv modules --importers xml_import` for more details.


## Export Options
The `export` section of your corpus config defines what the output data (or export) looks like. With the config option
`export.source_annotations` you can tell Sparv what elements and attributes present in your input data you would like to
keep in your output data (this only applies if your input data is XML). If you don't specify anything, everything will
be kept in the output. If you do list anything here, make sure that you include the root element (i.e. the element that
encloses all other included elements and text content) for each of your input documents. If you don't, the resulting
output XML will be invalid and Sparv won't be able to produce XML files. If you only want to produce other output
formats than XML you don't need to worry about this.

It is possible to rename elements and attributes present in your input data. Let's say your documents contain elements
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

**Hint:** If you want to produce multiple output formats with the same annotations you can use YAML
[anchors](https://docs.ansible.com/ansible/latest/user_guide/playbooks_advanced_syntax.html#yaml-anchors-and-aliases-sharing-variable-values)
to avoid copying and pasting the same settings.

The option `export.default` defines a list of export formats that will be produced when running `sparv run`. Per default
it only contains `xml_export:pretty`, the formatted XML export with one token per line. 

There are a couple of export options concerning XML namespaces. You can chose to prefix all annotations produced by
Sparv with a custom prefix with the `export.sparv_namespace` option. Likewise you can add a prefix to all elements and
attributes existing in your input with the `export.source_namespace` option.

The option `export.remove_module_namespaces` is `true` by default which means that the module name prefixes are removed
in the annotations. Turning the option off will result in output like:
```xml
<segment.token hunpos.pos="IN" saldo.baseform="|hej|">Hej</segment.token>
```
instead of the more compact:
```xml
<token pos="IN" baseform="|hej|">Hej</token>
```

`export.scramble_on` is a setting used by all the export formats that support scrambling. It controls on what annotation
your corpus will be scrambled. Typical settings are `export.scramble_on: <sentence>` or `export.scramble_on:
<paragraph>`.

The option `export.word` is used to define the strings to be output as tokens in the export. By default this is set to
`<token:word>`. A useful application for this setting is anonymisation of texts. If you want to produce XML containing
only annotations but not the actual text, you could set `export.word: <token>:anonymised` to get output like this:
```xml
    <sentence id="b1ac">
      <token pos="IN">***</token>
      <token pos="MAD">*</token>
    </sentence>
```
**Note:** For technical reasons the export `xml_export:preserved_format` does not respect this setting. The preserved
format XML will always include the original corpus text.

Each exporter may have additional options which can be listed with `sparv modules --exporters`.


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
combine different presets with each other. You can find the presets in the [Sparv data
directory](user-manual/installation-and-setup.md#setting-up-sparv) (in the `config/presets` folder) and here you can
even add your own preset files if you like. You can list all available presets for your corpus (and which annotations
they include) with `sparv presets`.

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
by Sparv as soon as you store them in `config/presets` in the [Sparv data directory](user-manual/installation-and-setup.md#setting-up-sparv).


## Parent Configuration
If you have multiple corpora with similar configurations where only some variables differ for each corpus (e.g. the
corpus ID) you may add a reference to a parent configuration file from your individual corpus config files. Specify the
path to the parent config file in the `parent` variable and your corpus configuration will inherit all the parameters
from it that are not explicitely specified in the individual config file. Using a list, multiple parents can be
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
Custom annotations may be used to apply more customised, non-pre-defined annotations to your corpus. The different
usages of custom annotations are explained below.

### Built-in Custom Annotations
Any Sparv annotation can be customised to your own needs by using it as a custom annotation. This means that you can
change its default arguments and thereby affect the resulting annotation. Some Sparv annotators can only be used as
custom annotations as they are lacking default values in their arguments.

The `misc:affix` annotator for example can be used to add a prefix and/or a suffix string to another annotation. When
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

Please note that custom annotations always result in new annotations, they do not modify existing ones.

**Hint:** When using a regular expression as input for a custom rule (e.g. in `misc:find_replace_regex`), the expression
must be surrounded by single quotation marks. Regular expressions inside double quotation marks in YAML are not parsed
correctly.

### Modifying Annotators with Custom Annotations
As previously mentioned, custom annotations may be used to modify the parameters of existing annotation functions even
if they have default values for all their arguments. This comes in handy when you want to use the same annotator
multiple times but with different parameters. In order to do this you specify the annotator and its parameters in the
`custom_annotations` section of your corpus config as explained in the section above. You only need to specify the
parameters you want to modify. In the example below we are re-using the `hunpos:msdtag` function with a custom model and
we are calling the output annotation `<token>:hunpos.msd.myHunposModel`:
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
declared in the `custom_annotations` section of your corpus config. Place your python script inside your corpus
directory and Sparv will be able to find it. There is an example of a user-defined custom annotation in the standard-swe
example corpus. The code for a simple annotator that converts all tokens to upper case looks like this:

```python
from sparv import Annotation, Output, annotator

@annotator("Convert every word to uppercase.")
def uppercase(word: Annotation = Annotation("<token:word>"),
              out: Output = Output("<token>:custom.convert.upper")):
    """Convert to uppercase."""
    out.write([val.upper() for val in word.read()])
```

The custom rule is then declared in your corpus config using the prefix `custom` followed by the file name (without
extension) and finally the annotator name. If the above code is contained in a file called `convert.py` it would be
referenced like this:
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

If you need more information on how to write an annotation function please refer to the [developer's
guide](developers-guide/writing-sparv-modules). If you have written a rather general annotation module you could
consider writing a Sparv plugin. This way others will be able to use your annotator. Read more about writing plugins in
the [developer's guide](developers-guide/writing-plugins).
