# Available Analyses

This section provides an overview of some of the built-in analyses available within Sparv and the Sparv plugins
developed by Språkbanken Text. Note that this is not an exhaustive list of available annotations but rather a summary of
the linguistic analyses. Technical annotations (e.g., automatic assignment of IDs or calculation of whitespace
information) are not included here. For a complete list of analyses, refer to the output of the `sparv modules` command.

> [!NOTE]
>
> **Annotations** refer to the names of the annotations as they appear in the corpus config file under the
> `export.annotations` section (learn more in the [corpus configuration
> section](corpus-configuration.md#export-options)). Please note that the annotations usually have shorter names in the
> corpus exports.
>
> **Annotators** are the names of the functions (including their module names) used to produce the annotations. These
> can be executed directly with the `sparv run-rule [annotator]` command. However, this is generally unnecessary, as
> they are automatically executed when running the `sparv run` command if their corresponding annotations are included
> in the corpus config file.

## Analyses for contemporary Swedish

For analysing texts in contemporary Swedish we recommend using the [annotation
preset](corpus-configuration.md#annotation-presets) called `SWE_DEFAULT`.

### Sentence segmentation with PunktSentenceTokenizer

|    |            |
|:---|:-----------|
|**Description** | Texts are split into sentences.|
|**Model**       | [punkt-nltk-svenska.pickle](https://github.com/spraakbanken/sparv-models/blob/master/segment/punkt-nltk-svenska.pickle?raw=true) trained on [StorSUC](https://spraakbanken.gu.se/resurser/storsuc)|
|**Method**      | The model is built with [NLTK's PunktTrainer](https://www.nltk.org/api/nltk.tokenize.html?highlight=punkttrainer#nltk.tokenize.punkt.PunktTrainer). The segmentation is done with NLTK's [PunktSentenceTokenizer](https://www.nltk.org/api/nltk.tokenize.html?highlight=punktsentencetokenizer#nltk.tokenize.punkt.PunktSentenceTokenizer).|
|**Annotations** | `segment.sentence` (sentence segments)|
|**Annotators**  | `segment:sentence`|

### Tokenization

|    |            |
|:---|:-----------|
|**Description** | Sentence segments are split into tokens.|
|**Model**       | - [configuration file bettertokenizer.sv](https://raw.githubusercontent.com/spraakbanken/sparv-models/master/segment/bettertokenizer.sv) <br />- word list `bettertokenizer.sv.saldo-tokens` built upon [SALDOs morphology](https://spraakbanken.gu.se/resurser/saldo) (it is built automatically by Sparv)|
|**Method**      | Tokenizer using regular expressions and lists of words containing special characters and common abbreviations. Sparv's version is custom-made for Swedish but it is possible to configure it for other languages.|
|**Annotations** | `segment.token` (token segments)|
|**Annotators**  | `segment:tokenize`|

### POS-tagging with Stanza

|    |            |
|:---|:-----------|
|**Description** | Sentence segments are analysed to enrich tokens with part-of-speech tags and morphosyntactic information.|
|**Tool**        | [Stanza](https://stanfordnlp.github.io/stanza/)|
|**Model**       | <https://spraakbanken.gu.se/resurser/stanzamorph>|
|**Tagset**      | - [SUC MSD tags](https://spraakbanken.gu.se/korp/markup/msdtags.html) <br />- [Universal features](https://universaldependencies.org/u/feat/index.html)|
|**Annotations** | - `<token>:stanza.pos` (part-of-speech tag) <br />- `<token>:stanza.msd` (morphosyntactic tag) <br />- `<token>:stanza.ufeats` (universal features)|
|**Annotators**  | `stanza:msdtag`|

### Translation from SUC to UPOS

|    |            |
|:---|:-----------|
|**Description**  | SUC part-of-speech tags are translated to UPOS. Not used by default because the translations are not very reliable.|
|**Model**        | Method has no model. A translation table is used.|
|**Tagset**       | [Universal POS tags](https://universaldependencies.org/u/pos/index.html)|
|**Annotations**  | - `<token>:misc.upos` (universal part-of-speech tag)|
|**Annotators**   | `misc:upostag`|

### POS-tagging with Hunpos

|    |            |
|:---|:-----------|
|**Description**  | Sentence segments are analysed to enrich tokens with part-of-speech tags and morphosyntactic information. No longer used by default because Stanza's POS-tagging yields better results.|
|**Tool**         | [Hunpos](https://code.google.com/archive/p/hunpos/)|
|**Model**        | [suc3_suc-tags_default-setting_utf8.model](https://github.com/spraakbanken/sparv-models/blob/master/hunpos/suc3_suc-tags_default-setting_utf8.model?raw=true) trained on [SUC 3.0](https://spraakbanken.gu.se/resurser/suc3)|
|**Tagset**       | [SUC MSD tags](https://spraakbanken.gu.se/korp/markup/msdtags.html)|
|**Annotations**  | - `<token>:hunpos.msd` (morphosyntactic tag) <br />- `<token>:hunpos.pos` (part-of-speech tag)|
|**Annotators**   | - `hunpos:msdtag` <br />- `hunpos:postag`|

### Dependency parsing with Stanza

|    |            |
|:---|:-----------|
|**Description**  | Sentence segments are analysed to enrich tokens with dependency information.|
|**Tool**         | [Stanza](https://stanfordnlp.github.io/stanza/)|
|**Model**        | <https://spraakbanken.gu.se/resurser/stanzasynt>|
|**Tagset**       | [Mamba-Dep](https://svn.spraakdata.gu.se/sb-arkiv/pub/mamba.html)|
|**Annotations**  | - `<token>:stanza.ref` (the token position within the sentence) <br />- `<token>:stanza.dephead_ref` (dependency head, the ref of the word which the current word modifies or is dependent of) <br />- `<token>:stanza.deprel` (dependency relation, the relation of the current word to its dependency head)|
|**Annotators**   | - `stanza:dep_parse` <br />- `stanza:make_ref`|

### Dependency parsing with MaltParser

|    |            |
|:---|:-----------|
|**Description**  | Sentence segments are analysed to enrich tokens with dependency information. No longer used by default because Stanza's dependency parsing yields better results.|
|**Tool**         | [MaltParser](https://www.maltparser.org/download.html)|
|**Model**        | [swemalt](https://www.maltparser.org/mco/swedish_parser/swemalt.html) trained on [Svensk trädbank](https://spraakbanken.gu.se/resurser/sv-treebank)|
|**Tagset**       | [Mamba-Dep](https://svn.spraakdata.gu.se/sb-arkiv/pub/mamba.html)|
|**Annotations**  | - `<token>:malt.ref` (the token position within the sentence) <br />- `<token>:malt.dephead_ref` (dependency head, the ref of the word which the current word modifies or is dependent of) <br />- `<token>:malt.deprel` (dependency relation, the relation of the current word to its dependency head)|
|**Annotators**   | - `malt:annotate` <br />- `malt:make_ref`|
|**Installation** | See the [installation and Setup section](installation-and-setup.md#maltparser) for more information.|

### Phrase structure parsing

|    |            |
|:---|:-----------|
|**Description**  | [Mamba-Dep](https://svn.spraakdata.gu.se/sb-arkiv/pub/mamba.html) dependencies produced by the dependency analysis are converted to phrase structures.|
|**Model**        | Method has no model.|
|**Annotations**  | - `phrase_structure.phrase` (phrase segments) <br />- `phrase_structure.phrase:phrase_structure.name` (name of the phrase segment) <br />- `phrase_structure.phrase:phrase_structure.func` (function of the phrase segment)|
|**Annotators**   | `phrase_structure:annotate`|

### Lexical SALDO-based analyses

|    |            |
|:---|:-----------|
|**Description**  | Tokens and their POS tags are looked up in the SALDO lexicon in order to enrich them with more information.|
|**Model**        | [SALDO morphology](https://spraakbanken.gu.se/resurser/saldo)|
|**Tagset**       | [SALDO tags](https://spraakbanken.gu.se/resurser/saldo/taggmangd) for lemgrams|
|**Annotations**  | - `<token>:saldo.baseform` (lemma) <br />- `<token>:saldo.lemgram` (lemgrams, identifying the inflectional table) <br />- `<token>:saldo.sense` (identify senses in SALDO)|
|**Annotators**   | `saldo:annotate`|

### Lemmatization with Stanza

|    |            |
|:---|:-----------|
|**Description**  | Sentence segments are analysed to enrich tokens with lemmas.|
|**Tool**         | [Stanza](https://stanfordnlp.github.io/stanza/)|
|**Model**        | <https://spraakbanken.gu.se/resurser/stanzasynt>|
|**Annotations**  | - `<token>:stanza.baseform` (lemma)|
|**Annotators**   | `stanza:annotate_swe`|

### Sense disambiguation

|    |            |
|:---|:-----------|
|**Description**  | SALDO IDs from the `<token>:saldo.sense`-attribute are enriched with likelihoods.|
|**Tool**         | [Sparv wsd](https://github.com/spraakbanken/sparv-wsd)|
|**Documentation**| [Running the Koala word sense disambiguators](https://github.com/spraakbanken/sparv-wsd/blob/master/README.pdf)|
|**Model**        | - [ALL_512_128_w10_A2_140403_ctx1.bin](https://github.com/spraakbanken/sparv-wsd/blob/master/models/scouse/ALL_512_128_w10_A2_140403_ctx1.bin) <br />- [lem_cbow0_s512_w10_NEW2_ctx.bin](https://github.com/spraakbanken/sparv-wsd/blob/master/models/scouse/lem_cbow0_s512_w10_NEW2_ctx.bin)|
|**Annotations**  | - `<token>:wsd.sense` (identifies senses in SALDO along with their likelihoods)|
|**Annotators**   | `wsd:annotate`|
|**Installation** | See the [installation and Setup section](installation-and-setup.md#sparv-wsd) for more information.|

### Compound analysis with SALDO

|    |            |
|:---|:-----------|
|**Description**  | Tokens and their POS tags are looked up in the SALDO lexicon in order to enrich them with compound information. More information (in Swedish) is found in the [Språkbanken Text FAQ ("Hur fungerar Sparvs sammansättningsanalys?")](https://spraakbanken.gu.se/faq/hur-fungerar-sparvs-sammansattningsanalys). Lemmas are enriched in this analysis.|
|**Model**        | - [SALDO morphology](https://spraakbanken.gu.se/resurser/saldo) <br />- [NST pronunciation lexicon for Swedish](https://www.nb.no/sprakbanken/en/resource-catalogue/oai-nb-no-sbr-22/) <br />- [word frequency statistics from Korp](https://svn.spraakdata.gu.se/sb-arkiv/pub/frekvens/stats_all.txt.zip)|
|**Annotations**  | - `<token>:saldo.complemgram` (compound lemgrams including a comparison score) <br />- `<token>:saldo.compwf` (compound word forms) <br />- `<token>:saldo.baseform2` (lemma)|
|**Annotators**   | `saldo:compound`|

### Sentiment analysis with SenSALDO

|    |            |
|:---|:-----------|
|**Description**  | Tokens and their SALDO IDs are looked up in SenSALDO in order to enrich them with sentiments.|
|**Model**        | [SenSALDO](https://spraakbanken.gu.se/resurser/sensaldo)|
|**Annotations**  | - `<token>:sensaldo.sentiment_label` (sentiment) <br />- `<token>:sensaldo.sentiment_score` (sentiment value)|
|**Annotators**   | `sensaldo:annotate`|

### Named entity recognition with HFST-SweNER

|    |            |
|:---|:-----------|
|**Description**  | Sentence segments are analysed and enriched with named entities.|
|**Tool**         | [hfst-SweNER](https://urn.fi/urn%3Anbn%3Afi%3Alb-2021101202)|
|**Model**        | included in the tool|
|**referenser**  | - [HFST-SweNER – A New NER Resource for Swedish](http://www.lrec-conf.org/proceedings/lrec2014/pdf/391_Paper.pdf) <br />- [Reducing the effect of name explosion](http://demo.spraakdata.gu.se/svedk/pbl/kokkinakisBNER.pdf)|
|**Tagset**       | [HFST-SweNER tags](https://svn.spraakdata.gu.se/sb-arkiv/pub/swener-tags.html)|
|**Annotations**  | - `swener.ne` (named entity segment) <br />- `swener.ne:swener.name` (text in the entire named entity segment) <br />- `swener.ne:swener.ex` (named entity; name expression, numerical expression or time expression) <br />- `swener.ne:swener.type` (named entity type) <br />- `swener.ne:swener.subtype` (named entity subtype)|
|**Annotators**   | `swener:annotate`|
|**Installation** | See the [installation and Setup section](installation-and-setup.md#hfst-swener) for more information.|

### Readability metrics

|    |            |
|:---|:-----------|
|**Description**  | Documents are analysed in order to enrich them with readability metrics.|
|**Model**        | Method has no model.|
|**Annotations**  | - `<text>:readability.lix` (the Swedish readability metric LIX, läsbarhetsindex) <br />- `<text>:readability.ovix` (the Swedish readability metric OVIX, ordvariationsindex) <br />- `<text>:readability.nk` (the Swedish readability metric nominalkvot (noun ratio))|
|**Annotators**   | - `readability:lix` <br />- `readability:ovix` <br />- `readability:nominal_ratio`|

### Lexical classes

|    |            |
|:---|:-----------|
|**Description**  | Tokens are looked up in Blingbring and SweFN in order to enrich them with information about their lexical classes. Documents are then enriched with information about lexical classes based on which classes are common for the tokens within them.|
|**Model**        | - [Blingbring](https://spraakbanken.gu.se/resurser/blingbring) <br />- [Swedish FrameNet (SweFN)](https://spraakbanken.gu.se/resurser/swefn)|
|**Annotations**  | - `<token>:lexical_classes.blingbring` (lexical class from the Blingbring resource per token <br />- `<token>:lexical_classes.swefn` (frames from Swedish FrameNet (SweFN) per token <br />- `<text>:lexical_classes.blingbring` (lexical class from the Blingbring resource per dokument) <br />- `<text>:lexical_classes.swefn` (frames from Swedish FrameNet (SweFN) per dokument)|
|**Annotators**   | `lexical_classes:blingbring_words` `lexical_classes:swefn_words` `lexical_classes:blingbring_text` `lexical_classes:swefn_text`|

### Geotagging

|    |            |
|:---|:-----------|
|**Description**  | Sentences (and paragraphs, if present) are enriched with place names (and their geographic coordinates) occurring within them. This is based on the place names found by the named entity tagger. Geographical coordinates are looked up in the GeoNames database.|
|**Model**        | [GeoNames](https://www.geonames.org/)|
|**Annotations**  | - `<sentence>:geo.geo_context` (places and their coordinates occurring within the sentence) <br />- `<paragraph>:geo.geo_context` (places and their coordinates occurring within the paragraph)|
|**Annotators**   | `geo:contextual`|

## Analyses for Swedish from the 1800's

We recommend using the [annotation preset](corpus-configuration.md#annotation-presets) called `SWE_1800`. All analyses
available for contemporary Swedish can also be applied to 19th-century Swedish. Additionally, some analyses have been
specifically adapted for this language variety:

### POS-tagging with Hunpos (adapted for 1800-talssvenska)

|    |            |
|:---|:-----------|
|**Description**  | Sentence segments are analysed to enrich tokens with part-of-speech tags and morphosyntactic information.|
|**Tool**         | [Hunpos](https://code.google.com/archive/p/hunpos/)|
|**Model**        | - [suc3_suc-tags_default-setting_utf8.model](https://github.com/spraakbanken/sparv-models/blob/master/hunpos/suc3_suc-tags_default-setting_utf8.model?raw=true) trained on [SUC 3.0](https://spraakbanken.gu.se/resurser/suc3) <br />- a word list along with the words' morphosyntactic information generated from the [Dalin morphology](https://spraakbanken.gu.se/resurser/dalinm) and the [Swedberg morphology](https://spraakbanken.gu.se/resurser/swedbergm)|
|**Tagset**       | [SUC MSD tags](https://spraakbanken.gu.se/korp/markup/msdtags.html)|
|**Annotations**  | - `<token>:hunpos.msd` (morphosyntactic tag) <br />- `<token>:hunpos.pos` (part-of-speech tag)|
|**Annotators**   | - `hunpos:msdtag_hist` <br />- `hunpos:postag`|
|**Installation** | See the [installation and Setup section](installation-and-setup.md#hunpos) for more information.|

### Lexicon-based analyses

|    |            |
|:---|:-----------|
|**Description**  | Tokens and their POS tags are looked up in different lexicons in order to enrich them with more information.|
|**Model**        | - [SALDO morphology](https://spraakbanken.gu.se/resurser/saldo) <br />- [Dalin morphology](https://spraakbanken.gu.se/resurser/dalinm) <br />- [Swedberg morphology](https://spraakbanken.gu.se/resurser/swedbergm) <br />- [Diachronic pivot](https://spraakbanken.gu.se/resurser/diapivot)|
|**Tagset**       | [SALDO tags](https://spraakbanken.gu.se/resurser/saldo/taggmangd) (for lemgrams)|
|**Annotations**  | - `<token>:hist.baseform` (lemma) <br />- `<token>:hist.sense` (identifies senses in SALDO) <br />- `<token>:hist.lemgram` (lemgrams, identifying the inflectional table) <br />- `<token>:hist.diapivot` (SALDO lemgrams from the diapivot model) <br />- `<token>:hist.combined_lemgrams` (SALDO lemgram, combined from SALDO, Dalin, Swedberg and the diapivot model)|
|**Annotators**   | - `hist:annotate_saldo` <br />- `hist:diapivot_annotate` <br />- `hist:combine_lemgrams`|

## Analyses for Old Swedish

We recommend using the [annotation preset](corpus-configuration.md#annotation-presets) called `SWE_FSV`.
All analyses for contemporary Swedish are available for this language variety. However, we do not recommend using them
due to the fact that the spelling often differs too much to give satisfying results. At Språkbanken Text we use the
following analyses for texts written in Old Swedish:

### Sentence segmentation

[Same analysis](#sentence-segmentation-with-punktsentencetokenizer) as for contemporary Swedish.

### Tokenization

[Same analysis](#tokenization) as for contemporary Swedish.

### Spelling variations

|    |            |
|:---|:-----------|
|**Description**  | Tokens are looked up in a model to get common spelling variations.|
|**Model**        | [model for Old Swedish spelling variations](https://media.githubusercontent.com/media/spraakbanken/sparv-models/master/hist/fsv-spelling-variants.txt)|
|**Annotations**  | `<token>:hist.spelling_variants` (possible spelling variations for the token)|
|**Annotators**   | `hist:spelling_variants`|

### Lexicon-based analyses

|    |            |
|:---|:-----------|
|**Description**  | Tokens and their POS tags are looked up in different lexicons in order to enrich them with more information.|
|**Model**        | - [Fornsvensk morphology from Söderwall and Schlyter](https://spraakbanken.gu.se/resurser/fsvm) <br />- [SALDO morphology](https://spraakbanken.gu.se/resurser/saldo) <br />- [Diachronic pivot](https://spraakbanken.gu.se/resurser/diapivot)|
|**Tagset**       | [SALDO tags](https://spraakbanken.gu.se/resurser/saldo/taggmangd) for lemgrams|
|**Annotations**  | - `<token>:hist.baseform` (lemma) <br />- `<token>:hist.lemgram` (lemgrams, identifying the inflectional table) <br />- `<token>:hist.diapivot` (SALDO lemgrams from the diapivot model) <br />- `<token>:hist.combined_lemgrams` (SALDO lemgram, combined from SALDO, Dalin, Swedberg and the diapivot model)|
|**Annotators**   | - `hist:annotate_saldo_fsv` <br />- `hist:diapivot_annotate` <br />- `hist:combine_lemgrams`|

### Homograph sets

|    |            |
|:---|:-----------|
|**Description**  | A set of possible POS tags is extracted from the lemgram annotation.|
|**Model**        | Method has no model.|
|**Tagset**       | [POS tags from the SUC MSD tag set](https://spraakbanken.gu.se/korp/markup/msdtags.html)|
|**Annotations**  | `<token>:hist.homograph_set` (possible part-of-speech tags for the token)|
|**Annotators**   | `hist:extract_pos`|

## Analyses for other languages than Swedish

Sparv supports analyses for a number of different languages. A list of which languages are supported and what analysis
tools are available can be found in the [installation and setup section](installation-and-setup.md#analyzing-languages-other-than-swedish).

### Analyses from TreeTagger

We recommend using the [annotation preset](corpus-configuration.md#annotation-presets) called `TREETAGGER`.

|    |            |
|:---|:-----------|
|**Description**  | Tokenised sentence segments are analysed to enrich tokens with more information.|
|**Tool**         | [TreeTagger](https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/)|
|**Model**        | Different language-dependent parameter files are used. Please check the [TreeTagger web site](https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/) for more information.|
|**Tagset**       | - Different language-dependent POS tag sets are used. Please check the [TreeTagger web page](https://www.cis.uni-muenchen.de/~schmid/tools/TreeTagger/) for more information. <br />- [Universal POS tags](https://universaldependencies.org/u/pos/index.html)|
|**Annotations**  | - `<token>:treetagger.baseform` (lemma) <br />- `<token>:treetagger.pos` (part-of-speech tag, may include morphosyntactic information) <br />- `<token>:treetagger.upos` (universal part-of-speech tags, translated from `<token>:treetagger.pos`)|
|**Annotators**   | `treetagger:annotate`|
|**Installation** | See the [installation and Setup section](installation-and-setup.md#treetagger) for more information.|

### Analyses from FreeLing

We recommend using the [annotation preset](corpus-configuration.md#annotation-presets) called `SBX_FREELING`
or `SBX_FREELING_FULL` (for languages supporting named entity recognition).

|    |            |
|:---|:-----------|
|**Description**  | Entire documents are analysed with FreeLing for sentence segmentation, tokenization and enrichment with other information. FreeLing does not use the same permissive licence as Sparv. Installation of the [Sparv FreeLing plugin](https://github.com/spraakbanken/sparv-freeling) is necessary.|
|**Tool**         | [FreeLing](https://github.com/TALP-UPC/FreeLing)|
|**Model**        | Models for different languages are included in the tool.|
|**Tagset**       | - Different language-dependent POS tagsets (often [EAGLES](http://www.ilc.cnr.it/EAGLES96/annotate/node9.html)). Please check the [FreeLing documentation](https://freeling-user-manual.readthedocs.io/en/v4.2/tagsets/) for more information. <br />- [Universal POS tags](https://universaldependencies.org/u/pos/index.html)|
|**Annotations**  | - `freeling.sentence` (sentence segments from FreeLing) <br />- `freeling.token` (token segments from FreeLing) <br />- `freeling.token:freeling.baseform` (lemma) <br />- `freeling.token:freeling.pos` (part-of-speech tag, often including some morphosyntactic information) <br />- `freeling.token:freeling.upos` (universal part-of-speech tags) <br />- `freeling.token:freeling.ne_type` (named entity type (only available for some languages)|
|**Annotators**   | `freeling:annotate` or `freeling:annotate_full` (depending on the language)|
|**Installation** | See the [installation and Setup section](installation-and-setup.md#freeling) for more information.|

### Analyses from Stanza (for English)

We recommend using the [annotation preset](corpus-configuration.md#annotation-presets) called `STANZA`.

|    |            |
|:---|:-----------|
|**Description**  | Entire documents are analysed with Stanza for sentence segmentation, tokenization and enrichment with other information.|
|**Tool**         | [Stanza](https://stanfordnlp.github.io/stanza/)|
|**Model**        | included in the tool|
|**Tagset**       | - [Universal POS tags](https://universaldependencies.org/u/pos/index.html) <br />- [Universal features](https://universaldependencies.org/u/feat/index.html)|
|**Annotations**  | - `stanza.sentence` (sentence segments from Stanza) <br />- `stanza.ne` (named entity segments from Stanza) <br />- `stanza.ne:stanza.ne_type` (named entity type) <br />- `stanza.token` (token segments from Stanza) <br />- `<token>:stanza.baseform` (lemma) <br />- `<token>:stanza.pos` (part-of-speech tag) <br />- `<token>:stanza.upos` (universal part-of-speech tags) <br />- `<token>:stanza.ufeats` (universal features) <br />- `<token>:stanza.ref` (the token position within the sentence) <br />- `<token>:stanza.dephead_ref` (dependency head, the ref of the word which the current word modifies or is dependent of) <br />- `<token>:stanza.deprel` (dependency relation, the relation of the current word to its dependency head)|
|**Annotators**   | - `stanza:annotate` <br />- `stanza:make_ref`|

### Analyses from Stanford Parser (for English)

We recommend using the [annotation preset](corpus-configuration.md#annotation-presets) called `STANFORD`.

|    |            |
|:---|:-----------|
|**Description**  | Entire documents are analysed with Stanford Parser for sentence segmentation, tokenization and enrichment with other information.|
|**Tool**         | [Stanford Parser](https://nlp.stanford.edu/software/lex-parser.shtml)|
|**Model**        | included in the tool|
|**Tagset**       | - [Penn Treebank tagset](https://www.sketchengine.eu/penn-treebank-tagset/) <br />- [Universal POS tags](https://universaldependencies.org/u/pos/index.html)|
|**Annotations**  | - `stanford.sentence` (sentence segments from Stanford Parser) <br />- `stanford.token` (token segments from Stanford Parser) <br />- `stanford.token:stanford.baseform` (lemma) <br />- `stanford.token:stanford.pos` (part-of-speech tag) <br />- `stanford.token:stanford.upos` (universal part-of-speech tags) <br />- `stanford.token:stanford.ne_type` (named entity type) <br />- `stanford.token:stanford.ref` (the token position within the sentence) <br />- `stanford.token:stanford.dephead_ref` (dependency head, the ref of the word which the current word modifies or is dependent of) <br />- `stanford.token:stanford.deprel` (dependency relation, the relation of the current word to its dependency head)|
|**Annotators**   | - `stanford:annotate` <br />- `stanford:make_ref`|
|**Installation** | See the [installation and Setup section](installation-and-setup.md#stanford-parser) for more information.|
