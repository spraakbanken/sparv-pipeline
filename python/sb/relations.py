# -*- coding: utf-8 -*-

import util

# python -m sb.relations --out "" --pos annotations/test.token.pos --lemgram annotations/test.token.lemgram --dephead annotations/test.token.dephead --deprel annotations/test.token.deprel --sentence annotations/test.children.sentence.token --word annotations/test.token.word

def relations(out, word, pos, lemgram, dephead, deprel, sentence, encoding=util.UTF8):
    """ """

    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    WORD = util.read_annotation(word)
    POS = util.read_annotation(pos)
    LEM = util.read_annotation(lemgram)
    DEPHEAD = util.read_annotation(dephead)
    DEPREL = util.read_annotation(deprel)
    
    triples = []
    
    for sent in sentences:
        
        incomplete = {}
        previous = {}
        
        for token_id in sent:
            token_pos = POS[token_id]
            token_lem = LEM[token_id]
            token_dh  = DEPHEAD[token_id]
            token_dr  = DEPREL[token_id]
            
            if token_lem == "|":
                token_lem = WORD[token_id] + "_" + token_pos
            else:
                token_lem = "|" + "|".join(sorted(l for l in token_lem[1:-1].split("|") if not "_" in l)) + "|"
            
            previous[token_id] = (token_lem, token_pos)
            
            if not token_dh == "-":
                triple = [None, token_dr, (token_lem, token_pos)]
                if token_dh in previous:
                    triple[0] = (previous[token_dh])
                    triples.append(tuple(triple))
                else:
                    incomplete.setdefault(token_dh, []).append(triple)
            
            if token_id in incomplete:
                for t in incomplete[token_id]:
                    t[0] = (token_lem, token_pos)
                    triples.append(tuple(t))
                del incomplete[token_id]
    
    print "Incomplete:", len(incomplete)
    
    OUT = [(str(i), "\t".join(("^".join(head), rel, "^".join(w)))) for (i, (head, rel, w)) in enumerate(triples)]
    util.write_annotation(out, OUT)


def frequency(source):
    
    pos_filter = (u"VB", u"NN", u"JJ")
    rel_filter = (u"SS", u"OO", u"IO", u"AT", u"ET" u"DT", u"OA", u"RA", u"TA") # http://stp.ling.uu.se/~nivre/swedish_treebank/dep.html
    min_count = 10
    
    source = source.split()
    
    freq = {}
    
    for s in source:
        REL = util.read_annotation(s)

        for _, triple in REL.iteritems():
            head, rel, w = triple.split(u"\t")
            #print "%50s %5s   %-50s" % (head, rel, w)
            freq.setdefault(head, {}).setdefault(rel, {}).setdefault(w, 0)
            freq[head][rel][w] += 1
        
    phead = prel = None
    
    with open("relationer.txt", "w") as F:
        for head, rels in freq.iteritems():
            for rel, w in rels.iteritems():
                for w, count in sorted(w.iteritems(), key=lambda x: -x[1]):
                    head_lem, head_pos = head.split(u"^")
                    w_lem, w_pos = w.split(u"^")
                    if count >= min_count and head_pos in pos_filter and w_pos in pos_filter and rel in rel_filter:
                        printhead = u"." if head == phead else head_lem
                        printrel  = u"." if head == phead and rel == prel else rel
                        phead = head
                        prel  = rel
                        print >>F, ("%50s %5s   %-50s %5d" % (printhead, printrel, w_lem, count)).encode("UTF-8")
    
################################################################################    

if __name__ == '__main__':
    util.run.main(relations, frequency=frequency)
