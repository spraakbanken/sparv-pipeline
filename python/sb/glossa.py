
import os
import subprocess
from glob import glob

import util
from util.mysql_wrapper import MySQL

def create_files(master, localdir, globaldir, glossadir):
    util.log.info("Creating Glossa files in: %s", glossadir)
    util.system.clear_directory(glossadir)
    glossafiles = [os.path.basename(f) for f in glob(os.path.join(localdir, '*'))]
    for name in glossafiles:
        localfile = os.path.join(localdir, name)
        name = name.replace("MASTER", master)
        util.log.info("Creating: %s", name)
        globalfile = os.path.join(globaldir, name.replace(master, "MASTER"))
        if os.path.isfile(globalfile):
            cat = ['cat', globalfile, localfile]
        else:
            cat = ['cat', localfile]
        destfile = os.path.join(glossadir, name)
        with open(destfile, "w") as F:
            subprocess.check_call(cat, stdout=F)
    if not glossafiles:
        util.log.warning("No files to create")


def create_mysql(db_name, master, class_table, text_table, corpus_files, sqlfile):
    if isinstance(corpus_files, basestring):
        corpus_files = corpus_files.split()
    MASTERclass = MASTERtable(master, class_table)
    MASTERtext  = MASTERtable(master, text_table)
    util.log.info("Creating MySQL tables: %s, %s", MASTERclass, MASTERtext)
    mysql = MySQL(db_name, encoding=util.UTF8, output=sqlfile)
    mysql.create_table(MASTERclass, drop=True, **MYSQL_CLASS)
    mysql.create_table(MASTERtext, drop=True,  **MYSQL_TEXT)
    mysql.lock(MASTERclass, MASTERtext)
    for corpus in corpus_files:
        ntokens = int(subprocess.Popen(["wc", "-l", corpus + "." + util.TOKEN], stdout=subprocess.PIPE).communicate()[0].split()[0]) # For Python <2.7
        #ntokens = int(subprocess.check_output(["wc", "-l", corpus + "." + util.TOKEN]).split()[0]) # Much faster than reading annotations, but not available in <2.7
        #ntokens = len(util.read_annotation(corpus + "." + util.TOKEN))
        mysql.add_row(MASTERclass, MYSQL_CLASS_ROW(os.path.basename(corpus), freq=ntokens))
        mysql.add_row(MASTERtext,  MYSQL_TEXT_ROW(os.path.basename(corpus), wordcount=ntokens))
    mysql.unlock()

def create_align(db_name, master, align_table, lang1, lang2, base_files, sqlfile):
    if isinstance(base_files, basestring):
        base_files = base_files.split()
    util.log.info("Reading links")
    rows = []
    for base in base_files:
        links = {lang1: {}, lang2: {}}
        for lang in links:
            for edge, nr in util.read_annotation_iteritems(base + "_" + lang + "." + util.LINK + "." + util.N):
                links[lang].setdefault(nr, []).append(edge)

        for nr in set(links[lang1]) ^ set(links[lang2]):
            util.log.warning("Missing link: %s", nr)

        for nr, edges1 in links[lang1].iteritems():
            for edge2 in links[lang2].get(nr, ()):
                rows += [{'source':edge1, 'target':edge2, 'lang':lang2}
                         for edge1 in edges1]
                rows += [{'source':edge2, 'target':edge1, 'lang':lang1}
                         for edge1 in edges1]

    MASTERalign = MASTERtable(master, align_table)
    util.log.info("Creating MySQL table with %d rows: %s", len(rows), MASTERalign)
    mysql = MySQL(db_name, encoding=util.UTF8, output=sqlfile)
    mysql.create_table(MASTERalign, drop=True, **MYSQL_ALIGN)
    mysql.lock([MASTERalign])
    mysql.add_row(MASTERalign, *rows)
    mysql.unlock()

def MASTERtable(master, name):
    return master.upper() + name

######################################################################

MYSQL_CLASS = {'columns': [("tid", str, "", "NOT NULL"),
                           ("class", str, "", "NOT NULL"),
                           ("classtype", str, "", "NOT NULL"),
                           ("freq", int, None, "")],
               'primary': "tid class",
               'keys': ["classtype",
                        "class tid"],
               'engine': "MyISAM",
               'default charset': 'latin1',
               }

def MYSQL_CLASS_ROW(corpus, **kwargs):
    default = {'tid': corpus,
               'class': "okategoriserad text",
               'classtype': "okategoriserad text",
               'freq': None,
               }
    return dict(default, **kwargs)

MYSQL_ALIGN = {'columns': [("source", str, "", ""),
                           ("target", str, "", ""),
                           ("lang", str, "", "")],
               'keys': ["source", "target", "lang"],
               'engine': "MyISAM",
               }

MYSQL_TEXT = {'columns': [("tid", str, "", "NOT NULL"),
                          ("title", str, "", ""),
                          ("wordcount", int, 0, ""),
                          ("publisher", str, "", ""),
                          ("pubdate", "year", None, ""),
                          ("pubplace", str, "", ""),
                          ("translation", str, None, ""),
                          ("lang", str, None, ""),
                          ("origlang", str, None, ""),
                          ("tagger", str, None, ""),
                          ("langvariety", str, None, ""),
                          ("author", str, None, ""),
                          ("translator", str, None, ""),
                          ("classcode", str, None, ""),
                          ("istrans", str, None, ""),
                          ("startpos", int, None, ""),
                          ("endpos", int, None, "")],
              'primary': "tid",
              'keys': ["title",
                       "publisher",
                       "pubdate",
                       "pubplace"],
              'engine': "MyISAM",
              'default charset': "utf8",
              }

def MYSQL_TEXT_ROW(corpus, **kwargs):
    default = {'tid': corpus,
               'title': None,
               'wordcount': None,
               'publisher': None,
               'pubdate': None,
               'pubplace': None,
               'translation': None,
               'lang': 'swe',
               'origlang': 'swe',
               'tagger': None,
               'langvariety': None,
               'author': None,
               'translator': None,
               'classcode': 'tidningstext',
               'istrans': None,
               'startpos': 0,
               'endpos': 0,
               }
    return dict(default, **kwargs)


######################################################################

if __name__ == '__main__':
    util.run.main(create_files=create_files,
                  create_mysql=create_mysql,
                  create_align=create_align)

