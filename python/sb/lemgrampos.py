# -*- coding: utf-8 -*-


def translatetag(tag):
    """A mapping from the tags in the lemgrams of lag1800 (a subset of saldos part
    of speech tags) to the korp POS-tagset."""

    d = {'nn': ['NN'],
         'av': ['JJ'],
         'vb': ['VB'],
         'pm': ['PM'],
         'ab': ['AB'],
         'in': ['IN'],
         'pp': ['PP'],
         'pn': ['PN'],
         'sn': ['SN'],
         'kn': ['KN'],
         'ie': ['IE'],
         'abh': ['AB'],
         'avh': ['NN'],
         'nnm': ['NN'],
         'nna': ['NN'],
         'avm': ['JJ'],
         'ava': ['JJ'],
         'vbm': ['VB'],
         'pmm': ['PM'],
         'abm': ['AB'],
         'aba': ['AB'],
         'pnm': ['PN'],
         'inm': ['IN'],
         'ppm': ['PP'],
         'ppa': ['PP'],
         'knm': ['KN'],
         'kna': ['KN'],
         'snm': ['SN'],
         'nl': ['RG', 'RO'],
         'nlm': ['RG', 'RO'],
         'al': ['DT'],
         'pma': ['PM'],
         'vb': ['VB']
         }

    return d.get(tag, [])
