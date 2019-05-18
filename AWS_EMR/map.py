#!/usr/bin/python
import sys
import random
def main(argv): 
	for line in sys.stdin:
		shots=int(line)
		incircle = 0
		for i in range(0, shots):
		        random1 = random.uniform(-1.0, 1.0)
		        random2 = random.uniform(-1.0, 1.0)
		        if( ( random1*random1 + random2*random2 ) < 1 ):
		                incircle += 1
		incircle *= 4
		print str(incircle)+','
if __name__ == "__main__": 
    main(sys.argv) 
