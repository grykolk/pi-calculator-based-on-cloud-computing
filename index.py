import time
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
#import boto.emr
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

def save_result(data,para):
    s3_connection=S3Connection(access_id,access_key)
    bucket=s3_connection.get_bucket('bucket774')
    k=Key(bucket)
    k.key='record.json'
    k.set_contents_from_string(data)
    k.key='record_para.json'
    k.set_contents_from_string(para)

def set_input_and_delete_output(R,Q,shotsForEachBlock):
    emr_input=''
    for i in range(R*Q):
        emr_input+=str(shotsForEachBlock)
        emr_input+='\n'
    s3_connection=S3Connection(access_id,access_key)
    bucket=s3_connection.get_bucket('bucket774')
    for key in bucket.list(prefix='output/'):
        key.delete()
    k=Key(bucket)
    k.key='input/0001'
    k.set_contents_from_string(emr_input)

def create_emr(R):
    if not boto.config.has_section('Boto'):
        boto.config.add_section('Boto')
    boto.config.set('Boto','https_validate_certificates','False')
    step=StreamingStep(name='MC_Method example', cache_files=['s3n://bucket774/map.py#map.py'],mapper='map.py',input='s3://bucket774/input/',output='s3://bucket774/output/')
    conn=EmrConnection(access_id,access_key)
    instance_groups=[]
    instance_groups.append(InstanceGroup(num_instances=1,role="MASTER",type='m4.large',market="ON_DEMAND",name="Master nodes"))
    if R>1:
        instance_groups.append(InstanceGroup(num_instances=R-1,role="CORE",type='m4.large',market="ON_DEMAND",name="Slave nodes"))
    cluster_id=conn.run_jobflow(name='test MC_method run',instance_groups=instance_groups,enable_debugging=False,steps=[step], visible_to_all_users=True, keep_alive=True, job_flow_role="EMR_EC2_DefaultRole",service_role="EMR_DefaultRole",hadoop_version='2.4.0',log_uri='s3://bucket774/log')
    return cluster_id,conn
def add_step_emr(conn,cluster_id):
    step=StreamingStep(name='MC_Method example', cache_files=['s3n://bucket774/map.py#map.py'],mapper='map.py',input='s3://bucket774/input/',output='s3://bucket774/output/')
    conn.add_jobflow_steps(cluster_id,step)
def get_output():
    data=''
    conn=S3Connection(access_id,access_key)
    bucket=conn.get_bucket('bucket774')
    k=Key(bucket)
    #k.key='output/part-00000'
    for key in bucket.list(prefix='output/part'):
        data+=key.get_contents_as_string()
    data=data.replace('\t\n','')#remove format
    data=data[:-1]#remove the final ","into the string
    return json.loads('['+data+']')

def in_circle_to_pi(PYdata,shotsForEachBlock):
    for i in range(1,len(PYdata)):
        PYdata[i]+=PYdata[i-1]
	PYdata[i-1]/=float(shotsForEachBlock*(i))
    PYdata[len(PYdata)-1]/=float(shotsForEachBlock*len(PYdata))
    return json.dumps(PYdata)
    
def store_parameter(shots_each_block,R,Q,shots,accuracy,runtime,emr_jobflow_working,emr_job_mode):
    s3_connection=S3Connection(access_id,access_key)
    bucket=s3_connection.get_bucket('bucket774')
    k=Key(bucket)
    k.key='temp_para.json'
    k.set_contents_from_string(json.dumps([shots_each_block,R,Q,shots,accuracy,runtime,emr_jobflow_working,emr_job_mode]))
def save_temp_result(PYdata):
    s3_connection=S3Connection(access_id,access_key)
    bucket=s3_connection.get_bucket('bucket774')
    k=Key(bucket)
    k.key='temp_data.json'
    k.set_contents_from_string(json.dumps(PYdata.tolist()))
def save_cluster_id(cluster_id):
    s3_connection=S3Connection(access_id,access_key)
    bucket=s3_connection.get_bucket('bucket774')
    k=Key(bucket)
    k.key='cluster_id'
    k.set_contents_from_string(cluster_id)
class S3Handler(webapp2.RequestHandler):
    def post(self):
        if not boto.config.has_section('Boto'):
            boto.config.add_section('Boto')
        boto.config.set('Boto','https_validate_certificates','False')
        note=''
        data_para=[0,0,0,0,0]
        s3_connection=S3Connection(access_id,access_key)
        bucket=s3_connection.get_bucket('bucket774')
        k=Key(bucket)
        k.key='temp_para.json'
        temp_para=json.loads(k.get_contents_as_string())
        if(temp_para[6]==1):
            k.key='cluster_id'
            cluster_id=k.get_contents_as_string()
            conn=EmrConnection(access_id,access_key)
            if(temp_para[7]==0):
                status=conn.describe_cluster(cluster_id)
                if(status.status.state=='WAITING'):
                    PYdata=get_output()
                    conn.terminate_jobflow(cluster_id)
                    data=in_circle_to_pi(PYdata,temp_para[0])
                    k.key='temp_para.json'
                    temp_para[6]=0
                    k.set_contents_from_string(json.dumps(temp_para))
                    data_para[0:4]=temp_para[0:4]
                    data_para[4]=json.loads(data)[-1]
                    note='last emr job done, reslut have been updated'
                    save_result(json.dumps(data),json.dumps(data_para))

                else:
                    note='last emr calculation havet finished,please waitting.'
                    k.key='record.json'
                    data=k.get_contents_as_string()
                    k.key='record_para.json'
                    data_para_json=k.get_contents_as_string()
                    data_para=json.loads(data_para_json)
            elif(temp_para[7]==1):
                status=conn.describe_cluster(cluster_id)
                if(status.status.state=='WAITING'):
                    k.key='temp_data.json'
                    PYdata=np.array(json.loads(k.get_contents_as_string()))
                    PYdata+=get_output()
                    if(round(np.sum(PYdata)/(temp_para[3]*temp_para[5]),temp_para[4])==round(math.pi,temp_para[4])):
                        for i in range(1,len(PYdata)):
			    PYdata[i]+=PYdata[i-1]
			    PYdata[i-1]/=temp_para[0]*(i)*temp_para[5]
			PYdata[len(PYdata)-1]/=temp_para[0]*len(PYdata)*temp_para[5]
			data=json.dumps(PYdata.tolist())#covernt numpy array to list

                        k.key='temp_para.json'
                        temp_para[6]=0
                        k.set_contents_from_string(json.dumps(temp_para))
                        data_para[0:4]=temp_para[0:4]
                        data_para[4]=json.loads(data)[-1]
                        conn.terminate_jobflow(cluster_id)
                        note='last emr job done,result have been updated'
                        save_result(json.dumps(data),json.dumps(data_para))
                    else:
                        note=str(np.sum(PYdata))+','+str(temp_para[3])+','+str(temp_para[5])
                        add_step_emr(conn,cluster_id)
                        save_temp_result(PYdata)
                        for key in bucket.list(prefix='output/'):
                            key.delete()
                        temp_para[5]+=1
                        k.key='temp_para.json'
                        k.set_contents_from_string(json.dumps(temp_para))
                        #note='havet find the given accuracy in last run, keep working'
                        k.key='record.json'
                        data=k.get_contents_as_string()
                        k.key='record_para.json'
                        data_para_json=k.get_contents_as_string()
                        data_para=json.loads(data_para_json)
                else:
                    note='last emr calculation havet finished,please waitting.'
                    k.key='record.json'
                    data=k.get_contents_as_string()
                    k.key='record_para.json'
                    data_para_json=k.get_contents_as_string()
                    data_para=json.loads(data_para_json)
        else:
            k.key='record.json'
            data=k.get_contents_as_string()
            k.key='record_para.json'
            data_para_json=k.get_contents_as_string()
            data_para=json.loads(data_para_json)

        doRender(self,'chart.htm',{'Data':data,'shots_each_threat':data_para[0],'R':data_para[1],'Q':data_para[2],'pi':math.pi,'shots':data_para[3],'result':data_para[4],'note':note})
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

		if mode == 1 :#mode=given accuracy
			accuracy = int(self.request.get('accuracy'))
                        runtimes=0
                        found=0
                        PYdata=np.zeros(Q*R)#set as a numpy array
                        if server==0:#server=lanbda, mode =given accuracy
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
                            parameter='['+str(shotsForEachBlock)+','+str(R)+','+str(Q)+','+str(shots)+','+str(PYdata[len(PYdata)-1])+']'
                            save_result(data,parameter)
                            doRender(self,'chart.htm',{'Data':data,'shots_each_threat':shotsForEachBlock,'R':R,'Q':Q,'pi':math.pi,'shots':shots,'result':PYdata[len(PYdata)-1]})

                        elif server==1:#server=emr, mode =given accuracy

                            set_input_and_delete_output(Q,R,shotsForEachBlock)
                            cluster_id,conn=create_emr(R)
                            store_parameter(shotsForEachBlock,R,Q,shots,accuracy,1,1,1)
                            save_cluster_id(cluster_id)
                            save_temp_result(np.zeros(R*Q))
                            doRender(self,'index.htm',{'note':'emr has create,pleast waiting for the result'})

                        
		
                elif mode==0:#mode=given number
                    if server==0:#server=lambda, mode=given number

			PYdata =multithreading_lambda_call(shotsForEachThread,Q,R)
                        parameter='['+str(shotsForEachBlock)+','+str(R)+','+str(Q)+','+str(shots)+','+str(PYdata[len(PYdata)-1])+']'
                        save_result(data,parameter)
                        doRender(self,'chart.htm',{'Data':data,'shots_each_threat':shotsForEachBlock,'R':R,'Q':Q,'pi':math.pi,'shots':shots,'result':PYdata[len(PYdata)-1]})

			
                    elif server==1:#server=emr,mode=give number
                        set_input_and_delete_output(R,Q,shotsForEachBlock)
                        cluster_id,conn=create_emr(R)
                        store_parameter(shotsForEachBlock,R,Q,shots,0,0,1,0)
                        save_cluster_id(cluster_id)
                        doRender(self,'index.htm',{'note':'emr has create, please waiting for the result'})




class MainPage(webapp2.RequestHandler):
	def get(self):
		path = self.request.path
		doRender(self, path)

app = webapp2.WSGIApplication([('/s3',S3Handler),('/calculate', CalculateHandler),('/.*', MainPage)],debug=True)

