"""Create or edit .info file."""

import time

from sparv import Config, Export, ExportInput, annotator


@annotator("CWB Info file")
def edit(out: str = Export("[cwb_datadir]/[id]/.info", absolute_path=True),
         sentences: str = ExportInput("info/sentencecount"),
         firstdate: str = ExportInput("info/datefirst"),
         lastdate: str = ExportInput("info/datelast"),
         protected: bool = Config("protected", False)):
    """Save information to the file specified by 'out'."""
    content = []

    for key, value_obj, is_file in [("Sentences", sentences, True),
                                    ("FirstDate", firstdate, True),
                                    ("LastDate", lastdate, True),
                                    ("Updated", time.strftime("%Y-%m-%d"), False),
                                    ("Protected", protected, False)]:
        if is_file:
            with open(value_obj, mode="r", encoding="UTF-8") as f:
                value = f.read().strip()
        else:
            value = value_obj

        content.append("%s: %s\n" % (key, value))

    # Write .info file
    with open(out, mode="w", encoding="UTF-8") as o:
        o.writelines(content)


# ifeq ($(has_sentences), true)
# $(root)annotations/_list_sentences_: $(files:%=$(root)annotations/%.sentence)
# 	$(call write-to-file0,$@,$+)
# $(root)annotations/sentencecount: $(root)annotations/_list_sentences_
# 	wc -l --files0-from $(1) | tail -1 | grep -oP [0-9]+ | head -1 > $@
# else
#   $(info Info: No sentence information found in corpus)
# $(root)annotations/sentencecount:
# 	echo "0" > $@
# endif

# ifeq ($(filter text:datefrom,$(vrt_structs)),)
# $(root)annotations/datefirst: $(CORPUS_REGISTRY)/$(corpus)
# 	touch $@

# $(root)annotations/datelast: $(CORPUS_REGISTRY)/$(corpus)
# 	touch $@
# else
# $(root)annotations/datefirst: $(CORPUS_REGISTRY)/$(corpus)
# 	cwb-scan-corpus -q $(corpus) text_datefrom text_timefrom | cut -f 2- | sort -n | grep -v -P '^\s+$$' | head -1 | rev | sed -r -e "s/([0-9]{2})([0-9]{2})([0-9]{2})\t([0-9]{2})([0-9]{2})([0-9]{3,4})/\1:\2:\3 \4-\5-\6/" | rev > $@

# $(root)annotations/datelast: $(CORPUS_REGISTRY)/$(corpus)
# 	cwb-scan-corpus -q $(corpus) text_dateto text_timeto | cut -f 2- | sort -n | tail -1 | rev | sed -r -e "s/([0-9]{2})([0-9]{2})([0-9]{2})\t([0-9]{2})([0-9]{2})([0-9]{3,4})/\1:\2:\3 \4-\5-\6/" | rev > $@
# endif
