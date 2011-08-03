# -*- coding: utf-8 -*-

import util
import codecs
import os


def edit_info(infofile, key, value="", valuefile=""):
    content = []
    existing = False
    
    if valuefile:
        with codecs.open(valuefile, mode="r", encoding="UTF-8") as V:
            value = V.read()

    if os.path.exists(infofile):
        with codecs.open(infofile, mode="r", encoding="UTF-8") as F:
            content = F.readlines()
    
        for i in range(len(content)):
            if content[i].split(": ")[0] == key:
                existing = True
                content[i] = "%s: %s" % (key, value)
                break

    if not existing:
        content.append("%s: %s" % (key, value))

    with codecs.open(infofile, mode="w", encoding="UTF-8") as O:
        O.writelines(content)

if __name__ == '__main__':
    util.run.main(edit=edit_info,
                  )