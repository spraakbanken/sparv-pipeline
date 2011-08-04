# -*- coding: utf-8 -*-

import util
from util.mysql_wrapper import MySQL
import re, math

def relations(out, word, pos, lemgram, dephead, deprel, sentence, sentence_id, ref, baseform, encoding=util.UTF8):
    """ Finds every dependency between words. """

    SENTID = util.read_annotation(sentence_id)
    sentences = [(SENTID[key], sent.split()) for key, sent in util.read_annotation_iteritems(sentence)]
    #sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    WORD = util.read_annotation(word)
    POS = util.read_annotation(pos)
    LEM = util.read_annotation(lemgram)
    DEPHEAD = util.read_annotation(dephead)
    DEPREL = util.read_annotation(deprel)
    REF = util.read_annotation(ref)
    BF = util.read_annotation(baseform)
    
    # http://stp.ling.uu.se/~nivre/swedish_treebank/dep.html
    rels = [
            ({1: "VB", 2: "SS", 3: "NN"}, {1: "VB", 4: "VG", 5: "VB"}, (5, 2, 3, "")), # "han har sprungit"
            ({1: "VB", 2: "(SS|OO|IO|OA)", 3: "(VB|NN|JJ)"},),
            ({1: "VB", 2: "(RA|TA)", 3: "(AB|NN)"},),
            ({1: "VB", 2: "(RA|TA)", 3: "PP"}, {3: "PP", 4: "(PA|HD)", 5: "NN"}, (1, 2, 5, "%(3)s")),    # "ges vid behov"
            ({1: "NN", 2: "(AT|ET)", 3: "JJ"},), # "stor hund"
            ({1: "NN", 2: "ET", 3: "VB"}, {3: "VB", 4: "SS", 5: "HP"}, (1, 2, 3, "%(5)s"))     # "brödet som bakats"
            ]
    
    triples = []
    
    for sentid, sent in sentences:
        incomplete = {} # Tokens looking for heads, with head as key
        tokens = {}   # Tokens in same sentence, with token_id as key
        
        # Link the tokens together
        for token_id in sent:
            token_pos = POS[token_id]
            token_lem = LEM[token_id]
            token_dh  = DEPHEAD[token_id]
            token_dr  = DEPREL[token_id]
            token_ref = REF[token_id]
            token_bf  = BF[token_id]
            
            if token_lem == "|":
                token_lem = WORD[token_id].lower() + "_" + token_pos
            
            this = {"pos": token_pos, "lemgram": token_lem, "head": None, "dep": [], "ref": token_ref, "bf": token_bf}
            
            tokens[token_id] = this
            
            if not token_dh == "-":
                # This token is looking for a head (token is not root)
                dep_triple = (token_dr, this)
                if token_dh in tokens:
                    this["head"] = (token_dr, tokens[token_dh])
                    tokens[token_dh]["dep"].append(dep_triple)
                else:
                    incomplete.setdefault(token_dh, []).append((token_id, dep_triple))
            
            # Is someone else looking for the current token as head?
            if token_id in incomplete:
                for t in incomplete[token_id]:
                    tokens[t[0]]["head"] = this
                    this["dep"].append(t[1])
                del incomplete[token_id]
    
        assert not incomplete, "incomplete is not empty"
                
        def _match(pattern, value):
            return bool(re.match(r"^%s$" % pattern, value))
        
        def _findrel(head, rel, dep):
            result = []
            if isinstance(head, dict):
                for d in head["dep"]:
                    if _match(rel, d[0]) and _match(dep, d[1]["pos"]):
                        result.append(d[1])
            if isinstance(dep, dict):
                h = dep["head"]
                if h and _match(rel, h[0]) and _match(head, h[1]["pos"]):
                        result.append(h[1])
            return result
        
        # Look for relations
        for v in tokens.itervalues():
            for d in v["dep"]:
                for rel in rels:
                    r = rel[0]
                    if _match(";".join([x[1] for x in sorted(r.items())]), ";".join([v["pos"], d[0], d[1]["pos"]])):
                        triple = None
                        if len(rel) == 1:
                            triple = ((v["lemgram"], v["ref"]), d[0], (d[1]["lemgram"], d[1]["ref"]), ("", None), sentid, v["ref"], d[1]["ref"])
                        else:
                            lookup = dict( zip( map(str, sorted(r.keys())), (v, d[0], d[1]) ) )
                            i = set(rel[0].keys()).intersection(set(rel[1].keys())).pop()
                            rel2 = [x[1] for x in sorted(rel[1].items())]
                            index1 = rel[0].keys().index(i)
                            index2 = rel[1].keys().index(i)
                            if index1 == 2 and index2 == 0:
                                result = _findrel(d[1], rel2[1], rel2[2])
                                if result:
                                    lookup.update( dict( zip( map(str, sorted(rel[1].keys())), (d[1], rel2[1], result[0])) ) )
                            elif index1 == 0 and index2 == 0:
                                result = _findrel(v, rel2[1], rel2[2])
                                if result:
                                    lookup.update( dict( zip( map(str, sorted(rel[1].keys())), (v, rel2[1], result[0])) ) )
                            
                            pp = rel[-1]
                            if len(lookup.keys()) > 3:
                                lookup_bf = dict((key, val["bf"]) for key, val in lookup.iteritems() if isinstance(val, dict))
                                lookup_ref = dict((key, val["ref"]) for key, val in lookup.iteritems() if isinstance(val, dict))
                                triple = (
                                          (lookup[str(pp[0])]["lemgram"], lookup[str(pp[0])]["ref"]),
                                          lookup[str(pp[1])],
                                          (lookup[str(pp[2])]["lemgram"], lookup[str(pp[2])]["ref"]),
                                          (pp[3] % lookup_bf, pp[3] % lookup_ref),
                                          sentid, lookup[str(pp[0])]["ref"], lookup[str(pp[2])]["ref"])
                        if triple:
                            triples.extend(_mutate_triple(triple))
                            break

    OUT = [(str(i), "\t".join((head, rel, dep, extra, sentid, refhead, refdep))) for (i, (head, rel, dep, extra, sentid, refhead, refdep)) in enumerate(triples)]
    util.write_annotation(out, OUT)


def _mutate_triple(triple):
    """ Split |head1|head2|...| REL |dep1|dep2|...| into several separate relations.
    Also remove multi-words which are in both head and dep, and remove the :nn part from words. """
    
    head, rel, dep, extra, sentid, refhead, refdep = triple
    
    triples = []
    is_lemgrams = {}
    parts = {"head": head, "dep": dep}
    
    for part, val in parts.items():
        if val[0].startswith("|") and val[0].endswith("|"):
            parts[part] = [w[:w.find(":")] if ":" in w else w for w in val[0].split("|") if w]
            is_lemgrams[part] = True
        else:
            parts[part] = [val[0]]
    
    def _remove_doubles(a, b):
        """ Remove multi-words which are in both. """
        if a in is_lemgrams and b in is_lemgrams:
            doubles = [d for d in set(parts[a]).intersection(set(parts[b])) if re.search(r"\.\.\w\wm\.", d)]
            for double in doubles:
                parts[a].remove(double)
                parts[b].remove(double)
    
    _remove_doubles("head", "dep")
    #_remove_doubles("extra", "dep")
    #_remove_doubles("head", "extra")
    
    # Remove multiword deps for words that are already in "extra"
    if extra[1] and dep[0].startswith("|") and dep[0].endswith("|"):
        dep_multi = [dm for dm in dep[0].split("|") if ":" in dm]
        for dm in dep_multi:
            w, _, r = dm.partition(":")
            if int(extra[1]) >= int(r) and int(extra[1]) <= int(dep[1]):
                try:
                    parts["dep"].remove(w)
                except:
                    pass
    
    if extra[0].startswith("|") and extra[0].endswith("|"):
        extra = [e for e in sorted([x for x in extra[0].split("|") if x], key=len)]
        extra = extra[0] if extra else ""
    else:
        extra = extra[0]
    
    for new_head in parts["head"]:
        for new_dep in parts["dep"]:
            triples.append( (new_head, rel, new_dep, extra, sentid, refhead, refdep) )

    return triples


def mi_lex(rel, x_rel_y, x_rel, rel_y):
    """ Calculates "Lexicographer's mutual information".
     - rel is the frequency of (rel)
     - x_rel_y is the frequency of (head, rel, dep)
     - x_rel is the frequency of (head, rel)
     - rel_y is the frequency of (rel, dep)
    """
    return x_rel_y * math.log((rel * x_rel_y) / (x_rel * rel_y * 1.0), 2)


def frequency(source, corpus, db_name, sqlfile):
    """Calculates statistics of the dependencies and saves to an SQL file.
       - source is a space separated string with relations-files.
       - corpus is the corpus name.
       - db_name is the name of the database.
       - sqlfile is the path and filename for the SQL file to be created.
         Resulting file might be split into several parts if too big.
    """
    
    # Relations that will be grouped together
    rel_grouping = {
        "OO": "OBJ",
        "IO": "OBJ",
        "RA": "ADV",
        "TA": "ADV",
        "OA": "ADV"
    }
    
    MAX_SQL_LINES = 50000
    source = source.split()
    corpus = corpus.upper()
    
    freq = {} # Frequency of (head, rel, dep, depextra)
    rel_count = {} # Frequency of (rel)
    head_rel_count = {} # Frequency of (head, rel)
    rel_dep_count = {} # Frequency of (rel, dep)
    
    for s in source:
        REL = util.read_annotation(s)

        for _, triple in REL.iteritems():
            head, rel, dep, extra, sid, refh, refd = triple.split(u"\t")
            rel = rel_grouping.get(rel, rel)
            freq.setdefault(head, {}).setdefault(rel, {}).setdefault(dep, {}).setdefault(extra, [0, []])
            freq[head][rel][dep][extra][0] += 1 # Frequency
            freq[head][rel][dep][extra][1].append(sid + ":" + refh + ":" + refd) # Sentence ID and "ref" for both head and dep
            
            rel_count.setdefault(rel, 0)
            rel_count[rel] += 1
            head_rel_count.setdefault((head, rel), 0)
            head_rel_count[(head, rel)] += 1
            rel_dep_count.setdefault((rel, dep, extra), 0)
            rel_dep_count[(rel, dep, extra)] += 1

    util.log.info("Creating SQL files")
    
    no = 1
    sqlfile_no = sqlfile + "." + "%03d" % no
    mysql = MySQL(db_name, encoding=util.UTF8, output=sqlfile_no)
    mysql.create_table(MYSQL_TABLE, drop=False, **MYSQL_RELATIONS)
    #mysql.lock(MYSQL_TABLE)
    mysql.set_names()
    mysql.delete_rows(MYSQL_TABLE, {"corpus": corpus})
    
    i = 0
    rows = []
    for head, rels in freq.iteritems():
        for rel, deps in rels.iteritems():
            for dep, extras in deps.iteritems():
                for extra, extra2 in extras.iteritems():
                    count, sids = extra2
                    sids = ";".join(sids)
                    
                    #mi = mi_lex(rel_count[rel], count, head_rel_count[(head, rel)], rel_dep_count[(rel, dep, extra)])
                    
                    row = {"head": head,
                           "rel": rel,
                           "dep": dep,
                           "depextra": extra,
                           "freq": count,
                           "freq_rel": rel_count[rel],
                           "freq_head_rel": head_rel_count[(head, rel)],
                           "freq_rel_dep": rel_dep_count[(rel, dep, extra)],
                           "corpus": corpus,
                           "sentences": sids
                           }
                    rows.append(row)
                    i += 1
                    if i > MAX_SQL_LINES:
                        mysql.add_row(MYSQL_TABLE, *rows)
                        rows = []
                        # To not create too large SQL-files.
                        i = 0
                        util.log.info("%s saved", sqlfile_no)
                        no += 1
                        sqlfile_no = sqlfile + "." + "%03d" % no
                        mysql = MySQL(db_name, encoding=util.UTF8, output=sqlfile_no)
                        mysql.set_names()
    if rows:
        mysql.add_row(MYSQL_TABLE, *rows)
    
    util.log.info("Done creating SQL files")
    

################################################################################

#POS_FILTER = (u"VB", u"NN", u"JJ")
#REL_FILTER = (u"SS", u"OO", u"IO", u"AT", u"ET", u"DT", u"OA", u"RA", u"TA")

REL_SEPARATOR = " "
MYSQL_TABLE = "relations"

MYSQL_RELATIONS = {'columns': [("head",   "varchar(1024)", "", "NOT NULL"),
                               ("rel",    "char(3)", "", "NOT NULL"),
                               ("dep",    "varchar(1024)", "", "NOT NULL"),
                               ("depextra",    "varchar(1024)", "", ""),
                               ("freq",   int, None, ""),
                               ("freq_rel", int, None, ""),
                               ("freq_head_rel", int, None, ""),
                               ("freq_rel_dep", int, None, ""),
                               ("corpus", str, "", "NOT NULL"),
                               ("sentences", "TEXT", "", "")],
               'indexes': ["head",
                           "dep",
                           "corpus"],
               'default charset': 'utf8',
               }

################################################################################    

if __name__ == '__main__':
    util.run.main(relations, frequency=frequency)
