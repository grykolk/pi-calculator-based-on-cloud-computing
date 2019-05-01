import json
import random
def lambda_handler(event, context):
    # TODO implement
    shots = int(event['shots_each_threat'])
    Q=int(event['Q'])
    result=[0 for i in range(Q)]
    for j in range(0,Q):
            incircle=0
            for s in range(0,shots//Q):
                random1 = random.uniform(-1.0, 1.0)
                random2 = random.uniform(-1.0, 1.0)
                if( ( random1*random1 + random2*random2 ) < 1 ):
                    incircle += 1
            result[j]= 4.0 * incircle
    return result