# Config Parameters

A Sparv user can steer and customise the use of Sparv functions to some extent by setting config parameters in the
[corpus config file](user-manual/corpus-configuration.md). Each function decorated with a [Sparv
decorator](developers-guide/sparv-decorators) (except for wizard functions) may take a `config` argument which contains
a list of config parameters, their descriptions and optional default values. The config parameters declared here can
then be referenced in the function's arguments:
```python
@annotator("Dependency parsing using MaltParser", language=["swe"], config=[
    Config("malt.jar", default="maltparser-1.7.2/maltparser-1.7.2.jar",
           description="Path name of the executable .jar file"),
    Config("malt.model", default="malt/swemalt-1.7.2.mco", description="Path to Malt model")
])
def annotate(maltjar: Binary = Binary("[malt.jar]"),
             model: Model = Model("[malt.model]"),
             ...):
    ...
    process = maltstart(maltjar, model)
    ...
```

Config parameters can also be declared in the module's `__init__.py` file, using the global variable `__config__`:
```python
__config__ = [
    Config("korp.remote_host", description="Remote host to install to"),
    Config("korp.mysql_dbname", description="Name of database where Korp data will be stored")
]
```

A Sparv function must never try to read any config values inside the function body. Config parameters are always
accessed via the function's arguments as shown in the above example. It is important to let the Sparv core handle the
reading of the corpus configuration in order for the internal [config hierarchy](#config-hierarchy) and [config
inheritance](#config-inheritance) to be respected and treated correctly.

To be able to use a config parameter inside a Sparv function it must first be declared in a Sparv decorator or in a
module's init file. However, a config parameter used inside a Sparv function does not necessarily have to be declared in
the decorator belonging to that same function, but the declaration may be done in a decorator belonging to a different
Sparv function, or even a different module.

Please note that it is mandatory to set a description for each declared config parameter. These descriptions are
displayed to the user when lising modules with the `sparv modules` command.


## Config hierarchy

When Sparv processes the corpus configuration it will look for config values in four different places in the indicated
priority order:
1. the corpus configuration file
2. a parent corpus configuration file
2. the default configuration file in the [Sparv data directory](user-manual/installation-and-setup.md#setting-up-sparv)
3. config default values defined in the Sparv decorators (as shown above)

This means that if a config parameter is given a default value in a Sparv decorator it can be overridden by the default
configuration file which in turn can be overridden by the user's corpus config file.


## Config Inheritance

Sparv importers and exporters inherit their configuration from the more general config categories `import` and `export`.
For example when setting `export.annotations` as follows:
```yaml
export:
    annotations:
        - <token>:hunpos.pos
        - <token>:saldo.baseform
```
the config parameter `csv_export.annotations` belonging to the CSV exporter will automatically be set to the same value
(unless it is explicitly set to another value in the corpus config file):
```yaml
csv_export:
    annotations:
        - <token>:hunpos.pos
        - <token>:saldo.baseform
```

This means that when writing an importer or exporter you should try to use the same predefined configuration key names
wherever it makes sense unless you have a good reason not to. Here is a list of all the existing configuration keys
for the `import` and the `export` categories that are inherited by importers and exporters:

Inheritable configuration keys for `import`:

| config key           | description |
|:---------------------|:------------|
| `text_annotation`    | The annotation representing one text. Any text-level annotations will be attached to this annotation.
| `encoding`           | Encoding of source file. Defaults to UTF-8.
| `keep_control_chars` | Set to True if control characters should not be removed from the text.
| `normalize`          | Normalize input using any of the following forms: 'NFC', 'NFKC', 'NFD', and 'NFKD'.
| `source_dir`         | The path to the directory containing the source files relative to the corpus directory.

Inheritable configuration keys for `export`:

| config key | description  |
|:-----------|:-------------|
|`default`                  | Exports to create by default when running 'sparv run'.
|`source_annotations`       | List of annotations from the source file to be kept.
|`annotations`              | List of automatic annotations to include.
|`word`                     | The token strings to be included in the export.
|`remove_module_namespaces` | Set to false if module name spaces should be kept in the export.
|`sparv_namespace`          | A string representing the name space to be added to all annotations created by Sparv.
|`source_namespace`         | A string representing the name space to be added to all annotations present in the source.
|`scramble_on`              | Chunk to scramble the XML export on.
