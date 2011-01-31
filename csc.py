import numpy
import datetime

version = '1.0'

def begin(meta,properties,filename):
	global version
	f=open(filename, 'w')
	#write come comments at the top
	f.write('# Generated by MmCalc v'+version+'\n')
	f.write('# http://andrewsteele.co.uk/mmcalc/\n')
	f.write('#\n')
	#write the metadata
	for key in meta:
		f.write('# '+str(key)+'='+str(meta[key])+'\n')
	f.write('# datetime='+datetime.datetime.now().strftime("%Y-%m-%d %H:%M")+'\n')
	#column titles
	columns = ''
	for property in properties:
		columns += (property+'\t')
	columns = columns[:-1]+'\n'
	f.write(columns)	
	return f

def write(title,properties,attr,filename):
	global version
	f=begin(title,properties,filename)
	#then numbers...
	for i in range(len(attr)):
		append(attr[i],f)
	f.close()
	return True
	
def append(attr,file):
	cscline=''
	for j in range(len(attr)):
		cscline+=str(attr[j])+'\t'
	#remove extra tab, add line break
	cscline=cscline[:-1]+'\n'
	file.write(cscline)
	return True

def vector_update(dict,vname,vkey,val,dim=3):
	if not dict.has_key(vname):
		dict[vname] = numpy.zeros(dim,numpy.float)
	dict[vname][vkey] = numpy.float(val)
	return dict

def read(filename):
	f=open(filename, 'r')
	values = []
	error = []
	properties = False
	i = 1
	for line in f:
		#if the first character isn't a hash, which implies comment
		if(line[0] != '#'):
			#discard the \n and/or \r characters
			line = line.replace('\r','').replace('\n','')
			#explode it by tabs to separate position and properties
			line=line.split('\t')
			#first line should be a tab-separated list of property names
			if properties is False:
				properties = line
			else:
				if len(line) == len(properties):
					line_values = {}
					for i in range(len(properties)):
						if properties[i] == 'r_x':
							line_values = vector_update(line_values,'r',0,line[i])
						elif properties[i] == 'r_y':
							line_values = vector_update(line_values,'r',1,line[i])
						elif properties[i] == 'r_z':
							line_values = vector_update(line_values,'r',2,line[i])
						elif properties[i] == 'u_x':
							line_values = vector_update(line_values,'u',0,line[i])
						elif properties[i] == 'u_y':
							line_values = vector_update(line_values,'u',1,line[i])
						elif properties[i] == 'u_z':
							line_values = vector_update(line_values,'u',2,line[i])
						elif properties[i] == 'mu_x':
							line_values = vector_update(line_values,'m',0,line[i])
						elif properties[i] == 'mu_y':
							line_values = vector_update(line_values,'m',1,line[i])
						elif properties[i] == 'mu_z':
							line_values = vector_update(line_values,'m',2,line[i])
						elif properties[i] == 'B_x':
							line_values = vector_update(line_values,'B',0,line[i])
						elif properties[i] == 'B_y':
							line_values = vector_update(line_values,'B',1,line[i])
						elif properties[i] == 'B_z':
							line_values = vector_update(line_values,'B',2,line[i])
						elif properties[i] == 'q':
							line_values['q'] = numpy.int(line[i])
						elif properties[i] == 'omega':
							line_values['omega'] = numpy.float(line[i])
						#anything else just outputs a string; this includes element name
						else:
							line_values[properties[i]] = line[i]
						values.append(line_values)
				else:
					error.append('Wrong number of values on line '+str(i)+' (expecting '+str(len(properties))+', received '+str(len(line))+')')
		elif line[0:len('# title=')] == '# title=':
			title = line[len('# title='):-1] #ie everything after = but before \n
		i += 1
	return title,values,error