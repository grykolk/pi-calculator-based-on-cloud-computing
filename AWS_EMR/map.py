#!/usr/bin/env python
import sys
import random

for line in sys.stdin:
    line=int(line.strip())
    incircle = 0
    shots=line
    for i in range(0, shots):
        
        random1 = random.uniform(-1.0, 1.0)
        random2 = random.uniform(-1.0, 1.0)
        if( ( random1*random1 + random2*random2 ) < 1 ):
            incircle += 1
    print 4.0*incircle
