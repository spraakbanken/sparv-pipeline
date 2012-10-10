# -*- coding: utf-8 -*-

import sb.saldo
import sb.compound
import util

from sb.util.membrane import serve_membranes

def start_server(saldo_model=None, compound_model=None,
                 hostname='localhost', port=8051, extendable=False):
    """
    Serves saldo and saldo compound annotation membrane requests.

    Set either or both of saldo_model and compound_model to a matching
    pickle file. If just one is set, then the address
    http://hostname:port can be queried, otherwise, use
    http://hostname:port/saldo and http://hostname:port/compound.
    """

    config = {}

    if saldo_model:
        config['saldo'] = dict(membrane=sb.saldo.annotate,
                               preload=[saldo_model],
                               extendable=extendable)

    if compound_model:
        config['compound'] = dict(membrane=sb.compound.annotate,
                                  preload=[compound_model],
                                  extendable=extendable)

    serve_membranes(hostname, port, **config)

if __name__ == '__main__':
    util.run.main(start_server)
