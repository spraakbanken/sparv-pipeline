# -*- coding: utf-8 -*-

import json
import sys
import codecs

global textstring
        
def jsontostandoff(jsonfile):
    textstring = '<text title=\"Korp-revert\">'
    
    """Checks if an annotation file exists."""
    s = jsonfile.read()
 
    decoded = json.loads(s)
    """print 'decoded: ', decoded"""

    runLoop = 0
    
    kwic = decoded.pop('kwic')
    """print >> sys.stdout, len(kwic)"""
    
    while runLoop < len(kwic):
        item = kwic[runLoop]
        runLoop = runLoop + 1
        """print >> sys.stdout, item"""
        
        j = 0
        tokensList = item.pop('tokens')
        textstring = textstring + '\n '
        while j < len(tokensList):
            token = tokensList[j]
            j = j + 1
            """print >> sys.stdout, token"""

            word = token.pop('word')
            pos = token.pop('pos')
            """print >> sys.stdout, word"""
            if pos not in ['MAD', 'MID']:
                textstring = textstring + ' '
            
            textstring = textstring + '<w pos=\"' + pos + '\">' + word + '</w>'

    """print >> sys.stdout, decoded;"""
    textstring = textstring + "</text>"
    """print >> sys.stdout, textstring"""
    
    f = codecs.open(sys.argv[2], 'w', "utf-8")
    f.write(textstring)
        
def printtoken(entry):
        """print 'kwic:', entry"""
        kwicpop = entry.pop()
        """tokens = kwic.pop('tokens');"""

        
        tokenspop = kwicpop.pop()
        tokenlist = kwicpop.iteritems()
        print >> sys.stdout, 'tokens:', tokenspop
        
        runLoop = True
        
        global textstring
        
        while runLoop:
            if 'word' not in tokenlist:
                runLoop = False
                print >> sys.stdout, 'FALSE'
            else:
                
                word = tokenlist.next()
                print >> sys.stdout, 'TRUE', word
                textstring + ', ' + word
                print >> sys.stdout, textstring

        return textstring
    
    
def printword(prefix):
     word = prefix.pop('word')
     return word
    
    
if __name__ == '__main__':
    jsonfile = codecs.open(sys.argv[1], "r", "utf-8" )
    jsontostandoff(jsonfile)
