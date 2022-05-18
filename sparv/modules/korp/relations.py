"""Create files needed for the word picture in Korp."""

import math
import re
from collections import defaultdict
from typing import Optional

from sparv.api import (AllSourceFilenames, Annotation, AnnotationDataAllSourceFiles, Config, Corpus, Export, ExportInput,
                       OutputCommonData, OutputData, annotator, exporter, get_logger, installer, util)
from sparv.api.util.mysql_wrapper import MySQL

logger = get_logger(__name__)


MAX_STRING_LENGTH = 100
MAX_STRINGEXTRA_LENGTH = 32
MAX_POS_LENGTH = 5


@installer("Install Korp's Word Picture SQL on remote host", language=["swe"])
def install_relations(sqlfile: ExportInput = ExportInput("korp.wordpicture/relations.sql"),
                      out: OutputCommonData = OutputCommonData("korp.install_relations_marker"),
                      db_name: str = Config("korp.mysql_dbname"),
                      host: str = Config("korp.remote_host")):
    """Install Korp's Word Picture SQL on remote host.

    Args:
        sqlfile (str, optional): SQL file to be installed. Defaults to ExportInput("korp.wordpicture/relations.sql").
        out (str, optional): Marker file to be written.
        db_name (str, optional): Name of the data base. Defaults to Config("korp.mysql_dbname").
        host (str, optional): Remote host to install to. Defaults to Config("korp.remote_host").
    """
    util.install.install_mysql(host, db_name, sqlfile)
    out.write("")


@annotator("Find dependencies for Korp's Word Picture", language=["swe"])
def relations(out: OutputData = OutputData("korp.relations"),
              word: Annotation = Annotation("<token:word>"),
              pos: Annotation = Annotation("<token:pos>"),
              lemgram: Annotation = Annotation("<token>:saldo.lemgram"),
              dephead: Annotation = Annotation("<token:dephead>"),
              deprel: Annotation = Annotation("<token:deprel>"),
              sentence_id: Annotation = Annotation("<sentence>:misc.id"),
              ref: Annotation = Annotation("<token:ref>"),
              baseform: Annotation = Annotation("<token>:saldo.baseform")):
    """Find certain dependencies between words, to be used by the Word Picture feature in Korp."""
    sentence_ids = sentence_id.read()
    sentence_tokens, _ = sentence_id.get_children(word)

    logger.progress(total=len(sentence_tokens) + 1)

    annotations = list(word.read_attributes((word, pos, lemgram, dephead, deprel, ref, baseform)))

    # http://stp.ling.uu.se/~nivre/swedish_treebank/dep.html
    # Tuples with relations (head, rel, dep) to be found (with indexes) and an optional tuple specifying which info
    # should be stored and how
    rels = [
        ({1: "VB", 2: "SS", 3: "NN"}, {1: "VB", 4: "VG", 5: "VB"}, (5, 2, 3, "")),  # "han har sprungit"
        ({1: "VB", 2: "(SS|OO|IO|OA)", 3: "NN"},),
        ({1: "VB", 2: "(RA|TA)", 3: "(AB|NN)"},),
        ({1: "VB", 2: "(RA|TA)", 3: "PP"}, {3: "PP", 4: "(PA|HD)", 5: "NN"}, (1, 2, 5, "%(3)s")),  # "ges vid behov"
        ({1: "NN", 2: "(AT|ET)", 3: "JJ"},),  # "stor hund"
        ({1: "NN", 2: "ET", 3: "VB"}, {3: "VB", 4: "SS", 5: "HP"}, (1, 2, 3, "%(5)s")),     # "brödet som bakats"
        ({1: "NN", 2: "ET", 3: "PP"}, {3: "PP", 4: "PA", 5: "(NN|PM)"}, (1, 2, 5, "%(3)s")),  # "barnen i skolan", "hundarna i Sverige"
        ({1: "PP", 2: "PA", 3: "NN"},),  # "på bordet"
        ({1: "JJ", 2: "AA", 3: "AB"},)  # "fullständigt galen"
    ]

    null_rels = [
        ("VB", ["OO"]),  # Verb som saknar objekt
    ]

    triples = []

    for sentid, sent in zip(sentence_ids, sentence_tokens):
        incomplete = {}  # Tokens looking for heads, with head as key
        tokens = {}   # Tokens in same sentence, with token_index as key
        skip_sentence = False

        # Link the tokens together
        for token_index in sent:
            token_word, token_pos, token_lem, token_dh, token_dr, token_ref, token_bf = annotations[token_index]
            if not token_dr:
                skip_sentence = True
                break
            token_word = token_word.lower()

            if token_lem == "|":
                token_lem = token_word

            this = {"pos": token_pos, "lemgram": token_lem, "word": token_word, "head": None, "dep": [],
                    "ref": token_ref, "bf": token_bf}

            tokens[token_index] = this

            if not token_dh == "-":
                token_dh = int(token_dh)
                # This token is looking for a head (token is not root)
                dep_triple = (token_dr, this)
                if token_dh in tokens:
                    # Found head. Link them together both ways
                    this["head"] = (token_dr, tokens[token_dh])
                    tokens[token_dh]["dep"].append(dep_triple)
                else:
                    incomplete.setdefault(token_dh, []).append((token_index, dep_triple))

            # Is someone else looking for the current token as head?
            if token_index in incomplete:
                for t in incomplete[token_index]:
                    tokens[t[0]]["head"] = this
                    this["dep"].append(t[1])
                del incomplete[token_index]

        if skip_sentence:
            continue

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
        for v in list(tokens.values()):
            for d in v["dep"]:
                for rel in rels:
                    r = rel[0]
                    if _match(";".join([x[1] for x in sorted(r.items())]), ";".join([v["pos"], d[0], d[1]["pos"]])):
                        triple = None
                        if len(rel) == 1:
                            triple = ((v["lemgram"], v["word"], v["pos"], v["ref"]), d[0],
                                      (d[1]["lemgram"], d[1]["word"], d[1]["pos"], d[1]["ref"]), ("", None), sentid,
                                      v["ref"], d[1]["ref"])
                        else:
                            lookup = dict(list(zip(list(map(str, sorted(r.keys()))), (v, d[0], d[1]))))
                            i = set(rel[0].keys()).intersection(set(rel[1].keys())).pop()
                            rel2 = [x[1] for x in sorted(rel[1].items())]
                            index1 = list(rel[0].keys()).index(i)
                            index2 = list(rel[1].keys()).index(i)
                            if index1 == 2 and index2 == 0:
                                result = _findrel(d[1], rel2[1], rel2[2])
                                if result:
                                    lookup.update(dict(
                                        list(zip(list(map(str, sorted(rel[1].keys()))), (d[1], rel2[1], result[0])))))
                            elif index1 == 0 and index2 == 0:
                                result = _findrel(v, rel2[1], rel2[2])
                                if result:
                                    lookup.update(
                                        dict(list(zip(list(map(str, sorted(rel[1].keys()))), (v, rel2[1], result[0])))))

                            pp = rel[-1]
                            if len(list(lookup.keys())) > 3:
                                lookup_bf = dict((key, val["bf"]) for key, val in list(lookup.items()) if isinstance(val, dict))
                                lookup_ref = dict((key, val["ref"]) for key, val in list(lookup.items()) if isinstance(val, dict))
                                triple = (
                                    (lookup[str(pp[0])]["lemgram"], lookup[str(pp[0])]["word"],
                                     lookup[str(pp[0])]["pos"], lookup[str(pp[0])]["ref"]),
                                    lookup[str(pp[1])],
                                    (lookup[str(pp[2])]["lemgram"], lookup[str(pp[2])]["word"],
                                     lookup[str(pp[2])]["pos"], lookup[str(pp[2])]["ref"]),
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
                        triple = (
                            (v["lemgram"], v["word"], v["pos"], v["ref"]), mrel, ("", "", "", v["ref"]), ("", None), sentid,
                            v["ref"], v["ref"])
                        triples.extend(_mutate_triple(triple))
        logger.progress()

    triples = sorted(set(triples))

    out_data = "\n".join(["\t".join((head, headpos, rel, dep, deppos, extra, sentid, refhead, refdep, str(bfhead),
                                     str(bfdep), str(wfhead), str(wfdep))) for (
                          head, headpos, rel, dep, deppos, extra, sentid, refhead, refdep, bfhead, bfdep, wfhead, wfdep)
                          in triples])
    out.write(out_data)
    logger.progress()


def _mutate_triple(triple):
    """Split |head1|head2|...| REL |dep1|dep2|...| into several separate relations.

    Also remove multi-words which are in both head and dep, and remove the :nn part from words.
    """
    head, rel, dep, extra, sentid, refhead, refdep = triple

    triples = []
    is_lemgrams = {}
    parts = {"head": head, "dep": dep}

    for part, val in list(parts.items()):
        if val[0].startswith("|") and val[0].endswith("|"):
            parts[part] = [w[:w.find(":")] if ":" in w else w for w in val[0].split("|") if w]
            is_lemgrams[part] = True
        else:
            parts[part] = [val[0]]

    def _remove_doubles(a, b):
        """Remove multi-words which are in both."""
        if a in is_lemgrams and b in is_lemgrams:
            doubles = [d for d in set(parts[a]).intersection(set(parts[b])) if re.search(r"\.\.\w\wm\.", d)]
            for double in doubles:
                parts[a].remove(double)
                parts[b].remove(double)

    _remove_doubles("head", "dep")
    # _remove_doubles("extra", "dep")
    # _remove_doubles("head", "extra")

    # Remove multiword deps for words that are already in "extra"
    if extra[1] and dep[0].startswith("|") and dep[0].endswith("|"):
        dep_multi = [dm for dm in dep[0].split("|") if ":" in dm]
        for dm in dep_multi:
            w, _, r = dm.partition(":")
            if int(r) <= int(extra[1]) <= int(dep[3]):
                try:
                    parts["dep"].remove(w)
                except Exception:
                    pass

    if extra[0].startswith("|") and extra[0].endswith("|"):
        extra = [e for e in sorted([x for x in extra[0].split("|") if x], key=len)]
        extra = extra[0] if extra else ""
    else:
        extra = extra[0]

    for new_head in parts["head"]:
        for new_dep in parts["dep"]:
            # head: lemgram, dep: lemgram
            triples.append((new_head, head[2], rel, new_dep, dep[2], extra, sentid, refhead, refdep, 1, 1, 0, 0))
            # head: wordform, dep: lemgram
            triples.append((head[1], head[2], rel, new_dep, dep[2], extra, sentid, refhead, refdep, 0, 1, 1, 0))
            # head: lemgram, dep: wordform
            triples.append((new_head, head[2], rel, dep[1], dep[2], extra, sentid, refhead, refdep, 1, 0, 0, 1))

    return triples


def mi_lex(rel, x_rel_y, x_rel, rel_y):
    """Calculate "Lexicographer's mutual information".

    - rel is the frequency of (rel)
    - x_rel_y is the frequency of (head, rel, dep)
    - x_rel is the frequency of (head, rel)
    - rel_y is the frequency of (rel, dep)
    """
    return x_rel_y * math.log((rel * x_rel_y) / (x_rel * rel_y * 1.0), 2)


@exporter("Word Picture SQL for use in Korp", language=["swe"])
def relations_sql(corpus: Corpus = Corpus(),
                  out: Export = Export("korp.wordpicture/relations.sql"),
                  relations: AnnotationDataAllSourceFiles = AnnotationDataAllSourceFiles("korp.relations"),
                  source_files: Optional[AllSourceFilenames] = AllSourceFilenames(),
                  source_files_list: str = "",
                  split: bool = False):
    """Calculate statistics of the dependencies and saves to SQL files.

    Args:
        corpus: the corpus name
        out: the name for the SQL file which will contain the resulting SQL statements
        relations: the name of the relations annotation
        source_files: a list of source filenames
        source_files_list: can be used instead of source_files, and should be a file containing the name of source
            files, one per row
        split: when set to true leads to SQL commands being split into several parts, requiring less memory during
            creation, but installing the data will take much longer
    """
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
    string_index = -1
    strings = {}  # ID -> string table
    freq_index = {}
    sentence_count = defaultdict(int)
    file_count = 0

    assert (source_files or source_files_list), "Missing source"

    if source_files_list:
        with open(source_files_list, encoding="utf-8") as insource:
            source_files = [line.strip() for line in insource]

    if len(source_files) == 1:
        split = False

    logger.progress(total=len(source_files) + 1)

    for file in source_files:
        file_count += 1
        sentences = {}
        if file_count == 1 or split:
            freq = {}                           # Frequency of (head, rel, dep)
            rel_count = defaultdict(int)        # Frequency of (rel)
            head_rel_count = defaultdict(int)   # Frequency of (head, rel)
            dep_rel_count = defaultdict(int)    # Frequency of (rel, dep)

        relations_data = relations.read(file)

        for triple in relations_data.splitlines():
            head, headpos, rel, dep, deppos, extra, sid, refh, refd, bfhead, bfdep, wfhead, wfdep = triple.split(u"\t")
            bfhead, bfdep, wfhead, wfdep = int(bfhead), int(bfdep), int(wfhead), int(wfdep)

            if not (head, headpos) in strings:
                string_index += 1
            head = strings.setdefault((head, headpos), string_index)

            if not (dep, deppos, extra) in strings:
                string_index += 1
            dep = strings.setdefault((dep, deppos, extra), string_index)

            rel = rel_grouping.get(rel, rel)

            if (head, rel, dep) in freq_index:
                this_index = freq_index[(head, rel, dep)]
            else:
                this_index = index
                freq_index[(head, rel, dep)] = this_index
                index += 1
            #                                                                         freq    bf/wf
            freq.setdefault(head, {}).setdefault(rel, {}).setdefault(dep, [this_index, 0, [0, 0, 0, 0]])
            freq[head][rel][dep][1] += 1  # Frequency

            if sentence_count[this_index] < MAX_SENTENCES:
                sentences.setdefault(this_index, set())
                sentences[this_index].add((sid, refh, refd))  # Sentence ID and "ref" for both head and dep
                sentence_count[this_index] += 1

            freq[head][rel][dep][2][0] = freq[head][rel][dep][2][0] or bfhead
            freq[head][rel][dep][2][1] = freq[head][rel][dep][2][1] or bfdep
            freq[head][rel][dep][2][2] = freq[head][rel][dep][2][2] or wfhead
            freq[head][rel][dep][2][3] = freq[head][rel][dep][2][3] or wfdep

            if bfhead and bfdep:
                rel_count[rel] += 1
            if (bfhead and bfdep) or wfhead:
                head_rel_count[(head, rel)] += 1
            if (bfhead and bfdep) or wfdep:
                dep_rel_count[(dep, rel)] += 1

        # If not the last file
        if not file_count == len(source_files):
            if split:
                # Don't print string table until the last file
                _write_sql({}, sentences, freq, rel_count, head_rel_count, dep_rel_count, out, db_table, split,
                           first=(file_count == 1))
            else:
                # Only save sentences data, save the rest for the last file
                _write_sql({}, sentences, {}, {}, {}, {}, out, db_table, split, first=(file_count == 1))

        logger.progress()

    # Create the final file, including the string table
    _write_sql(strings, sentences, freq, rel_count, head_rel_count, dep_rel_count, out, db_table, split,
               first=(file_count == 1), last=True)

    logger.progress()
    logger.info("Done creating SQL files")


def _write_sql(strings, sentences, freq, rel_count, head_rel_count, dep_rel_count, sql_file, db_table,
               split=False, first=False, last=False):

    temp_db_table = "temp_" + db_table
    update_freq = "ON DUPLICATE KEY UPDATE freq = freq + VALUES(freq)" if split else ""

    mysql = MySQL(output=sql_file, append=True)

    if first:
        if not split:
            del MYSQL_RELATIONS["constraints"]
            del MYSQL_REL["constraints"]
            del MYSQL_HEAD_REL["constraints"]
            del MYSQL_DEP_REL["constraints"]
        mysql.create_table(temp_db_table, drop=True, **MYSQL_RELATIONS)
        mysql.create_table(temp_db_table + "_strings", drop=True, **MYSQL_STRINGS)
        mysql.create_table(temp_db_table + "_rel", drop=True, **MYSQL_REL)
        mysql.create_table(temp_db_table + "_head_rel", drop=True, **MYSQL_HEAD_REL)
        mysql.create_table(temp_db_table + "_dep_rel", drop=True, **MYSQL_DEP_REL)
        mysql.create_table(temp_db_table + "_sentences", drop=True, **MYSQL_SENTENCES)
        mysql.disable_keys(temp_db_table, temp_db_table + "_strings", temp_db_table + "_rel",
                           temp_db_table + "_head_rel", temp_db_table + "_dep_rel", temp_db_table + "_sentences")
        mysql.disable_checks()
        mysql.set_names()

    rows = []

    for string, index in sorted(strings.items()):
        if len(string) == 3:
            string, pos, stringextra = string
        else:
            string, pos = string
            stringextra = ""
        row = {
            "id": index,
            "string": string[:MAX_STRING_LENGTH],
            "stringextra": stringextra[:MAX_STRINGEXTRA_LENGTH],
            "pos": pos}
        rows.append(row)

    mysql.add_row(temp_db_table + "_strings", rows, "")

    sentence_rows = []
    rows = []
    for head, rels in sorted(freq.items()):
        for rel, deps in sorted(rels.items()):
            for dep, dep2 in sorted(deps.items()):
                index, count, bfwf = dep2

                row = {
                    "id": index,
                    "head": head,
                    "rel": rel,
                    "dep": dep,
                    "freq": count,
                    "bfhead": bfwf[0],
                    "bfdep": bfwf[1],
                    "wfhead": bfwf[2],
                    "wfdep": bfwf[3]
                }
                rows.append(row)

    mysql.add_row(temp_db_table, rows, update_freq)

    rows = []
    for rel, freq in sorted(rel_count.items()):
        row = {
            "rel": rel,
            "freq": freq}
        rows.append(row)

    mysql.add_row(temp_db_table + "_rel", rows, update_freq)

    rows = []
    for head_rel, freq in sorted(head_rel_count.items()):
        head, rel = head_rel
        row = {
            "head": head,
            "rel": rel,
            "freq": freq}
        rows.append(row)

    mysql.add_row(temp_db_table + "_head_rel", rows, update_freq)

    rows = []
    for dep_rel, freq in sorted(dep_rel_count.items()):
        dep, rel = dep_rel
        row = {
            "dep": dep,
            "rel": rel,
            "freq": freq}
        rows.append(row)

    mysql.add_row(temp_db_table + "_dep_rel", rows, update_freq)

    for index, sentenceset in sorted(sentences.items()):
        for sentence in sorted(sentenceset):
            srow = {
                "id": index,
                "sentence": sentence[0],
                "start": int(sentence[1]),
                "end": int(sentence[2])
            }
            sentence_rows.append(srow)

    mysql.add_row(temp_db_table + "_sentences", sentence_rows)

    if last:
        mysql.enable_keys(temp_db_table, temp_db_table + "_strings", temp_db_table + "_rel",
                          temp_db_table + "_head_rel", temp_db_table + "_dep_rel", temp_db_table + "_sentences")
        mysql.drop_table(db_table, db_table + "_strings", db_table + "_rel", db_table + "_head_rel",
                         db_table + "_dep_rel", db_table + "_sentences")
        mysql.rename_table({
            temp_db_table: db_table,
            temp_db_table + "_strings": db_table + "_strings",
            temp_db_table + "_rel": db_table + "_rel",
            temp_db_table + "_head_rel": db_table + "_head_rel",
            temp_db_table + "_dep_rel": db_table + "_dep_rel",
            temp_db_table + "_sentences": db_table + "_sentences"
        })

        mysql.enable_checks()

    logger.info("%s written", sql_file)


################################################################################

# Names of every possible relation in the resulting database
RELNAMES = ["SS", "OBJ", "ADV", "AA", "AT", "ET", "PA"]
rel_enum = "ENUM(%s)" % ", ".join("'%s'" % r for r in RELNAMES)

MYSQL_TABLE = "relations"

MYSQL_RELATIONS = {"columns": [("id", int, 0, "NOT NULL"),
                               ("head", int, 0, "NOT NULL"),
                               ("rel", rel_enum, RELNAMES[0], "NOT NULL"),
                               ("dep", int, 0, "NOT NULL"),
                               ("freq", int, 0, "NOT NULL"),
                               ("bfhead", "BOOL", None, ""),
                               ("bfdep", "BOOL", None, ""),
                               ("wfhead", "BOOL", None, ""),
                               ("wfdep", "BOOL", None, "")],
                   "primary": "head wfhead dep rel freq id",
                   "indexes": ["dep wfdep head rel freq id",
                               "head dep bfhead bfdep rel freq id",
                               "dep head bfhead bfdep rel freq id"],
                   "constraints": [("UNIQUE INDEX", "relation", ("head", "rel", "dep"))],
                   "default charset": "utf8mb4",
                   "row_format": "compressed"
                   # "collate": "utf8mb4_bin"
                   }

MYSQL_STRINGS = {"columns": [("id", int, 0, "NOT NULL"),
                             ("string", "varchar(%d)" % MAX_STRING_LENGTH, "", "NOT NULL"),
                             ("stringextra", "varchar(%d)" % MAX_STRINGEXTRA_LENGTH, "", "NOT NULL"),
                             ("pos", "varchar(%d)" % MAX_POS_LENGTH, "", "NOT NULL")],
                 "primary": "string id pos stringextra",
                 "indexes": ["id string pos stringextra"],
                 "default charset": "utf8mb4",
                 "collate": "utf8mb4_bin",
                 "row_format": "compressed"
                 }

MYSQL_REL = {"columns": [("rel", rel_enum, RELNAMES[0], "NOT NULL"),
                         ("freq", int, 0, "NOT NULL")],
             "primary": "rel freq",
             "indexes": [],
             "constraints": [("UNIQUE INDEX", "relation", ("rel",))],
             "default charset": "utf8mb4",
             "collate": "utf8mb4_bin",
             "row_format": "compressed"
             }

MYSQL_HEAD_REL = {"columns": [("head", int, 0, "NOT NULL"),
                              ("rel", rel_enum, RELNAMES[0], "NOT NULL"),
                              ("freq", int, 0, "NOT NULL")],
                  "primary": "head rel freq",
                  "indexes": [],
                  "constraints": [("UNIQUE INDEX", "relation", ("head", "rel"))],
                  "default charset": "utf8mb4",
                  "collate": "utf8mb4_bin",
                  "row_format": "compressed"
                  }

MYSQL_DEP_REL = {"columns": [("dep", int, 0, "NOT NULL"),
                             ("rel", rel_enum, RELNAMES[0], "NOT NULL"),
                             ("freq", int, 0, "NOT NULL")],
                 "primary": "dep rel freq",
                 "indexes": [],
                 "constraints": [("UNIQUE INDEX", "relation", ("dep", "rel"))],
                 "default charset": "utf8mb4",
                 "collate": "utf8mb4_bin",
                 "row_format": "compressed"
                 }

MYSQL_SENTENCES = {"columns": [("id", int, None, ""),
                               ("sentence", "varchar(64)", "", "NOT NULL"),
                               ("start", int, None, ""),
                               ("end", int, None, "")],
                   "indexes": ["id"],
                   "default charset": "utf8mb4",
                   "collate": "utf8mb4_bin",
                   "row_format": "compressed"
                   }
