# -*- coding: utf_8 -*-
import saldo 
import lemgrampos
import util
import diapivot
import codecs
import re
import itertools

def annotate_variants(word, out, spellmodel, model, delimiter="|", affix="|"):
    """Use a lexicon model and a spelling model to annotate words with their spelling variants
      - word is existing annotations for wordforms
      - out is a string containing the resulting annotation file
      - spellmodel is the spelling model
      - model is the lexicon model
      - delimiter is the delimiter character to put between ambiguous results
      - affix is an optional character to put before and after results
    """
    # model -> {word : [(variant,dist)]}
    def parsevariant(modelfile):
      d = {}
      def addword(res,word,info):
        for part in info.strip().split('^^'):
          if part:
            xs = part.split(',')
            res.setdefault(word,[]).append((xs[0],float(xs[1])))
    
      with codecs.open(modelfile,encoding='utf8') as f:
        for line in f:
          wd,info    = line.split(':::')
          addword(d,wd,info)
      return d
 
    lexicon = saldo.SaldoLexicon(model)
    variations = parsevariant(spellmodel)


    def findvariants(tokid,theword):
      variants = filter(lambda (x,d):x!=theword,variations.get(theword.lower(),[]))
      #return set(_concat([getsingleannotation(lexicon,v,'lemgram') for v,d in variants]))
      return set([v for v,d in variants])

    annotate_standard(out,word,findvariants,split=False)
       
  
     

def extract_pos(out,lemgrams, extralemgrams='',delimiter="|", affix="|"):
   """ Annotates each lemgram with pos-tags, extracted from this
     - out is the resulting annotation file
     - lemgram is the existing annotations for lemgram
     - extralemgrams is an optional extra annotation from which more pos-tags can be extracted
     - delimiter is the delimiter character to put between ambiguous results
     - affix is an optional character to put before and after results
   """

   def oktag(tag):
     return tag is not None and tag.group(1) not in ['e','sxc','mxc']


   def mkpos(tokid,thelems):
       pos  = [re.search('\.\.(.*?)\.',lem) for lem in thelems]
       return set(sum([lemgrampos.translatetag(p.group(1)) for p in pos if oktag(p)],[]))

   annotate_standard(out,lemgrams,mkpos,extralemgrams)
 
def annotate_fallback(out,word,lemgram,models,key='lemgram',lexicons=None):
    """ Annotates the words that does not already have a lemgram, according to model 
        - out is the resulting annotation file
        - word is the words to be annotated
        - lemgram is the existing annotations for lemgram
        - model is the crosslink model
    """

    # catalaunch stuff
    if lexicons is None:
      models = models.split()
      lexicons = [saldo.SaldoLexicon(lex) for lex in models]

    WORD = util.read_annotation(word)
    def annotate_empties(tokid,lemgrams):
      fallbacks = []
      if not lemgrams:
        word = WORD[tokid]
        fallbacks.extend(getsingleannotation(lexicons,word,key))

      return fallbacks

    annotate_standard(out,lemgram,annotate_empties)


def annotate_diachron(out,lemgram,model,extralemgrams='',delimiter="|", affix="|"):
  """ Annotates each lemgram with its corresponding saldo_id, according to model (diapivot.pickle)
   - out is the resulting annotation file
   - lemgram is the existing annotations for lemgram
   - model is the diapivot model
   - delimiter is the delimiter character to put between ambiguous results
   - affix is an optional character to put before and after results
  """

  lexicon = diapivot.PivotLexicon(model)
  def diachronlink(tokid,thelems):
     all_lemgrams = thelems
     for lemgram in thelems: 
       s_i = lexicon.get_exactMatch(lemgram)
       if s_i:
         all_lemgrams += [s_i]
     return all_lemgrams
 
  annotate_standard(out,lemgram,diachronlink,extralemgrams)

def mergemany(out, annotations, separator="|"):
    """Concatenate values from two or more annotations, with an optional separator.
       Removes superfluous separators"""
    #annotations = [util.read_annotation(a) for a in annotations]
    d ={}
    OUT ={}

    if isinstance(annotations, basestring):
        annotations = annotations.split()
    for annotation in [util.read_annotation(a) for a in annotations]:
      for key_a,val_a in annotation.items():
        if val_a:
          d.setdefault(key_a,[]).append(val_a)

    
    for key,lst in d.items():
      OUT[key] = separator + separator.join(lst) + separator if lst else separator

    util.write_annotation(out, OUT)


def merge(out, left, right, separator=""):
    """Concatenate values from two annotations, with an optional separator.
       Removes superfluous separators"""
    b = util.read_annotation(right)
    OUT ={}

    for key_a,val_a in util.read_annotation_iteritems(left):
      val = filter(lambda x:x!=separator,[val_a, b[key_a]])
      OUT[key_a] = separator.join(list(val)) if val else separator

    
    util.write_annotation(out, OUT)

def posset(out, pos, separator="|"):
    """Concatenate values from two annotations, with an optional separator.
       Removes superfluous separators"""
    oldpos = util.read_annotation(pos)
    OUT ={}

   # dummy function to annotated thepos with separators
    def makeset(tokid,thepos):
      return [thepos]

    annotate_standard(out,pos,makeset,split=False)
   
def annotate_standard(out,input_annotation,annotator,extra_input='',delimiter="|", affix="|",split=True):
   """
     Applies the 'annotator' function to the annotations in 'input_annotation' and writes the new output
     to 'out'. The annotator function should have type :: token_id -> oldannotations -> newannotations
     No support for multiword expressions
   - out is the output file
   - input_annotation is the given input annotation
   - f is the function which is to be applied to the input annotation
   - extra_input is an extra input annotation
   - delimiter is the delimiter character to put between ambiguous results
   - affix is an optional character to put before and after results
   - split defines if the input annatoation is a set, with elements separated by delimiter
     if so, return a list. Else, return one single element
   """
   def merge(d1,d2):
     result = dict(d1)
     for k,v in d2.iteritems():
       if k in result:
         result[k] = result[k]+delimiter+v
       else:
         result[k] = v
     return result
 
   LEMS = util.read_annotation(input_annotation)
   if extra_input:
     LEMS = merge(LEMS,util.read_annotation(extra_input))
     
   util.clear_annotation(out)
   OUT    = {}

   for tokid in LEMS:
       thelems = LEMS[tokid]
       if split: 
         thelems = [x for x in thelems.split(delimiter) if x!='']
       
       output_annotation = set(annotator(tokid,thelems))
       OUT[tokid] = affix + delimiter.join(list(output_annotation)) + affix if output_annotation else affix

   util.write_annotation(out, OUT)



def annotate_full(word, msd, sentence, reference, out, annotations, models, delimiter="|", affix="|", precision=":%.3f", filter=None, skip_multiword=False, lexicons=None):
    # TODO almost the same as normal saldo.annotate, but doesn't use msd or saldo-specific stuff
    """Use a lmf-lexicon model to annotate (pos-tagged) words.
      - word, msd are existing annotations for wordforms and part-of-speech
      - sentence is an existing annotation for sentences and their children (words)
      - reference is an existing annotation for word references, to be used when
        annotating multi-word units
      - out is a string containing a whitespace separated list of the resulting annotation files
      - annotations is a string containing a whitespace separate list of annotations to be written.
        Number of annotations and their order must correspond to the list in the 'out' argument.
      - model is the Saldo model
      - delimiter is the delimiter character to put between ambiguous results
      - affix is an optional character to put before and after results
      - precision is a format string for how to print the precision for each annotation
        (use empty string for no precision)
      - filter is an optional filter, currently there are the following values:
        max: only use the annotations that are most probable
        first: only use one annotation; one of the most probable
      - skip_multiword can be set to True to disable multi word annotations
    """
    MAX_GAPS = 0 # Maximum number of gaps in multi-word units.
                 # Set to 0 since many (most?) multi-word in the old lexicons are unseparable (half öre etc)
    
    annotations = annotations.split()
    out = out.split()
    assert len(out) == len(annotations), "Number of target files and annotations must be the same"

    skip_multiword = (isinstance(skip_multiword, bool) and skip_multiword == True) or (isinstance(skip_multiword, basestring) and skip_multiword.lower() == "true")
    
    # we allow multiple lexicons, each word will get annotations from only one of the lexicons, starting the lookup in the first lexicon in the list 
    if lexicons is None:
      models = models.split()
      lexicons = [saldo.SaldoLexicon(lex) for lex in models]
    WORD = util.read_annotation(word)
    MSD = util.read_annotation(msd)
    REF = util.read_annotation(reference)
    for out_file in out:
        util.clear_annotation(out_file)
    
    sentences = [sent.split() for _, sent in util.read_annotation_iteritems(sentence)]
    OUT = {}

    for sent in sentences:
        incomplete_multis = [] # :: [{annotation, words, [ref], is_particle, lastwordWasGap, numberofgaps}]
        complete_multis   = [] # :: ([ref], annotation)
        sentence_tokens   = {}
        
        for tokid in sent:
            thewords = [w for w in WORD[tokid].split('|') if w]
            msdtag = MSD[tokid]
            ref = REF[tokid]
            
            annotation_info = {}
            sentence_tokens[ref] = {"tokid": tokid, "word": thewords, "msd": msdtag, "annotations": annotation_info}
            
            for theword in thewords:  

              # First use MSD tags to find the most probable single word annotations
              ann_tags_words = findsingleword(theword,lexicons,msdtag,annotation_info)
                            
              # For multi-word expressions
              if not skip_multiword:
                findmultiwordexpressions(incomplete_multis,complete_multis,theword,ref,MAX_GAPS,ann_tags_words)

              # Loop to next token
        
        # Check that we don't have any unwanted overlaps
        removeunwantedoverlaps(complete_multis)
     
        # Then save the rest of the multi word expressions in sentence_tokens
        savemultiwords(complete_multis,sentence_tokens)

        for token in sentence_tokens.values():
            OUT[token["tokid"]] = saldo._join_annotation(token["annotations"], delimiter, affix)
        
        # Loop to next sentence

    for out_file, annotation in zip(out, annotations):
        util.write_annotation(out_file, [(tok, OUT[tok].get(annotation, affix)) for tok in OUT], append=True)


    
def findsingleword(theword,lexicons,msdtag,annotation_info):
    ann_tags_words = []

    for lexicon in lexicons:
      result = lexicon.lookup(theword)
      if result:
        ann_tags_words += result
        break
    #ann_tags_words += (lexicon.lookup(theword) for lexicon in lexicons).next()

    annotation_precisions = [annotation for (annotation, msdtags, wordslist, _) in ann_tags_words if not wordslist]
    for annotation in annotation_precisions:
        for key in annotation:
            annotation_info.setdefault(key, []).extend(annotation[key])
    return ann_tags_words
      

def findmultiwordexpressions(incomplete_multis,complete_multis,theword,ref,MAX_GAPS,ann_tags_words):
    todelfromincomplete = [] # list to keep track of which expressions that have been completed
    
    for i, x in enumerate(incomplete_multis):
        seeking_word = x['words'][0] # The next word we are looking for in this multi-word expression
        
        # TODO '*' only in saldo
        if seeking_word == "*":
            if x['words'][1].lower() == theword.lower():
                seeking_word = x['words'][1]
                del x['words'][0]
        
        if x['numberofgaps'] > MAX_GAPS:
            todelfromincomplete.append(i)

        elif seeking_word.lower() == theword.lower():
            x['lastwordwasgap'] = False
            del x['words'][0]
            x['ref'].append(ref)
            
            # Is current word the last word we are looking for?
            if len(x['words']) == 0:
                todelfromincomplete.append(i)
                complete_multis.append((x['ref'], x['annotation']))
        else:
            # Increment gap counter if previous word was not part of a gap
            if not x['lastwordwasgap']:       
                x['numberofgaps'] += 1
            x['lastwordwasgap'] = True # Marking that previous word was part of a gap
                    
    # Remove found word from incompletes-list
    for x in todelfromincomplete[::-1]:
        del incomplete_multis[x]
    
    # Is this word a possible start for multi-word units?
    looking_for = [{'annotation': annotation,'words': words, 'ref': [ref]
                   , 'is_particle': is_particle, 'lastwordwasgap' : False, 'numberofgaps': 0}
                  for (annotation, _, wordslist, is_particle) in ann_tags_words if wordslist for words in wordslist]
    if len(looking_for) > 0:
        incomplete_multis.extend(looking_for)

def getsingleannotation(lexicons,word,key):
  annotation = [] 
  for lexicon in lexicons:
    res = [ann for (ann, msdtags, wordslist, _) in lexicon.lookup(word) if not wordslist]
    if res:
      annotation = res
      break
  return _concat(x.get(key) for x in annotation)

def removeunwantedoverlaps(complete_multis):
  remove = set()
  for ci, c in enumerate(complete_multis):
      for d in complete_multis:
        if re.search(r"(.*)--.*", c[1]["lemgram"][0]).groups()[0] != re.search(r"(.*)--.*", d[1]["lemgram"][0]).groups()[0]:
          # Both are from the same lexicon
          remove.add(ci)
        elif len(set(c[0]))!=len(c[0]):
          # Since we allow many words for one token (when using spelling variation)
          # we must make sure that two words of a mwe are not made up by two variants of one token
          # that is, that the same reference-id is not used twice in a mwe
          remove.add(ci)
        elif re.search(r"\.\.(\w+)\.", c[1]["lemgram"][0]).groups()[0] == re.search(r"\.\.(\w+)\.", d[1]["lemgram"][0]).groups()[0]:
            # Both are of same POS
            if d[0][0] < c[0][0] and d[0][-1] > c[0][0] and d[0][-1] < c[0][-1]:
                # A case of x1 y1 x2 y2. Remove y.
                remove.add(ci)
            elif c[0][0] < d[0][0] and d[0][-1] == c[0][-1]:
                #A case of x1 y1 xy2. Remove x.
                remove.add(ci)
  
  for c in sorted(remove, reverse=True):
      del complete_multis[c]
 
def savemultiwords(complete_multis,sentence_tokens):
  for c in complete_multis:
      first = True
      first_ref = ""
      for tok_ref in c[0]:
          if first:
              first_ref = tok_ref
          for ann, val in c[1].items():
              if not first:
                  val = [x + ":" + first_ref for x in val]
              sentence_tokens[tok_ref]["annotations"].setdefault(ann, []).extend(val)
          first = False
        

def _concat(xs):
  return sum(xs,[])


if __name__ == '__main__':
    util.run.main(annotate_variants=annotate_variants,
                  extract_pos=extract_pos,
                  merge=merge,
                  mergemany=mergemany,
                  posset=posset,
                  annotate_full=annotate_full,
                  annotate_fallback=annotate_fallback,
                  annotate_diachron=annotate_diachron
                  )

