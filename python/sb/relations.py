# -*- coding: utf-8 -*-

import util
from util.mysql_wrapper import MySQL
import re

def relations(out, word, pos, lemgram, dephead, deprel, sentence, encoding=util.UTF8):
    """ Finds every dependency between words. """

    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    WORD = util.read_annotation(word)
    POS = util.read_annotation(pos)
    LEM = util.read_annotation(lemgram)
    DEPHEAD = util.read_annotation(dephead)
    DEPREL = util.read_annotation(deprel)
    
    triples = []
    
    for sent in sentences:
        root = None
        incomplete = {} # Tokens looking for heads, with head as key
        previous = {}   # Previous tokens in same sentence, with token_id as key
        
        for token_id in sent:
            token_pos = POS[token_id]
            token_lem = LEM[token_id]
            token_dh  = DEPHEAD[token_id]
            token_dr  = DEPREL[token_id]
            
            if token_lem == "|":
                token_lem = WORD[token_id].lower() + "_" + token_pos
            
            this_dep = [(token_lem, token_pos), []]
            previous[token_id] = this_dep
            
            if token_dh == "-":
                root = this_dep
            else:
                # This token is looking for a head (token is not root)
                triple = (token_dr, this_dep)
                if token_dh in previous:
                    previous[token_dh][1].append((token_dr, this_dep))
                else:
                    incomplete.setdefault(token_dh, []).append(triple)
            
            # Is someone else looking for the current token as head?
            if token_id in incomplete:
                for t in incomplete[token_id]:
                    previous[token_id][1].append((t[0], t[1]))
                del incomplete[token_id]
    
        assert not incomplete, "incomplete is not empty"
        result = _traverse_relations(root)
        
        if result:
            for r in result:
                triples.extend(_mutate_triple((r[0][0], r[1], [x[0] for x in r[2::2]])))
    
    OUT = [(str(i), "\t".join((head, rel, REL_SEPARATOR.join(dep)))) for (i, (head, rel, dep)) in enumerate(triples)]
    util.write_annotation(out, OUT)


def _traverse_relations(root, rels=[], r=None):
    # http://stp.ling.uu.se/~nivre/swedish_treebank/dep.html
    _pos = "(VB|NN|JJ)"
    baserels = [
                ["VB", "(SS|OO|IO|OA)", _pos],
                ["VB", "(RA|TA)", "(AB|NN)"],
                #["VB", "(RA|TA)", "PP", "(PA|HD)", "NN"],
                ["NN", "(AT|ET)", _pos],
                [_pos, "AT", "JJ"]
                ]

    head, deps = root
    
    def match(pattern, value):
        return True or (pattern == value or pattern == "*")
    
    if not deps: # Leaf
        return head if [rel for rel in rels if len(rel) == 1 and match(rel[0], head[1])] else None
    else:
        depres = []
        
        for deproot in deps:
            newrels = [rel[2:] for rel in rels + baserels if len(rel) > 2 and match(rel[0], head[1]) and match(rel[1], deproot[0])]
            dep = _traverse_relations(deproot[1], newrels, deproot[0])

            if isinstance(dep, list):
                depres.extend([x for x in dep if len(x) > 2])
                for l in dep:
                    if len(l) > 2 and len(l[2]) > 2:
                        if len(l) > 3:
                            assert False, "This should not happen"
                        temp = list(l[:2])
                        for ll in l[2]:
                            temp.append(ll)
                        l = temp
                    depres.append([head, deproot[0]] + l)
            elif dep: # Leaf
                depres.append([head, deproot[0], dep])
        
        result = []
        matchpattern = "^" + "$|^".join([";".join(x).replace("*", "[^;]+") for x in rels + baserels]) + "$"

        for d in depres:
            pattern = ";".join([x if isinstance(x, basestring) else x[1] for x in d])
            if re.match(matchpattern, pattern):
                result.append(d)
        
        if [rel for rel in rels if len(rel) == 1 and match(rel[0], head[1])]:
            result.append([head])
        
        return result


def _mutate_triple(triple):
    """ Split |head1|head2|...| REL |dep1|dep2|...| into several separate relations.
    Also remove multi-words which are in both head and dep, and remove the :nn part from words. """
    head, rel, _dep = triple
    
    extra = _dep[:-1][0] if _dep[:-1] else ""
    dep = _dep[-1]
    
    triples = []
    is_lemgrams = {}
    parts = {"head": head, "extra": extra, "dep": dep}
    
    for part, val in parts.items():
        if val.startswith("|") and val.endswith("|"):
            parts[part] = [w[:w.find(":")] if ":" in w else w for w in val.split("|") if w]
            is_lemgrams[part] = True
        else:
            parts[part] = [val]
    
    def _remove_doubles(a, b):
        if a in is_lemgrams and b in is_lemgrams:
            # Remove multi-words which are in both
            doubles = [d for d in set(parts[a]).intersection(set(parts[b])) if re.search(r"\.\.\w\wm\.", d)]
        
            for double in doubles:
                parts[a].remove(double)
                parts[b].remove(double)
    
    _remove_doubles("head", "dep")
    _remove_doubles("extra", "dep")
    _remove_doubles("head", "extra")
    
    extras = "|".join(e for e in parts["extra"]) if parts["extra"] else ""
    extras = extras or []
    
    for new_head in parts["head"]:
        for new_dep in parts["dep"]:
            triples.append( (new_head, rel, extras + [new_dep]) )

    return triples


def frequency(source, corpus, db_name, sqlfile):
    """ Calculates statistics of the dependencies and saves to an SQL file. """
    
    min_count = 1
    source = source.split()
    
    freq = {}
    
    for s in source:
        REL = util.read_annotation(s)

        for _, triple in REL.iteritems():
            head, rel, w = triple.split(u"\t")
            #print "%50s %5s   %-50s" % (head, rel, w)
            freq.setdefault(head, {}).setdefault(rel, {}).setdefault(w, 0)
            freq[head][rel][w] += 1
    
    util.log.info("Creating SQL files")
    
    no = 1
    sqlfile_no = sqlfile + "." + "%03d" % no
    mysql = MySQL(db_name, encoding=util.UTF8, output=sqlfile_no)
    mysql.create_table(MYSQL_TABLE, drop=False, **MYSQL_RELATIONS)
    mysql.lock(MYSQL_TABLE)
    mysql.delete_rows(MYSQL_TABLE, {"corpus": corpus.upper()})
    
    i = 0
    for head, rels in freq.iteritems():
        for rel, w in rels.iteritems():
            for w, count in sorted(w.iteritems(), key=lambda x: -x[1]):
                #w_split = w.split(REL_SEPARATOR)
                
                if count >= min_count:
                    row = {"head": head,
                           "rel": rel,
                           "dep": w,
                           "freq": count,
                           "corpus": corpus.upper()
                           }
                    mysql.add_row(MYSQL_TABLE, row)
                    i += 1
                    if i > 50000:
                        # To not create too large SQL-files.
                        i = 0
                        mysql.unlock()
                        no += 1
                        sqlfile_no = sqlfile + "." + "%03d" % no
                        mysql = MySQL(db_name, encoding=util.UTF8, output=sqlfile_no)
                        mysql.lock(MYSQL_TABLE)
    mysql.unlock()
    
    util.log.info("Done creating SQL files")
    

################################################################################

POS_FILTER = (u"VB", u"NN", u"JJ")
REL_FILTER = (u"SS", u"OO", u"IO", u"AT", u"ET", u"DT", u"OA", u"RA", u"TA")

REL_SEPARATOR = " "
MYSQL_TABLE = "relations"

MYSQL_RELATIONS = {'columns': [("head",   "varchar(1024)", "", "NOT NULL"),
                               ("rel",    "char(2)", "", "NOT NULL"),
                               ("dep",    "varchar(1024)", "", "NOT NULL"),
                               ("freq",   int, None, ""),
                               ("corpus", str, "", "NOT NULL")],
               'indexes': ["head",
                           "dep",
                           "corpus",
                           "rel"],
               'default charset': 'utf8',
               }

################################################################################    

if __name__ == '__main__':
    util.run.main(relations, frequency=frequency)
