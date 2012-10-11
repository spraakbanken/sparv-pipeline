# -*- coding: utf-8 -*-

import sb.util as util
from time import sleep

import sb.util
import os

def silly(msg='silly'):
    util.log.output("Silly %s!", msg)
    sleep(0.1)
    util.log.output("Silly %s, a while later!", msg)

def ls():
    os.system('ls -lh')

def write(file, msg):
    f = open(file, 'w')
    f.write(msg + '\n')
    f.close()

if __name__ == '__main__':
    util.run.main(silly, ls=ls, write=write)
