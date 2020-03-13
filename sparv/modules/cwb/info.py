# -*- coding: utf-8 -*-
import sparv.util as util
import os
import time


def edit_info(infofile, key, value="", valuefile=""):
    """Save information to the file specified by 'infofile'.
    'key' and 'value' specify the key and value. Alternatively 'valuefile'
    can be used as input for the value. The value file must contain only one
    row of text."""

    content = []
    existing = False

    if valuefile:
        with open(valuefile, mode="r", encoding="UTF-8") as V:
            value = V.read().strip()

    if value == "%DATE%":
        value = time.strftime("%Y-%m-%d")

    if os.path.exists(infofile):
        with open(infofile, mode="r", encoding="UTF-8") as F:
            content = F.readlines()

        for i in range(len(content)):
            if content[i].split(": ")[0] == key:
                existing = True
                content[i] = "%s: %s\n" % (key, value)
                break

    if not existing:
        content.append("%s: %s\n" % (key, value))

    with open(infofile, mode="w", encoding="UTF-8") as O:
        O.writelines(content)

if __name__ == '__main__':
    util.run.main(edit=edit_info,
                  )
