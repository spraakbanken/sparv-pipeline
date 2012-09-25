# -*- coding: utf-8 -*-

import util
from collections import defaultdict
from util.mysql_wrapper import MySQL
import re, math

def relations(out, word, pos, lemgram, dephead, deprel, sentence, sentence_id, ref, baseform, encoding=util.UTF8):
    """ Finds every dependency between words. """

    SENTID = util.read_annotation(sentence_id)
    sentences = [(SENTID[key], sent.split()) for key, sent in util.read_annotation_iteritems(sentence) if key]
    #sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    WORD = util.read_annotation(word)
    POS = util.read_annotation(pos)
    LEM = util.read_annotation(lemgram)
    DEPHEAD = util.read_annotation(dephead)
    DEPREL = util.read_annotation(deprel)
    REF = util.read_annotation(ref)
    BF = util.read_annotation(baseform) # Used for "depextra"
    
    # http://stp.ling.uu.se/~nivre/swedish_treebank/dep.html
    # Tuples with relations (head, dep, rel) to be found (with indexes) and an optional tuple specifying which info should be stored and how
    rels = [
            ({1: "VB", 2: "SS", 3: "NN"}, {1: "VB", 4: "VG", 5: "VB"}, (5, 2, 3, "")), # "han har sprungit"
            ({1: "VB", 2: "(SS|OO|IO|OA)", 3: "NN"},),
            ({1: "VB", 2: "(RA|TA)", 3: "(AB|NN)"},),
            ({1: "VB", 2: "(RA|TA)", 3: "PP"}, {3: "PP", 4: "(PA|HD)", 5: "NN"}, (1, 2, 5, "%(3)s")),    # "ges vid behov"
            ({1: "NN", 2: "(AT|ET)", 3: "JJ"},), # "stor hund"
            ({1: "NN", 2: "ET", 3: "VB"}, {3: "VB", 4: "SS", 5: "HP"}, (1, 2, 3, "%(5)s")),     # "brödet som bakats"
            ({1: "NN", 2: "ET", 3: "PP"}, {3: "PP", 4: "PA", 5: "(PM|NN)"}, (1, 2, 5, "%(3)s")),     # "barnen i skolan", "hundarna i Sverige"
            ({1: "PP", 2: "PA", 3: "NN"},) # "på bordet"
            ]

    null_rels = [
                 ("VB", ["OO"]), # Verb som saknar objekt
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
            token_word = WORD[token_id].lower() + "_" + token_pos

            if token_lem == "|":
                token_lem = token_word
            
            this = {"pos": token_pos, "lemgram": token_lem, "word": token_word, "head": None, "dep": [], "ref": token_ref, "bf": token_bf}
            
            tokens[token_id] = this
            
            if not token_dh == "-":
                # This token is looking for a head (token is not root)
                dep_triple = (token_dr, this)
                if token_dh in tokens:
                    # Found head. Link them together both ways
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
                            triple = ((v["lemgram"], v["word"], v["ref"]), d[0], (d[1]["lemgram"], d[1]["word"], d[1]["ref"]), ("", None), sentid, v["ref"], d[1]["ref"])
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
                                          (lookup[str(pp[0])]["lemgram"], lookup[str(pp[0])]["word"], lookup[str(pp[0])]["ref"]),
                                          lookup[str(pp[1])],
                                          (lookup[str(pp[2])]["lemgram"], lookup[str(pp[2])]["word"], lookup[str(pp[2])]["ref"]),
                                          (pp[3] % lookup_bf, pp[3] % lookup_ref),
                                          sentid, lookup[str(pp[0])]["ref"], lookup[str(pp[2])]["ref"])
                        if triple:
                            triples.extend(_mutate_triple(triple))
                            break
            token_rels = [d[0] for d in v["dep"]]
            for nrel in null_rels:
                if nrel[0] == v["pos"]:
                    missing_rels = [x for x in nrel[1] if x not in token_rels]
                    for mrel in missing_rels:
                        triple = ((v["lemgram"], v["word"], v["ref"]), mrel, ("", "", v["ref"]), ("", None), sentid, v["ref"], v["ref"])
                        triples.extend(_mutate_triple(triple))

    triples = set(triples)

    OUT = [(str(i), "\t".join((head, rel, dep, extra, sentid, refhead, refdep, wf))) for (i, (head, rel, dep, extra, sentid, refhead, refdep, wf)) in enumerate(triples)]
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
            if int(extra[1]) >= int(r) and int(extra[1]) <= int(dep[2]):
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
            triples.append( (new_head, rel, new_dep, extra, sentid, refhead, refdep, "") )
            # For words not in SALDO, wf has the same value, so no need to add them
            #if not head[1] == new_head:
            triples.append( (head[1], rel, new_dep, extra, sentid, refhead, refdep, "1") )
            #if not dep[1] == new_dep:
            triples.append( (new_head, rel, dep[1], extra, sentid, refhead, refdep, "2") )

    return triples


def mi_lex(rel, x_rel_y, x_rel, rel_y):
    """ Calculates "Lexicographer's mutual information".
     - rel is the frequency of (rel)
     - x_rel_y is the frequency of (head, rel, dep)
     - x_rel is the frequency of (head, rel)
     - rel_y is the frequency of (rel, dep)
    """
    return x_rel_y * math.log((rel * x_rel_y) / (x_rel * rel_y * 1.0), 2)


def frequency(source, corpus, db_name, table_file, table_file2, combined=True):
    """Calculates statistics of the dependencies and saves to SQL files.
       - source is a space separated string with relations-files.
       - corpus is the corpus name.
       - db_name is the name of the database.
       - table_file is the filename for the SQL file which will contain the table creation SQL.
       - combined set to true leads to all the SQL commands being saved to one single file. This might not work for too large amounts of data.
    """
    
    combined = False if combined == "" or (isinstance(combined, str) and combined.lower() == "false") else True
    
    db_table = MYSQL_TABLE + "_" + corpus.upper()
    
    # Relations that will be grouped together
    rel_grouping = {
        "OO": "OBJ",
        "IO": "OBJ",
        "RA": "ADV",
        "TA": "ADV",
        "OA": "ADV"
    }
    
    MAX_SENTENCES = 5000
    
    index = 0
    freq_index = {}
    sentence_count = defaultdict(int)
    first_file = True
    file_count = 0
    source_files = source.split()
    
    for s in source_files:
        file_count += 1
        if first_file or not combined:
            freq = {} # Frequency of (head, rel, dep, depextra)
            rel_count = defaultdict(int) # Frequency of (rel)
            head_rel_count = defaultdict(int) # Frequency of (head, rel)
            dep_rel_count = defaultdict(int) # Frequency of (rel, dep)
        
        REL = util.read_annotation(s)
        basename = s.rsplit(".", 1)[0]

        for _, triple in REL.iteritems():
            head, rel, dep, extra, sid, refh, refd, wf = triple.split(u"\t")
            rel = rel_grouping.get(rel, rel)
            
            if (head, rel, dep, extra) in freq_index:
                this_index = freq_index[(head, rel, dep, extra)]
            else:
                this_index = index
                freq_index[(head, rel, dep, extra)] = this_index
                index += 1
            
            freq.setdefault(head, {}).setdefault(rel, {}).setdefault(dep, {}).setdefault(extra, [this_index, 0, set(), 0])
            freq[head][rel][dep][extra][1] += 1 # Frequency
            
            if sentence_count[this_index] < MAX_SENTENCES:
                freq[head][rel][dep][extra][2].add((sid, refh, refd)) # Sentence ID and "ref" for both head and dep
                sentence_count[this_index] += 1
            freq[head][rel][dep][extra][3] += int(wf) if wf else 0
            
            if not wf:
                rel_count[rel] += 1
            if not wf or wf == "1":
                head_rel_count[(head, rel)] += 1
            if not wf or wf == "2":
                dep_rel_count[(dep, extra, rel)] += 1

        if not combined:
            write_sql(freq, rel_count, head_rel_count, dep_rel_count, table_file, basename + ".sql", db_name, db_table, combined, first=first_file)
            first_file = False
        elif not file_count == len(source_files):
            write_sql({}, {}, {}, {}, table_file, basename + ".sql", db_name, db_table, combined, first=first_file)
            first_file = False
    
    if combined:
        write_sql(freq, rel_count, head_rel_count, dep_rel_count, table_file, basename + ".sql", db_name, db_table, combined, first=first_file)
    
    mysql = MySQL(db_name, encoding=util.UTF8, output=table_file2)
    mysql.enable_keys(db_table, db_table + "_rel", db_table + "_head_rel", db_table + "_dep_rel", db_table + "_sentences")
    
    util.log.info("Done creating SQL files")
    

def write_sql(freq, rel_count, head_rel_count, dep_rel_count, table_file, sqlfile, db_name, db_table, combined=False, first=False):
    
    update_freq_wf = "ON DUPLICATE KEY UPDATE freq = freq + VALUES(freq), wf = wf + VALUES(wf)" if not combined else ""
    update_freq = "ON DUPLICATE KEY UPDATE freq = freq + VALUES(freq)" if not combined else ""
    
    if first:
        if combined:
            del MYSQL_RELATIONS["constraints"]
            del MYSQL_REL["constraints"]
            del MYSQL_HEAD_REL["constraints"]
            del MYSQL_DEP_REL["constraints"]
        mysql = MySQL(db_name, encoding=util.UTF8, output=table_file)
        mysql.create_table(db_table, drop=True, **MYSQL_RELATIONS)
        mysql.create_table(db_table + "_rel", drop=True, **MYSQL_REL)
        mysql.create_table(db_table + "_head_rel", drop=True, **MYSQL_HEAD_REL)
        mysql.create_table(db_table + "_dep_rel", drop=True, **MYSQL_DEP_REL)
        mysql.create_table(db_table + "_sentences", drop=True, **MYSQL_SENTENCES)
        mysql.disable_keys(db_table, db_table + "_rel", db_table + "_head_rel", db_table + "_dep_rel", db_table + "_sentences")
    
    mysql = MySQL(db_name, encoding=util.UTF8, output=sqlfile)
    if freq:
        mysql.set_names()
    
    sentence_rows = []
    rows = []
    for head, rels in freq.iteritems():
        for rel, deps in rels.iteritems():
            for dep, extras in deps.iteritems():
                for extra, extra2 in extras.iteritems():
                    index, count, sids, wf = extra2
                    for sid in sids:
                        srow = {
                               "id": index,
                               "sentence": sid[0],
                               "start": sid[1],
                               "end": sid[2]
                               }
                        sentence_rows.append(srow)
                    
                    row = {
                           "id": index,
                           "head": head,
                           "rel": rel,
                           "dep": dep,
                           "depextra": extra,
                           "freq": count,
                           "wf": wf
                           }
                    rows.append(row)

    mysql.add_row(db_table, rows, update_freq_wf)
    
    rows = []
    for rel, freq in rel_count.iteritems():
        row = {
               "rel": rel,
               "freq": freq}
        rows.append(row)
    
    mysql.add_row(db_table + "_rel", rows, update_freq)

    rows = []
    for head_rel, freq in head_rel_count.iteritems():
        head, rel = head_rel
        row = {
               "head": head,
               "rel": rel,
               "freq": freq}
        rows.append(row)
    
    mysql.add_row(db_table + "_head_rel", rows, update_freq)

    rows = []
    for dep_extra_rel, freq in dep_rel_count.iteritems():
        dep, extra, rel = dep_extra_rel
        row = {
               "dep": dep,
               "depextra": extra,
               "rel": rel,
               "freq": freq}
        rows.append(row)
    
    mysql.add_row(db_table + "_dep_rel", rows, update_freq)
    

    
    mysql.add_row(db_table + "_sentences", sentence_rows)
    
    util.log.info("%s written", sqlfile)
    
################################################################################

MYSQL_TABLE = "relations"

MYSQL_RELATIONS = {'columns': [
                               ("id",     int, None, ""),
                               ("head",   "varchar(100)", "", "NOT NULL"),
                               ("rel",    "char(3)", "", "NOT NULL"),
                               ("dep",    "varchar(100)", "", "NOT NULL"),
                               ("depextra",    "varchar(32)", "", ""),
                               ("freq",   int, None, ""),
                               ("wf", "TINYINT", None, "")],
               'indexes': ["head",
                           "dep"
                           ],
               'constraints': [("UNIQUE INDEX", "relation", ("head", "rel", "dep", "depextra"))],
               'default charset': 'utf8',
               #'collate': 'utf8_bin'
               }

MYSQL_REL = {'columns': [
                          ("rel",    "char(3)", "", "NOT NULL"),
                          ("freq", int, None, "")],
               'indexes': ["rel"],
               'constraints': [("UNIQUE INDEX", "relation", ("rel",))],
               'default charset': 'utf8',
               'collate': 'utf8_bin'
               }

MYSQL_HEAD_REL = {'columns': [
                              ("head",   "varchar(100)", "", "NOT NULL"),
                              ("rel",    "char(3)", "", "NOT NULL"),
                              ("freq", int, None, "")],
                  'indexes': ["head",
                              "rel"],
                  'constraints': [("UNIQUE INDEX", "relation", ("head", "rel"))],
                  'default charset': 'utf8',
                  'collate': 'utf8_bin'
                   }

MYSQL_DEP_REL = {'columns': [
                              ("dep",   "varchar(100)", "", "NOT NULL"),
                              ("depextra",    "varchar(32)", "", ""),
                              ("rel",    "char(3)", "", "NOT NULL"),
                              ("freq", int, None, "")],
                 'indexes': ["dep",
                           "rel"],
                 'constraints': [("UNIQUE INDEX", "relation", ("dep", "depextra", "rel"))],
                 'default charset': 'utf8',
                 'collate': 'utf8_bin'
                 }

MYSQL_SENTENCES = {'columns': [
                               ("id", int, None, ""),
                               ("sentence",   "varchar(64)", "", "NOT NULL"),
                               ("start",    int, None, ""),
                               ("end", int, None, "")],
               'indexes': ["id"],
               'default charset': 'utf8',
               'collate': 'utf8_bin'
               }
################################################################################    

if __name__ == '__main__':
    util.run.main(relations, frequency=frequency)
