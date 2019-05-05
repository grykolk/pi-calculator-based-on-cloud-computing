
import os
import webapp2
import jinja2
import httplib
import json
import Queue
import threading
import math
import numpy as np
import boto
from boto.s3.connection import S3Connection
from boto.s3.key import Key
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_environment = jinja2.Environment( loader = jinja2.FileSystemLoader(template_dir), autoescape=True)
	
def doRender(handler, tname, values={}):
	temp = os.path.join(os.path.dirname(__file__), 'templates/'+tname)
	if not os.path.isfile(temp):
		doRender(handler, 'index.htm')
		return

	# Make a copy of the dictionary and add the path
	newval = dict(values)
	newval['path'] = handler.request.path

	template = jinja_environment.get_template(tname)
	handler.response.out.write(template.render(newval))
	return True
def lambda_call(shots,Q,queue):
    c = httplib.HTTPSConnection("b5e5hz094g.execute-api.eu-west-2.amazonaws.com")
    json_send= '{ "shots_each_threat": "'+str(shots)+'","Q": "'+str(Q)+'"}'
    c.request("POST", "/default", json_send)
    response = c.getresponse()
    queue.put(json.loads(response.read()))
def multithreading_lambda_call(shots,Q,thread_count):
    queue=Queue.Queue()
    threads=[]
    for i in range(thread_count):
        t=threading.Thread(target=lambda_call,args=(shots,Q,queue))
        t.start()
        threads.append(t)
    for thread in threads:
        thread.join()
    results=[]
    for i in range(thread_count):
        results[thread_count*Q:(thread_count*Q)+Q]=queue.get()
    return results
class S3Handler(webapp2.RequestHandler):
    def post(self):
        s3_connection=S3Connection('AKIAI7AQSIAKUCHT2IWA','sVOEy7qRNZ18Ef138lIRCsQCyzcRRlxE/1OD0GYl')
        bucket=s3_connection.get_bucket('temp0331')
        k=Key(bucket)
        k.key='record.json'
        k.set_contents_from_string('[160,156]')
        doRender(self,'index.htm',{'note':bucketnames})
class CalculateHandler(webapp2.RequestHandler):
	def post(self):
		try:
			R =int( self.request.get('R'))
			Q = int(self.request.get('Q'))
			shots = int(self.request.get('total_shots'))
			mode = int(self.request.get('mode'))
			server = int(self.request.get('server'))
		except OSError as reason:
			doRender(
					self,
					'index.htm',
					{'note':str(reason)})
                shotsForEachThread=shots//R
                shotsForEachBlock=shotsForEachThread//Q

		if mode == 1 :
			accuracy = int(self.request.get('accuracy'))
                        runtimes=0
                        found=0
                        PYdata=np.zeros(Q*R)#set as a numpy array
                        while(found==0):
                            runtimes+=1
                            #use+=  here to cumulative value for each calculation
                            PYdata +=multithreading_lambda_call(shotsForEachThread,Q,R)
                            if(round(np.sum(PYdata)/(shots*runtimes),accuracy)==round(math.pi,accuracy)):
                                found=1
                        for i in range(1,len(PYdata)):
				PYdata[i]+=PYdata[i-1]
				PYdata[i-1]/=shotsForEachBlock*(i)*runtimes
			PYdata[len(PYdata)-1]/=shotsForEachBlock*len(PYdata)*runtimes
			data=json.dumps(PYdata.tolist())#covernt numpy array to list
                        doRender(self,'chart.htm',{'Data':data,'shots_each_threat':shotsForEachBlock,'R':R,'Q':Q,'pi':math.pi,'shots':shots*runtimes,'result':PYdata[len(PYdata)-1]})
		
		else:

			PYdata =multithreading_lambda_call(shotsForEachThread,Q,R)
			for i in range(1,len(PYdata)):
				PYdata[i]+=PYdata[i-1]
				PYdata[i-1]/=shotsForEachBlock*(i)
			PYdata[len(PYdata)-1]/=shotsForEachBlock*len(PYdata)
			data=json.dumps(PYdata)
    			doRender(self,'chart.htm',{'Data':data,'shots_each_threat':shotsForEachBlock,'R':R,'Q':Q,'pi':math.pi,'shots':shots,'result':PYdata[len(PYdata)-1]})



class MainPage(webapp2.RequestHandler):
	def get(self):
		path = self.request.path
		doRender(self, path)

app = webapp2.WSGIApplication([('/s3',S3Handler),('/calculate', CalculateHandler),('/.*', MainPage)],debug=True)

