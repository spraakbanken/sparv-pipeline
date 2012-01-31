# -*- coding: utf-8 -*-

import json
import sys
import codecs

var = '<text title=\"Korp revert\">'
        
def jsontostandoff(jsonfile):
    """Checks if an annotation file exists."""
    s = jsonfile.read()
 
    decoded = json.loads(s)
    """print 'decoded: ', decoded"""

    runLoop = 0
    
    global var
    
    kwic = decoded.pop('kwic')
    """print >> sys.stdout, len(kwic)"""
    
    while runLoop < len(kwic):
        item = kwic[runLoop]
        runLoop = runLoop + 1
        """print >> sys.stdout, item"""
        
        j = 0
        tokensList = item.pop('tokens')
        var = var + '\n '
        while j < len(tokensList):
            token = tokensList[j]
            j = j + 1
            """print >> sys.stdout, token"""

            word = token.pop('word')
            """print >> sys.stdout, word"""
            var = var + ' ' + word

    """print >> sys.stdout, decoded;"""
    var = var + "</text>\n"
    """print >> sys.stdout, var"""
    
    f = codecs.open(sys.argv[2], 'w', "utf-8")
    f.write(var)


        
def printtoken(entry):
        """print 'kwic:', entry"""
        kwicpop = entry.pop()
        """tokens = kwic.pop('tokens');"""

        
        tokenspop = kwicpop.pop()
        tokenlist = kwicpop.iteritems()
        print >> sys.stdout, 'tokens:', tokenspop
        
        runLoop = True
        
        global var
        
        while runLoop:
            if 'word' not in tokenlist:
                runLoop = False
                print >> sys.stdout, 'FALSE'
            else:
                
                word = tokenlist.next()
                print >> sys.stdout, 'TRUE', word
                var + ', ' + word
                print >> sys.stdout, var

        return var
    
    
def printword(prefix):
     word = prefix.pop('word')
     return word
    
    
if __name__ == '__main__':
    jsonfile = codecs.open(sys.argv[1], "r", "utf-8" )
    jsontostandoff(jsonfile)
