
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
import boto.emr
from boto.emr.connection import EmrConnection
from boto.emr.step import StreamingStep
from boto.emr.instance_group import InstanceGroup

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
        results[i*Q:(i*Q)+Q]=queue.get()
    return results
class S3Handler(webapp2.RequestHandler):
    def post(self):
        s3_connection=S3Connection('AKIAI7AQSIAKUCHT2IWA','sVOEy7qRNZ18Ef138lIRCsQCyzcRRlxE/1OD0GYl')
        bucket=s3_connection.get_bucket('bucket774')
        k=Key(bucket)
        k.key='record.json'
        data=k.get_contents_as_string()
        k.key='record_para.json'
        data_para_json=k.get_contents_as_string()
        data_para=json.loads(data_para_json)
        doRender(self,'chart.htm',{'Data':data,'shots_each_threat':data_para[0],'R':data_para[1],'Q':data_para[2],'pi':math.pi,'shots':data_para[3],'result':data_para[4]})
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
                        
		
		else:
                    if server==0:

			PYdata =multithreading_lambda_call(shotsForEachThread,Q,R)
			for i in range(1,len(PYdata)):
				PYdata[i]+=PYdata[i-1]
				PYdata[i-1]/=shotsForEachBlock*(i)
			PYdata[len(PYdata)-1]/=shotsForEachBlock*len(PYdata)
			data=json.dumps(PYdata)
                    else:
                        emr_input=''
                        for i in range(R*Q):
                            emr_input+=str(shotsForEachBlock)
                            emr_input+='\n'

                        s3_connection=S3Connection('AKIAI7AQSIAKUCHT2IWA','sVOEy7qRNZ18Ef138lIRCsQCyzcRRlxE/1OD0GYl')
                        bucket=s3_connection.get_bucket('bucket774')
                        for key in bucket.list(prefix='output/'):
                            key.delete()
                        k=Key(bucket)
                        k.key='input/0001'
                        k.set_contents_from_string(emr_input)
                        step=StreamingStep(name='MC_Method example',mapper='s3://bucket774/map.py',reducer='s3://',input='s3://input/',output='s3://output/')
                        #emr_conn=boto.emr.connect_to_region(region_name='eu-west-2',aws_access_key_id='AKIAI7AQSIAKUCHT2IWA',aws_secret_access_key='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',)
                        emr_conn=EmrConnection('AKIAI7AQSIAKUCHT2IWA','sVOEy7qRNZ18Ef138lIRCsQCyzcRRlxE/1OD0GYl')
                        instance_groups=[]
                        instance_groups.append(InstanceGroup(num_instances=1,role="MASTER",type='m4.large',market="ON_DEMAND",name="Master nodes"))
                        if R>1:
                            instance_groups.append(InstanceGroup(num_instances=R-1,role="CORE",type='m4.large',market="ON_DEMAND",name="Slave nodes"))
                        cluster_id=emr_conn.run_jobflow(name='test MC_method run',availability_zone='eu-west-2b',instance_groups=instance_groups,enable_debugging=False,steps=[step], visible_to_all_users=True, keep_alive=False, job_flow_role="EMR_EC2_DefaultRole",service_role="EMR_EC2_DefaultRole",hadoop_version='2.4.0')





    		s3_connection=S3Connection('AKIAI7AQSIAKUCHT2IWA','sVOEy7qRNZ18Ef138lIRCsQCyzcRRlxE/1OD0GYl')
                bucket=s3_connection.get_bucket('bucket774')
                k=Key(bucket)
                k.key='record.json'
                k.set_contents_from_string(data)
                k.key='record_para.json'
                parameter='['+str(shotsForEachBlock)+','+str(R)+','+str(Q)+','+str(shots)+','+str(PYdata[len(PYdata)-1])+']'
                #record_para=json.loads(parameter)
                k.set_contents_from_string(parameter)
                doRender(self,'chart.htm',{'Data':data,'shots_each_threat':shotsForEachBlock,'R':R,'Q':Q,'pi':math.pi,'shots':shots,'result':PYdata[len(PYdata)-1]})



class MainPage(webapp2.RequestHandler):
	def get(self):
		path = self.request.path
		doRender(self, path)

app = webapp2.WSGIApplication([('/s3',S3Handler),('/calculate', CalculateHandler),('/.*', MainPage)],debug=True)

