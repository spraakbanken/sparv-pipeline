# -*- coding: utf-8 -*-

"""
Interface to the Porter Snowball Stemmer:
http://snowball.tartarus.org/

This version makes use of the Python wrapper:
http://pypi.python.org/pypi/PyStemmer/
"""

import util
import Stemmer as Snowball

def stem(out, word, language=util.SWE):
    stemmer = Snowball.Stemmer(language)
    util.write_annotation(out, util.read_annotation_iteritems(word), stemmer.stemWord)


if __name__ == '__main__':
    util.run.main(stem)

