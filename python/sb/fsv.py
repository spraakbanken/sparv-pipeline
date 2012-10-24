import saldo 
import lemgrampos
import util
import diapivot
import codecs
import re

def annotate_variants(word, out, spellmodel, model, delimiter="|", affix="|"):
    """Use a lexicon model and a spelling model to annotate words with their spelling variants
      - word is existing annotations for wordforms
      - out is a string containing the resulting annotation file
      - spellmodel is the spelling model
      - model is the lexicon model
      - delimiter is the delimiter character to put between ambiguous results
      - affix is an optional character to put before and after results
    """
 
    lexicon = saldo.SaldoLexicon(model)
    variations = parsevariant(spellmodel)
    def getlemgram(saldodict):
      def getlem(d):
        return d.get('lemgram',())
      return concat((getlem(x[0]) for x in saldodict))


    def findvariants(tokid,theword):
      variants = filter(lambda (x,d):x!=theword,variations.get(theword.lower(),[]))
      return set(concat([getlemgram(lexicon.lookup(v)) for v,d in variants]))

    annotate_standard(out,word,findvariants,split=False)
       
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
   
     

def concat(xs):
  return sum(xs,[])

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
 
def annotate_fallback(out,word,lemgram,model):
    """ Annotates the words that does not already have a lemgram, according to model 
        - out is the resulting annotation file
        - word is the words to be annotated
        - lemgram is the existing annotations for lemgram
        - model is the crosslink model
    """


    lexicon = saldo.SaldoLexicon(model)
    WORD = util.read_annotation(word)
    def annotate_empties(tokid,lemgrams):
      fallbacks = []
      if not lemgrams:
        word = WORD[tokid]
        for data,_,_,_ in lexicon.lookup(word):
          fallbacks += data.get('lemgram','')
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
   
def annotate_standard(out,input_annotation,f,extra_input='',delimiter="|", affix="|",split=True):
   """
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
       
       output_annotation = f(tokid,thelems)
       OUT[tokid] = affix + delimiter.join(list(output_annotation)) + affix if output_annotation else affix

   util.write_annotation(out, OUT)

 

if __name__ == '__main__':
    util.run.main(annotate_variants=annotate_variants,
                  extract_pos=extract_pos,
                  merge=merge,
                  posset=posset,
                  annotate_fallback=annotate_fallback,
                  annotate_diachron=annotate_diachron
                  )

