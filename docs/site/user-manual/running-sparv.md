# Running Sparv

This section contains a guide to running Sparv on the corpus you have prepared according to the instructions in the
previous sections. It also provides an overview of all the key commands available in Sparv.

> [!NOTE]
>
> Sparv is a command line application, and all interactions with Sparv are done through the terminal.

## Annotating Your Corpus with Sparv

Before running Sparv, make sure you have set up your corpus configuration file and placed your source files in the
source directory, as described in the previous sections.

Once you have prepared your corpus, you can start the annotation process by running the `sparv run` command from inside
the corpus directory. This command initiates the annotation process and generates all the output formats specified in
your corpus configuration file. If no output formats are specified, Sparv will use the default export format, which is
the pretty-printed XML format.

Once the annotation process is complete, the generated output files will be stored in an `export` directory within your
corpus directory. The directory structure of your corpus should look something like this:

```text
my_corpus/
├── config.yaml
├── export
│  └── xml_export.pretty
│     ├── document1_export.xml
│     ├── document2_export.xml
│     └── document3_export.xml
├── source
│  ├── document1.xml
│  ├── document2.xml
│  └── document3.xml
└── sparv-workdir
   └── ...
```

The `sparv-workdir` directory contains intermediate files used by Sparv during the annotation process. This directory is
managed by Sparv and should not be manually modified.

Keeping the `sparv-workdir` directory allows Sparv to re-run only the necessary parts of the annotation process when
changes are made to your source files. If you update a model or any other dependency, Sparv will re-run only the
annotations that depend on the updated model, including any subsequent annotations that rely on those initial
annotations. This dependency tracking mechanism ensures that you only re-run the affected parts of the annotation
process, rather than starting from scratch.

However, if you make changes to your *corpus configuration file*, you will need to perform a clean run for the changes
to take effect. Use the `sparv clean --all` command to remove intermediate files and output directories. If you only
changed the list of annotations or export formats, running `sparv clean --export` to remove the `export` directory is
sufficient.

## Other Commands

For an overview of all the commands available in Sparv, see the next section: [Command Line Interface](cli.md).
