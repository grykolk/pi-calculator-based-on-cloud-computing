
import os
import webapp2
import jinja2
import httplib
import json
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
		if mode == 1 :
			accuracy = int(self.request.get('accuracy'))
		
		else:
			shotsForEachBlock=shots//(Q*R)
			#threat loop
			c = httplib.HTTPSConnection("b5e5hz094g.execute-api.eu-west-2.amazonaws.com")
			json= '{ "shots_each_threat": "'+str(shots)+'","Q": "'+str(Q)+'"}'
			c.request("POST", "/default", json)
			response = c.getresponse()
			data = response.read()
			PYdata=json.loads(data)
			for i in range(1,len(PYdata)):
				PYdata[i]+=PYdata[i-1]
				PYdata[i-1]/=shotsForEachBlock*(i)
			PYdata[len(PYdata)-1]/=shotsForEachBlock*len(PYdata)
			data=json.dumps(PYdata)
			doRender(self,'chart.htm',{'Data':data,'shots_each_threat':shotsForEachBlock})
			#doRender(self,'index.htm',{'note':data})#demo test line
			#doRender(self,'chart.htm',
			#{'data': str(mP) + ',' + str(fP)})

class MainPage(webapp2.RequestHandler):
	def get(self):
		path = self.request.path
		doRender(self, path)

app = webapp2.WSGIApplication([('/calculate', CalculateHandler),('/.*', MainPage)],
							  debug=True)


