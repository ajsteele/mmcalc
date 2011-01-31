# coding=utf-8

# VERSION 1.0.development
#global variable for MmCalc version number
# 999 - currently doesn't work in imported modules...what is the standard way to get around this?
version = '1.0.dev'

#this code is commented with markers for things which need improving/would be nice. Simply search for the numbers.
# 999 - need
# 998 - would be nice

# I've never experienced any problems importing these standard Python modules
import os
import platform
import time

import ui
import langen as lang

# numpy needs to be installed
# 998 - should this try to import Numeric? Does that work too?
try:
	import numpy as np
except:
	ui.fatalerror("Error importing Numeric Python module. Please make sure the module 'numpy' is installed. See http://numpy.scipy.org/")

# JSON support is only built-in by default after Python 2.6
try:
	import simplejson as json
except ImportError:
	try:
		import json 
	except:
		ui.fatalerror("Error importing JSON module. If you are using Python < 2.6, install the module 'simplejson' and try again. Python 2.6+ and 3.0+ should include the 'json' module as standard.")

# these modules are all part of the program so should just work...
import sg
import difn
import difast
import didraw
import csc
#to export drawings into http://vpython.org/contents/contributed.html
import povexport

ui.clear()

#global variables for the visualisation window
visual_window = None
visual_window_contents = None

# JSON is not able to serialise complex number objects. These custom functions change any errant complex numbers into a JSON-friendly dictionary.
def complex_serialise(a):
	if a.__class__.__name__ == 'dict': #if it's a Python dictionary, do this function on all sub-elements thereof
		for key in iter(a):
			a[key] = complex_serialise(a[key])
	elif  a.__class__.__name__ == 'list':
		for i in range(len(a)):
			a[i] = complex_serialise(a[i])
	elif a.__class__.__name__ == 'complex': #if it's a complex number, turn it into a JSON-friendly dictionary
		a = {'__complex__':True,'real':np.float(np.real(a)),'imag':np.float(np.imag(a))}
	return a

def complex_unserialise(a):
	if a.__class__.__name__ == 'dict' and '__complex__' in a:
		a = a['real'] + a['imag']*1.0j
	elif a.__class__.__name__ == 'dict': #if it's a Python dictionary, do this function on all sub-elements thereof
		for key in iter(a):
			a[key] = complex_unserialise(a[key])
	elif  a.__class__.__name__ == 'list':
		for i in range(len(a)):
			a[i] = complex_unserialise(a[i])
	return a

def json_custom_save(filename,stuff):
	f = open(filename, 'w')
	json.dump(complex_serialise(stuff),f,indent=4)
	f.close()
	return stuff

def json_custom_load(filename):
	f = open(filename, 'r')
	stuff = json.load(f)
	f.close()
	return complex_unserialise(stuff)

def save_current(variablename,stuff):
	json_custom_save("current/"+variablename+'.json',stuff)

def load_current(variablename):
	#check if the file exists
	if os.path.exists("current/"+variablename+'.json'):
		stuff = json_custom_load("current/"+variablename+'.json')
		return stuff
	#if not, just return a blank dictionary
	else:
		return {}

def save_output(dictname,filetypedesc,directory,suffix,returnto):
	data = load_current(dictname)
	title = ui.inputscreen('Please enter a title for your '+filetypedesc+' file:','str',notblank=True)
	data['title'] = title
	while True:
		filename = ui.inputscreen('Please enter a filename for your '+filetypedesc+' file:','str',notblank=True)
		full_filename = directory+'/'+filename+suffix+'.json'
		if os.path.exists(full_filename):
			if ui.inputscreen('File \''+full_filename+'\' exists. Overwrite?','yn') == 'yes':
				json_custom_save(full_filename,data)
				break
		else:
			json_custom_save(full_filename,data)
			break
	return returnto
	
def load_output(dictname,filetypedesc,directory,suffix,returnto):
	if ui.inputscreen('Do you wish to unload current '+filetypedesc+'?','yn') == 'yes':
		error = ''
		while True:
			filename = ui.inputscreen('Enter '+filetypedesc+' filename to load:','str',notblank=True,text=error)
			full_filename = directory+'/'+filename+suffix+'.json'
			if os.path.exists(full_filename):
				data = json_custom_load(full_filename)
				save_current(dictname,data)
				break
			else:
				error = lang.red+'File '+full_filename+' does not exist.'+lang.reset
	return returnto

def update_value(dictionaryname, key, value):
	#read in the old stuff
	data = load_current(dictionaryname)
	data[key] = value
	#overwrite old with new
	save_current(dictionaryname,data)

def option_toggle(dictionaryname,key,goto):
	data = load_current("draw")
	if data[key]:
		a = False
	else:
		a = True
	update_value(dictionaryname,key,a)
	return goto

def get_csc(directory,suffix,default_filename,file_description=''):
	errtext=''
	while True:
		filename = ui.get_filename(directory,suffix,default_filename,file_description=file_description)
		title,values,error = csc.read(directory+'/'+filename+suffix)
		if error == []:
			return filename,title,values
		else:
			errtext = str(error)

def main_menu():
	return ui.menu([
	['c','crystal structure',crystal,''],
	['d','dipole field calculations',dipole,''],
	['v','visualisation',draw,''],
	['h','help',muhelp,''],
	['q','quit',ui.quit,'']
	])

def crystal():
	#read in crystal temp file
	crystal_data = load_current("crystal")
	#stuff to append to menu items if it's set
	menu_data = {}
	if crystal_data.has_key('spacegroup'):
		menu_data['spacegroup'] = lang.grey + crystal_data['spacegroup'] + lang.reset
	else:
		menu_data['spacegroup'] = ''
	if crystal_data.has_key('length_unit'):
		if crystal_data['length_unit'] == 'n':
			menu_data['length_unit'] = 'nm'
		elif crystal_data['length_unit'] == 'm':
			menu_data['length_unit'] = 'm'
		elif crystal_data['length_unit'] == 'a':
			menu_data['length_unit'] = lang.angstrom
		menu_data['length_unit'] = lang.grey + menu_data['length_unit'] + lang.reset
		menu_data['length_unit_forabc'] = menu_data['length_unit']
	else:
		menu_data['length_unit_forabc'] = 'units'
		menu_data['length_unit'] = lang.red+'not set'+lang.reset
		
	for i in ['a','b','c']:
		if crystal_data.has_key(i):
			menu_data[i] = lang.grey + '= ' + str(crystal_data[i]) + ' ' + menu_data['length_unit_forabc'] + lang.reset
		else:
			menu_data[i] = lang.red + 'not set' + lang.reset
	for i in ['alpha','beta','gamma']:
		if crystal_data.has_key(i):
			menu_data[i] = lang.grey + '= ' + str(crystal_data[i]) + lang.degree + lang.reset
		else:
			menu_data[i] = lang.red + 'not set' + lang.reset
	if crystal_data.has_key('space_group'):
		menu_data['space_group'] = lang.grey + crystal_data['space_group_name'] + ', #' + str(crystal_data['space_group'])
		if crystal_data['space_group_setting'] != '':
			menu_data['space_group'] += ' ['+crystal_data['space_group_setting']+']'
		menu_data['space_group'] += lang.reset
	else:
		menu_data['space_group'] = lang.red + 'not set' + lang.reset
	if crystal_data.has_key('atoms') and len(crystal_data['atoms']) > 0:
		menu_data['atoms'] = lang.grey
		for atom in crystal_data['atoms']:
			menu_data['atoms'] += atom[0]+', '
		menu_data['atoms'] = menu_data['atoms'][:-2] + lang.reset
	else:
		menu_data['atoms'] = lang.red + 'not set' + lang.reset
	#the menu
	return ui.menu([
	['s','space group',space_group,menu_data['space_group']],
	['u','length unit',length_unit,menu_data['length_unit']],
	['a','a',a,menu_data['a']],
	['b','b',b,menu_data['b']],
	['c','c',c,menu_data['c']],
	['1','alpha',alpha,menu_data['alpha']],
	['2','beta',beta,menu_data['beta']],
	['3','gamma',gamma,menu_data['gamma']],
	['t','atoms',atoms_menu,menu_data['atoms']],
	['m','magnetic properties',magnetic_properties_menu,''],
	['d','draw crystal',draw_crystal,''],
	['v','save crystal',save_crystal,''],
	['l','load crystal',load_crystal,''],
	['q','back to main menu',main_menu,'']
	])

def crystal_length(axis):
	crystal_data = load_current("crystal")
	if crystal_data.has_key('length_unit'):
		if crystal_data['length_unit'] == 'n':
			length_unit = 'nm'
		elif crystal_data['length_unit'] == 'm':
			length_unit = 'm'
		elif crystal_data['length_unit'] == 'a':
			length_unit = lang.angstrom
	else:
		length_unit = lang.red+'length unit not defined'+lang.reset
	a = ui.inputscreen('Type length of '+axis+' ('+length_unit+'):','float',0,eqmin=False)
	if a is not False:
		update_value('crystal',axis,a)
	return crystal

def a():
	return crystal_length('a')

def b():
	return crystal_length('b')

def c():
	return crystal_length('c')

def length_unit():
	error=''
	while 1:
		a = ui.option([
		['n','nm',False,'nanometre'],
		['m','m',False,'metre'],
		['a',lang.angstrom,False,'angstrom']
		])
		#if it's blank, just go to the previous menu
		if a == '':
			return crystal
		else:
			update_value('crystal','length_unit',a)
			return crystal
	
def crystal_angle(angle):
	#998 more complex constraints based on space group?
	a = ui.inputscreen('Type value of '+angle+' ('+lang.degree+'): ','float',0,360,False,False)
	if a is not False:
		update_value('crystal',angle,a)
	return crystal

def alpha():
	return crystal_angle('alpha')

def beta():
	return crystal_angle('beta')

def gamma():
	return crystal_angle('gamma')

def sg_validate(a):
	#if it's an integer
	try:
		a = np.int(a)
		int = True
	except: 
		int = False
	if int:
		if a <= 230 and a > 0:
			return True,a
		else:
			return False,'Please enter a number between 1 and 230, or a valid space group in international notation eg P1, P2/m, Cm, P42/n, Fd-3m...'
	else:
		if sg.get_sg(a) is not False:
			return True,a
		else:
			return False,ui.wrap(a + ' is not a valid space group in international notation. Enter a valid space group eg P1, P2/m, Cm, P42/n, Fd-3m... or a number between 1 and 230.',ui.width)

def choose_setting(spacegroups):
	error=''
	while 1:
		spacegroups_menu = []
		i = 1
		for spacegroup in spacegroups:
			spacegroups_menu.append([str(i),spacegroup['setting'],False,''])
			i+= 1
		return np.int(ui.option(spacegroups_menu,True))

def space_group():
	a = ui.inputscreen('Type a space group name or number:',validate=sg_validate)
	if a is not False:
		#turn it into a space group name and number
		a = sg.get_sg(a)
		if len(a) > 1:
			setting = choose_setting(a)
		else:
			setting = 1
		update_value('crystal','space_group',a[setting-1]['number'])
		update_value('crystal','space_group_name',a[setting-1]['name'])
		update_value('crystal','space_group_setting',a[setting-1]['setting'])
	return crystal

def atoms_table():
	#load (and print out) any already-existent atom data
	crystal_data = load_current('crystal')
	if crystal_data.has_key('atoms'):
		atoms = crystal_data['atoms']
		atoms_table_array = []
		atoms_table_array.append(['#','element','x','y','z','q'])
		i = 1
		for atom in atoms:
			atom_row = []
			atom_row.append(str(i))
			for property in atom:
				atom_row.append(str(property))
			atoms_table_array.append(atom_row)
			i += 1
		return ui.table(atoms_table_array)
	else:
		return ''

def atoms_menu():
	crystal_data = load_current('crystal')
	#if there are atoms
	if crystal_data.has_key('atoms') and len(crystal_data['atoms']) != 0:
		return ui.menu([
		['a','add atom',add_atom,''],
		['d','delete atom',delete_atom,''],
		['e','edit atom',edit_atom,''],
		['q','back to crystal menu',crystal,'']
		],atoms_table())
	#if none has been set yet
	else:
		return ui.menu([
		['a','add atom',add_atom,''],
		['q','back to crystal menu',crystal,'']
		])

def add_atom():
	newatom=[]
	#998 make a way to get these all on one screen
	newatom.append(ui.inputscreen('                     element:','string',notblank=True))
	newatom.append(ui.inputscreen('  x (fractional coordinates):','float',0,1,notblank=True))
	newatom.append(ui.inputscreen('  y (fractional coordinates):','float',0,1,notblank=True))
	newatom.append(ui.inputscreen('  z (fractional coordinates):','float',0,1,notblank=True))
	newatom.append(ui.inputscreen('                     q (|e|):','int',notblank=True))
	#load the old atoms
	crystal_data = load_current('crystal')
	if crystal_data.has_key('atoms'):
		atoms = crystal_data['atoms']
	else:
		atoms = []
	atoms.append(newatom)
	update_value('crystal','atoms',atoms)
	return atoms_menu

def delete_atom():
	crystal_data = load_current('crystal')
	atoms = crystal_data['atoms']
	atoms_data = atoms_table()
	if len(atoms) > 1:
		query = 'Delete which atom? (1-'+str(len(atoms))+', blank to cancel)'
	else:
		query =  'There is only one atom. Enter 1 to confirm deletion, or leave blank to cancel:'
	kill_me = ui.inputscreen(query,'int',1,len(atoms))
	if kill_me is not False:
		del atoms[kill_me-1]
		update_value('crystal','atoms',atoms)
	return atoms_menu

def edit_atom():
	crystal_data = load_current('crystal')
	atoms = crystal_data['atoms']
	atoms_data = atoms_table()
	if len(atoms) > 1:
		query = 'Edit which atom? (1-'+str(len(atoms))+')'
		edit_me = ui.inputscreen(query,'int',1,len(atoms))
	else:
		edit_me = 1
	atom = []
	#998 make a way to get these all on one screen
	atom.append(ui.inputscreen('    element (blank for '+str(atoms[edit_me-1][0])+'):','string'))
	atom.append(ui.inputscreen('          x (blank for '+str(atoms[edit_me-1][1])+'):','float',0,1))
	atom.append(ui.inputscreen('          y (blank for '+str(atoms[edit_me-1][2])+'):','float',0,1))
	atom.append(ui.inputscreen('          z (blank for '+str(atoms[edit_me-1][3])+'):','float',0,1))
	atom.append(ui.inputscreen('       q (e) (blank for '+str(atoms[edit_me-1][4])+'):','int'))
	for i in range(len(atom)):
		if atom[i] is not False:
			atoms[edit_me-1][i] = atom[i]
	update_value('crystal','atoms',atoms)
	return atoms_menu

def vector_table(vectors_name, vectors,offset=0):
	table_array=[]
	#table_array.append([lang.bold+vectors_name+lang.reset,'#',vectors_name+'_x',vectors_name+'_y',vectors_name+'_z'])
	#998 make table cell width recognise control characters
	table_array.append([vectors_name,vectors_name+'_x',vectors_name+'_y',vectors_name+'_z'])
	i = offset+1
	for vector in vectors:
		row = []
		row.append(str(i))
		for component in vector:
			row.append(str(component))
		table_array.append(row)
		i += 1
	return ui.table(table_array)

def generated_atoms_table(crystal_data):
	#load (and print out) any already-existent atom data
	if crystal_data.has_key('generated_atoms'):
		atoms = crystal_data['generated_atoms']
		properties = crystal_data['generated_atoms_properties']
		atoms_table_array = []
		atoms_table_array.append(['#','element','x','y','z','q','m','k']) #lang.bold+'m'+lang.reset,lang.bold+'k'+lang.reset]) #it would be nice to make this bold, but the column length counter doesn't ignore control codes at the moment so they just appear as ellipses
		for i in range(len(crystal_data['generated_atoms'])):
			atom_row = []
			atom_row.append(str(i+1))
			for property in crystal_data['generated_atoms'][i]:
				atom_row.append(str(property))
			for property in properties[i]:
				atom_row.append(str(property))
			atoms_table_array.append(atom_row)
			i += 1
		return ui.table(atoms_table_array)
	else:
		return ''

def generate_atoms():
	crystal_data = load_current('crystal')
	r_in = []
	attr_in = []
	for atom in crystal_data['atoms']:
		r_in.append([atom[1],atom[2],atom[3]])
		attr_in.append([atom[0],atom[4]])
	# generate and save unit cell data
	r, attr = sg.gen_unit_cell({'number':crystal_data['space_group'],'setting':crystal_data['space_group_setting']},r_in, attr_in)
	crystal_data['generated_atoms'] = []
	for i in range(len(r)):
		crystal_data['generated_atoms'].append([attr[i][0],r[i][0],r[i][1],r[i][2],attr[i][1]])
	update_value('crystal','generated_atoms',crystal_data['generated_atoms'])
	if crystal_data.has_key('generated_atoms_properties') and len(crystal_data['generated_atoms_properties']) != 0:
		#if there are more or the same number of atoms, leave it be, but if fewer pad with zeros
		if len(crystal_data['generated_atoms_properties']) <= len(crystal_data['generated_atoms']):
			for i in range(len(crystal_data['generated_atoms'])-len(crystal_data['generated_atoms_properties'])):
				crystal_data['generated_atoms_properties'].append([[],[]])
	#create blank generated atom properties
	else:
		crystal_data['generated_atoms_properties'] = []
		for i in range(len(crystal_data['generated_atoms'])):
			crystal_data['generated_atoms_properties'].append([[],[]])
	update_value('crystal','generated_atoms',crystal_data['generated_atoms'])
	update_value('crystal','generated_atoms_properties',crystal_data['generated_atoms_properties'])
	return load_current('crystal')


def magnetic_properties_menu():
	crystal_data = load_current('crystal')
	menu_options = []
	menu_data = ''
	menu_options.append(['m','add basis vector '+lang.bold+'m'+lang.reset,add_m,''])
	menu_options.append(['k','add propagation vector '+lang.bold+'k'+lang.reset,add_k,''])
	if crystal_data.has_key('m') and len(crystal_data['m']) != 0:
		menu_data += ui.heading('m vectors')
		menu_data += vector_table('m',crystal_data['m'])
	if crystal_data.has_key('k') and len(crystal_data['k']) != 0:
		menu_data += ui.heading('k vectors')
		menu_data += vector_table('k',crystal_data['k'],len(crystal_data['m']))
	if menu_data != '': #if there's menu data, at least some m and k must be set, so add options to change or delete
		menu_options.append(['d','delete vector',delete_m_or_k,''])
		menu_options.append(['v','edit vector',edit_m_or_k,''])
	#if there are atoms and a space group
	if crystal_data.has_key('atoms') and len(crystal_data['atoms']) != 0 and crystal_data.has_key('space_group'):
		crystal_data = generate_atoms()
		menu_data += ui.heading('atoms')
		menu_data += generated_atoms_table(crystal_data)
		#only allow them to give atoms ms and ks if at least one of each has been defined
		if crystal_data.has_key('m') and len(crystal_data['m']) != 0 and crystal_data.has_key('k') and len(crystal_data['k']) != 0:
			menu_options.append(['t','edit atom '+lang.bold+'m'+lang.reset+' and '+lang.bold+'k'+lang.reset,edit_atom_m_and_k,''])
			menu_options.append(['x','clear atom '+lang.bold+'m'+lang.reset+' and '+lang.bold+'k'+lang.reset,clear_atom_m_and_k,''])
	else:
		#if one hasn't been defined, find out which (or both)...
		if crystal_data.has_key('atoms') and len(crystal_data['atoms']) != 0:
			menu_data += lang.newline+lang.red+'You need to define a space group.'+lang.reset
		elif crystal_data.has_key('space_group'):
			menu_data += lang.newline+lang.red+'You need to define some atoms.'+lang.reset
		else:
			menu_data += lang.newline+lang.red+'You need to define some atoms and a space group.'+lang.reset
	menu_options.append(['q','back to crystal menu',crystal,''])
	return ui.menu(menu_options,menu_data)
	
def edit_generated_atoms():
	pass

def add_m():
	newm=[]
	#998 make a way to get these all on one screen
	newm.append(ui.inputscreen('  m_x (units of µ_B, complex):','complex',notblank=True))
	newm.append(ui.inputscreen('  m_y (units of µ_B, complex):','complex',notblank=True))
	newm.append(ui.inputscreen('  m_z (units of µ_B, complex):','complex',notblank=True))
	#load the old atoms
	crystal_data = load_current('crystal')
	if crystal_data.has_key('m'):
		m = crystal_data['m']
	else:
		m = []
	m.append(newm)
	update_value('crystal','m',m)
	return magnetic_properties_menu
	
def add_k():
	newk=[]
	#998 make a way to get these all on one screen
	#is it always true that |k|/pi <= 0.5 because it should be in the first BZ?
	newk.append(ui.inputscreen('    k_x/2π:','complex',notblank=True))
	newk.append(ui.inputscreen('    k_y/2π:','complex',notblank=True))
	newk.append(ui.inputscreen('    k_z/2π:','complex',notblank=True))
	#load the old atoms
	crystal_data = load_current('crystal')
	if crystal_data.has_key('k'):
		k = crystal_data['k']
	else:
		k = []
	k.append(newk)
	update_value('crystal','k',k)
	return magnetic_properties_menu

def delete_m_or_k():
	crystal_data = load_current('crystal')
	menu_data = ''
	if crystal_data.has_key('m') and len(crystal_data['m']) != 0:
		m = crystal_data['m']
		menu_data += ui.heading('m vectors')
		menu_data += vector_table('m',crystal_data['m'])
	else:
		m = []
	if crystal_data.has_key('k') and len(crystal_data['k']) != 0:
		k = crystal_data['k']
		menu_data += ui.heading('k vectors')
		menu_data += vector_table('k',crystal_data['k'],len(crystal_data['m']))
	else:
		k = []
	if len(m)+len(k) > 1:
		query = 'Delete which vector? (1-'+str(len(m) + len(k))+', blank to cancel)'
	else:
		query =  'There is only one vector. Enter 1 to confirm deletion, or leave blank to cancel:'
	kill_me = ui.inputscreen(query,'int',1,len(m) + len(k),text=menu_data)
	if kill_me is not False:
		if kill_me <= len(m):
			del m[kill_me-1]
			update_value('crystal','m',m)
		else:
			del k[kill_me-len(m)-1]
			update_value('crystal','k',k)
	return magnetic_properties_menu

def edit_m_or_k():
	crystal_data = load_current('crystal')
	menu_data = ''
	if crystal_data.has_key('m') and len(crystal_data['m']) != 0:
		m = crystal_data['m']
		menu_data += ui.heading('m vectors')
		menu_data += vector_table('m',crystal_data['m'])
	else:
		m = []
	if crystal_data.has_key('k') and len(crystal_data['k']) != 0:
		k = crystal_data['k']
		menu_data += ui.heading('k vectors')
		menu_data += vector_table('k',crystal_data['k'],len(crystal_data['m']))
	else:
		k = []
	if len(m)+len(k) > 1:
		query = 'Edit which vector? (1-'+str(len(m) + len(k))+', blank to cancel)'
		edit_me = ui.inputscreen(query,'int',1,len(m) + len(k),text=menu_data)
	else:
		edit_me = 1
	if edit_me is not False:
		if edit_me <= len(m):
			newm = []
			newm.append(ui.inputscreen('  m_x (blank for '+str(m[edit_me-1][0])+'):','complex'))
			newm.append(ui.inputscreen('  m_y (blank for '+str(m[edit_me-1][1])+'):','complex'))
			newm.append(ui.inputscreen('  m_z (blank for '+str(m[edit_me-1][2])+'):','complex'))
			for i in range(len(newm)):
				if newm[i] is not False:
					m[edit_me-1][i] = newm[i]
			update_value('crystal','m',m)
		else:
			newk = []
			newk.append(ui.inputscreen('    k_x/π (blank for '+str(k[edit_me-len(m)-1][0])+'):','complex'))
			newk.append(ui.inputscreen('    k_y/π (blank for '+str(k[edit_me-len(m)-1][1])+'):','complex'))
			newk.append(ui.inputscreen('    k_z/π (blank for '+str(k[edit_me-len(m)-1][2])+'):','complex'))
			for i in range(len(newk)):
				if newk[i] is not False:
					k[edit_me-len(m)-1][i] = newk[i]
			update_value('crystal','k',k)
	return magnetic_properties_menu

def edit_atom_m_and_k():
	crystal_data = load_current('crystal')
	generated_atoms_properties = crystal_data['generated_atoms_properties']
	generated_atoms = crystal_data['generated_atoms']
	for i in range(len(generated_atoms)):
		print i,generated_atoms[i]
	m = crystal_data['m']
	k = crystal_data['k']
	#if there's more than one atom, allow the user to choose it
	if len(generated_atoms) > 1:
		menu_data = ''
		menu_data += ui.heading('atoms')
		menu_data += generated_atoms_table(crystal_data)
		query = 'Edit which atom? (1-'+str(len(generated_atoms))+', blank to cancel)'
		edit_me = ui.inputscreen(query,'int',1,len(generated_atoms),text=menu_data)
	#otherwise, allow them to edit the only existent atom by default
	else:
		edit_me = 1
	#the actual internal array starts at zero, so subtract the offset
	edit_me -= 1
	if edit_me is not False:
		extrainfo = ''
		menu_data = ui.heading('m vectors')
		menu_data += vector_table('m',crystal_data['m'])
		menu_data += ui.heading('k vectors')
		menu_data += vector_table('k',crystal_data['k'],len(crystal_data['m']))
		if len(generated_atoms_properties[edit_me][0]) > 0:
			extrainfo =  ' (blank for '+','.join(map(str, generated_atoms_properties[edit_me][0]))+')'
			notblank = False
		else:
			notblank = True
		newmlist = ui.inputscreen('  Enter a comma-separated list of m vectors'+extrainfo+':','intlist',1,len(m),notblank=notblank,text=menu_data)
		if newmlist == False: #if they didn't enter anything, revert to the previous list
			newmlist = generated_atoms_properties[edit_me][0]
		if len(generated_atoms_properties[edit_me][1]) > 0:
			#if the previous list is the same length as a the new m list, they're allowed to carry it over
			if len(newmlist) == len(generated_atoms_properties[edit_me][1]):
				extrainfo =  ' (enter '+str(len(newmlist))+' values, or blank for '+','.join(map(str, generated_atoms_properties[edit_me][1]))+')'
				notblank = False
			else: #otherwise, they're not allowed the old values
				extrainfo =  ' (enter '+str(len(newmlist))+' values)'
				notblank = True
		else:
			extrainfo =  ' (enter '+str(len(newmlist))+' values)'
			notblank = True
		newklist = ui.inputscreen('  Enter a comma-separated list of k vectors'+extrainfo+':','intlist',len(m)+1,len(m)+len(k),number=len(newmlist),notblank=notblank,text=menu_data)
		#newmlist is never false because it gets updated to the old values if it is
		generated_atoms_properties[edit_me][0] = newmlist
		if newklist is not False:
			generated_atoms_properties[edit_me][1] = newklist
		update_value('crystal','generated_atoms_properties',generated_atoms_properties)
	return magnetic_properties_menu

#998 add features to not show atoms without magnetic properties in the list, and to not even show this as a menu item if there aren't any...
def clear_atom_m_and_k():
	crystal_data = load_current('crystal')
	generated_atoms_properties = crystal_data['generated_atoms_properties']
	generated_atoms = crystal_data['generated_atoms']
	#if there's more than one atom, allow the user to choose it
	if len(generated_atoms) > 1:
		menu_data = ''
		menu_data += ui.heading('atoms')
		menu_data += generated_atoms_table(crystal_data)
		query = 'Clear magnetic properties of which atom? (1-'+str(len(generated_atoms))+', blank to cancel)'
	#otherwise, allow them to edit the only existent atom by default
	else:
		query = 'There is only one atom. Enter 1 to clear its properties, or blank to cancel'
	clear_me = ui.inputscreen(query,'int',1,len(generated_atoms),text=menu_data)
	#the actual internal array starts at zero, so subtract the offset
	clear_me -= 1
	if clear_me is not False:
		generated_atoms_properties[clear_me][0] = []
		generated_atoms_properties[clear_me][1] = []
		update_value('crystal','generated_atoms_properties',generated_atoms_properties)
	return magnetic_properties_menu

#the converts the stored values in the dict to something processable
def stored_unit_cell():
	crystal_data = generate_atoms()
	#get appropriate multiplier for nanometres, angstroms, metres
	if crystal_data['length_unit'] == 'n':
		unit = difn.nano
	elif crystal_data['length_unit'] == 'a':
		unit = difn.angstrom
	else:
		unit = 1.0
	a = np.array([crystal_data['a'],crystal_data['b'],crystal_data['c']],np.float)*unit
	alpha = np.array([crystal_data['alpha'],crystal_data['beta'],crystal_data['gamma']],np.float)
	a_cart = difn.triclinic([crystal_data['a'],crystal_data['b'],crystal_data['c']],np.array([crystal_data['alpha'],crystal_data['beta'],crystal_data['gamma']]))*unit
	r_atoms = []
	q_atoms = []
	m_atoms = []
	k_atoms = []
	name_atoms = []
	for i in range(len(crystal_data['generated_atoms'])):
		r_atoms.append(np.array([crystal_data['generated_atoms'][i][1],crystal_data['generated_atoms'][i][2],crystal_data['generated_atoms'][i][3]]))
		q_atoms.append(crystal_data['generated_atoms'][i][4])
		#if there are m- and k-vectors specified, go through the list and work out which ones
		atom_ms = []
		atom_ks = []
		if len(crystal_data['generated_atoms_properties'][i][0]) > 0:
			for j in range(len(crystal_data['generated_atoms_properties'][i][0])):
				atom_ms.append(np.array(crystal_data['m'][crystal_data['generated_atoms_properties'][i][0][j]-1],np.complex)*difn.mu_B)
				atom_ks.append(np.array(crystal_data['k'][crystal_data['generated_atoms_properties'][i][1][j]-1-len(crystal_data['m'])],np.complex)) #subtract length of array of ms because ks are stored with indices starting from len(m)+1
		else: #if there aren't any, just set these to false so they can be discarded if not needed
			atom_ms = False
			atom_ks = False
		m_atoms.append(atom_ms)
		k_atoms.append(atom_ks)
		name_atoms.append(crystal_data['generated_atoms'][i][0])
	#get all the used k vectors 999 add this
	#~ for i in range(len(crystal_data['generated_atoms']['k'])):
		#~ crystal_data['generated_atoms']['k'][i]
	return a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms

############################
# Commands on the drawing menu #
############################

def draw_crystal():
	crystal_data = load_current('crystal')
	#check that everything is defined as necessary
	#998 might be nice to be able to draw the unit cell without definining magnetic properties
	if crystal_data.has_key('generated_atoms') and len(crystal_data['generated_atoms']) > 0 and len(crystal_data['generated_atoms_properties']) >= len(crystal_data['generated_atoms']):
		#check the magnetic unit cell isn't too big--if it is, limit size to 10x10x10
		return ui.menu([
		['c','draw crystallographic unit cell',draw_crystal_unit_cell,''],
		['m','draw magnetic unit cell',draw_magnetic_unit_cell_from_crystal,''],
		#['o','choose origin',draw_origin],
		['q','back to crystal menu',crystal,'']
		])
	else:
		return ui.menu([	['q','back to crystal menu',crystal,'']],
		'You need to fully specify your crystal structure and magnetic properties before you can visit this menu')

def draw_crystal_unit_cell():
	global visual_window
	global visual_window_contents
	crystal_data = generate_atoms()
	draw_data = load_current('draw')
	#get appropriate multiplier for nanometres, angstroms, metres
	if crystal_data['length_unit'] == 'n':
		unit = difn.nano
	elif crystal_data['length_unit'] == 'a':
		unit = difn.angstrom
	else:
		unit = 1.0
	a = difn.triclinic([crystal_data['a'],crystal_data['b'],crystal_data['c']],np.array([crystal_data['alpha'],crystal_data['beta'],crystal_data['gamma']]))*unit
	scale = draw_default_scale()
	if(visual_window is None):
		visual_window = didraw.initialise('nostereo')
	else:
		visual_window_contents = didraw.hide(visual_window_contents)
		del visual_window_contents
		visual_window_contents = None
	#set the centre to be in the centre of the unit cell
	visual_window.center = ((a[0]+a[1]+a[2])*0.5)
	visual_window.visible = True
	visual_window_contents = {'unitcell':didraw.unitcell_init(a,scale)}
	atoms_r = []
	atoms_attr = []
	for atom in crystal_data['generated_atoms']:
		atoms_attr.append([atom[0],atom[4]])
		atoms_r.append([atom[1],atom[2],atom[3]])
	#if fenceposts...on by default for now 999
	atoms_r,atoms_attr = difn.unit_cell_shared_atoms(atoms_r,atoms_attr)
	#go through the generated atoms...
	atoms_names = []
	for i in range(len(atoms_r)):
		#and give them real cartesian rather than fractional coordinates
		atoms_r[i] = atoms_r[i][0]*a[0]+atoms_r[i][1]*a[1]+atoms_r[i][2]*a[2]
		#and split up the attributes into name, charge etc
		atoms_names.append(atoms_attr[i][0])
	atoms_r = difn.zero_if_close(atoms_r)
	visual_window_contents['atoms'] = didraw.draw_atoms(atoms_r,atoms_names,[],[],'e',scale,{}) #draw completely standard, coloured by element etc, to avoid hiding points
	return draw_crystal

def draw_magnetic_unit_cell():
	global visual_window
	global visual_window_contents
	draw_initialise()
	draw_data = load_current('draw')
	a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
	L = difn.mag_unit_cell_size(k_atoms)
	atoms_r = difn.zero_if_close(r_atoms)
	r_i,q_i,mu_i,names_i = difn.make_para_crystal(a_cart, r_atoms, m_atoms, k_atoms, q_atoms, name_atoms,[0,0,0], L)
	#then delete all atoms outside the magnetic unit cell
	r_i,q_i,mu_i,names_i = difn.make_crystal_trim_para(r_i,q_i,mu_i,names_i,a_cart,L)
	scale = draw_data['scale']
	if(visual_window is None):
		visual_window = didraw.initialise('nostereo')
	else:
		visual_window_contents = didraw.hide(visual_window_contents)
		del visual_window_contents
		visual_window_contents = None
	visual_window.visible = True
	visual_window.center = ((a_cart[0]*L[0]+a_cart[1]*L[1]+a_cart[2]*L[2])*0.5)
	visual_window_contents = {'unitcell':didraw.unitcell_init(a_cart,scale),
	'atoms':didraw.draw_atoms(r_i,names_i,q_i,mu_i,'e',scale,{}), #draw completely standard, coloured by element etc, to avoid hiding points
	'atoms_mu':didraw.vector_field(r_i,mu_i,0,0,'fadetoblack','proportional',scale)}
	update_value('draw','scale',scale)
	
def draw_draw():
	global visual_window
	global visual_window_contents
	draw_data = load_current('draw')
	L =  draw_data['L']
	#turn the array of custom atoms into a usable dictionary
	atom_custom = {}
	if draw_data.has_key('atoms'):
		for atom in draw_data['atoms']:
			if atom[1] == 'yes': #if it's visible
				atom_custom[atom[0]] = {'visible':True,'colour':atom[2],'size_unit':atom[3],'size':atom[4],'opacity':atom[5]}
			else: #if it's invisible
				atom_custom[atom[0]] = {'visible':False}
	a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
	atoms_r = difn.zero_if_close(r_atoms)
	r_i,q_i,mu_i,names_i = difn.make_para_crystal(a_cart, r_atoms, m_atoms, k_atoms, q_atoms, name_atoms,[0,0,0], L)
	#then delete all atoms outside the magnetic unit cell
	r_i,q_i,mu_i,names_i = difn.make_crystal_trim_para(r_i,q_i,mu_i,names_i,a_cart,L)
	scale = draw_data['scale']
	#delete the old 3D window
	if visual_window is not None:
		visual_window.visible = False
		visual_window = None
	del visual_window_contents
	visual_window_contents = None
	#3d settings
	if draw_data['stereo_3d'] == 'r':
		stereo_3d = 'redcyan'
	elif draw_data['stereo_3d'] == 'b':
		stereo_3d = 'redblue'
	elif draw_data['stereo_3d'] == 'y':
		stereo_3d = 'yellowblue'
	else: # = 'n', but turn it off under all other circumstances
		stereo_3d = 'nostereo'
	visual_window = didraw.initialise(stereo_3d)
	visual_window.visible = True
	visual_window.center = ((a_cart[0]*L[0]+a_cart[1]*L[1]+a_cart[2]*L[2])*0.5)
	visual_window_contents = {}
	if draw_data['unitcell']:
		print 'Drawing unit cell boundary...'
		visual_window_contents['unitcell'] = didraw.unitcell_init(a_cart,scale)
	if True: #you can't currently turn off atoms 999
		print 'Drawing atoms...'
		visual_window_contents['atoms']= didraw.draw_atoms(r_i,names_i,q_i,mu_i,draw_data['atom_colours'],scale,atom_custom)
	if draw_data['moments']:
		print 'Drawing magnetic moments...'
		visual_window_contents['atoms_mu'] = didraw.vector_field(r_i,mu_i,0,0,'fadetoblack','proportional',scale)
	#if the field is visible, load it and draw it
	if draw_data['field_visible']:
		print 'Drawing dipole field of ',
		title, values, error = csc.read('output'+'/'+draw_data['field_filename']+'-dipole-field.tsv') #998 do something with error?
		print '\''+title+'\'...'
		r_field,B_field,omega_field = csc_to_dipole_field(values)
		omega_minmax = draw_data['omega_minmax']
		omega_maxmax = 0. #the largest maximum specified
		omega_minmin = 99.999e99 #and the smallest minimum
		for i in range(len(omega_minmax)): #loop through to find them
			omega_minmax[i][0] = omega_minmax[i][0]*1e6 #turn it into Hz while you're at it
			omega_minmax[i][1] = omega_minmax[i][1]*1e6 
			if omega_minmax[i][1] > omega_maxmax:
				omega_maxmax = omega_minmax[i][1]
			if omega_minmax[i][0] < omega_minmin:
				omega_minmin = omega_minmax[i][0]
		#ditch those values outside the drawable range
		B_to_draw = []
		r_to_draw = []
		for i in range(len(r_field)):
			if np.random.random() < 0.1: #999 only draw one per 1/x points at random
				for minmax in omega_minmax:
					if minmax[0] < omega_field[i] and minmax[1] > omega_field[i]:
						B_to_draw.append(B_field[i])
						r_to_draw.append(r_field[i])
		B_minmin = omega_minmin / difn.gamma_mu #convert back to B by dividing by M(Hz) and gyromagnetic ratio
		B_maxmax = omega_maxmax / difn.gamma_mu
		do_draw = True
		if len(r_to_draw) > 100000:
			if ui.inputscreen('Your chosen minimum and maximum values will result in '+str(len(r_to_draw))+' field points being drawn. I strongly suggest you don\'t. Continue?','yn') == 'no':
				do_draw = False #stop drawing the if user doesn't want computer-crippling-ness
			else:
				if ui.inputscreen('Drawing '+str(len(r_to_draw))+' points is REALLY NOT RECOMMENDED. Sure?','yn') == 'no':
					do_draw = False #stop drawing the if user doesn't want computer-crippling-ness
		elif len(r_to_draw) > 10000:
			if ui.inputscreen('Your chosen minimum and maximum values will result in '+str(len(r_to_draw))+' field points being drawn. This may cause your computer to run slowly. Continue?','yn') == 'no':
				do_draw = False #stop drawing the if user doesn't want computer-crippling-ness
		if do_draw:
			visual_window_contents['dipole_field'] = didraw.vector_field(r_to_draw,B_to_draw,B_minmin,B_maxmax,draw_data['field_colours'],0.2,scale)
	
def draw_magnetic_unit_cell_from_crystal():
	draw_magnetic_unit_cell()
	return draw_crystal
	
def save_crystal():
	return save_output('crystal','crystal structure','output','-crystal-structure',crystal)

def load_crystal():
	return load_output('crystal','crystal structure','output','-crystal-structure',crystal)

def dipole():
	dipole_data = load_current('dipole')
	menu_data = {}
	if dipole_data.has_key('r_sphere'):
		menu_data['v_size'] = 'r='+str(dipole_data['r_sphere'])
	else:
		menu_data['v_size'] = lang.red+'not set'+lang.reset
	if dipole_data.has_key('n_a') and dipole_data.has_key('n_b') and dipole_data.has_key('n_c'):
		menu_data['n_points'] = 'n_a='+str(dipole_data['n_a'])+', n_b='+str(dipole_data['n_b'])+', n_c='+str(dipole_data['n_c'])
	else:
		menu_data['n_points'] = lang.red+'not set'+lang.reset
	return ui.menu([
#	['s','vcrystal shape',vcrystal_shape,'only spherical possible at the moment'],	
	['c','convergence test',convergence_test,''],
	['z','vcrystal size',vcrystal_size,menu_data['v_size']],
	['n','number of points',n_points,menu_data['n_points']],
	['e','evaluate dipole field by direct summation',calculate_dipole,''],
	['m','evaluate dipole field near muonophiles',calculate_dipole_near_muonophile,''],
	['s','symmetry eqv',dipole_symmetry_eqv,''], #999
	['d','draw dipole field',draw_dipole,''],
#	['f','draw frequencies',draw_freq,''], #999
	['h','histogram of frequencies',histo_freq,''],
	['q','back to main menu',main_menu,'']
	])

def vcrystal_shape():
	pass #998 add this feature?

#999 check this function actually works!!
def generate_random_position(r,a,tolerance):
	sorted = False
	tolerance2 = tolerance*tolerance
	while sorted != True:
		sorted = True
		r_test = np.random.rand()*a[0]+np.random.rand()*a[1]+np.random.rand()*a[2]
		#print r_test
		for i in range(len(r)):
			#if it's too close to an atom, send it round again
			if np.dot((r_test-r[i]),(r_test-r[i])) < tolerance2:
				#print i,r[i]
				sorted = False
				break
	return r_test

def convergence_test():
	global visual_window
	global visual_window_contents
	t_begin = time.clock()
	draw_data = load_current('draw')
	a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
	#make a 2x2x2 crystal so if it's close to one in an adjacent cell this isn't missed
	r,q,mu,name = difn.make_para_crystal(a_cart, r_atoms, m_atoms, k_atoms, q_atoms, name_atoms,[0,0,0], [1,1,1])
	#trim excess atoms 999
	r_test = np.zeros((10,3),np.float)
	#define how close it's OK to be... 998 how close is it OK to be? Doesn't really matter as long as not on top?
	tolerance = 1e-10 #m
	#pick three random points not too near any atoms
	#998 these are only in the crystal (not magnetic) unit cell, does that matter?
	for i in range(len(r_test)):
		r_test[i] = generate_random_position(r,a_cart,tolerance)
	scale = draw_data['scale']
	if(visual_window is None):
		visual_window = didraw.initialise('nostereo')
	else:
		visual_window_contents = didraw.hide(visual_window_contents)
		del visual_window_contents
		visual_window_contents = None
	visual_window.visible = True
	print 'Drawing magnetic unit cell...'
	visual_window_contents = {
	'unitcell':didraw.unitcell_init(a_cart,scale),
	'atoms':didraw.draw_atoms(r,name,q,mu,'e',scale,{}), #draw completely standard, coloured by element etc, to avoid hiding points
	'points':didraw.points(r_test,scale)
	}
	r_max = 21 #999 user-define
	B = np.zeros((r_max+1,len(r_test),3),np.float)
	omega = np.zeros((r_max+1,len(r_test)),np.float)
	error = np.zeros((r_max+1,len(r_test)),np.float)
	t = np.zeros((r_max+1,len(r_test)),np.float)
	B_perfect = np.zeros((len(r_test),3),np.float)
	omega_perfect = np.zeros((len(r_test)),np.float)
	t_perfect = np.zeros((len(r_test)),np.float)
	#make 'perfect answer'
	radius_perfect = 31 #999 user-define
	print 'Finding reference answer at r = '+str(radius_perfect)+'a...',
	print 'creating vcrystal...',
	#create vcrystal
	L,r,q,mu,name,r_whatisthis = difn.make_crystal(radius_perfect,a,alpha,r_atoms,m_atoms,k_atoms, q_atoms, name_atoms,type='magnetic')
	r_fast = difast.reshape_array(r)
	mu_fast = difast.reshape_array(mu)
	#do dipole fields at the various points
	for i in range(len(r_test)):
		print 'point '+str(i+1)+'...',
		t_start = time.clock()
		r_test_fast = difast.reshape_vector(r_test[i])
		B_perfect = difast.calculate_dipole(r_test_fast, r_fast, mu_fast)
		#B_perfect = difn.calculate_dipole(r_test[i], r, mu) #old function
		t_stop = time.clock()
		omega_perfect[i] = difn.gyro(B_perfect)
		t_perfect[i] = t_stop - t_start
	print ''
	for radius in range(1,r_max):
		print 'Testing r = '+str(radius)+'a...'
		#create vcrystal
		L,r,q,mu,name,r_whatisthis = difn.make_crystal(radius,a,alpha,r_atoms,m_atoms,k_atoms, q_atoms, name_atoms,type='magnetic')
		r_fast = difast.reshape_array(r)
		mu_fast = difast.reshape_array(mu)
		if radius ==10:
			
			if(visual_window is None):
				visual_window = didraw.initialise('nostereo')
			else:
				visual_window_contents = didraw.hide(visual_window_contents)
				del visual_window_contents
				visual_window_contents = None
			visual_window.visible = True
			print 'Drawing vcrystal with r = 10a...'
			visual_window_contents = {
			'unitcell':didraw.unitcell_init(a_cart,scale),
			'atoms':didraw.draw_atoms(r,name,q,mu,'e',scale,{}), #draw completely standard, coloured by element etc, to avoid hiding points
			}
		#do dipole fields at the various points
		for i in range(len(r_test)):
			t_start = time.clock()
			r_test_fast = difast.reshape_vector(r_test[i]) #998 bit inefficient to calculate this every time
			B[radius][i] = difast.calculate_dipole(r_test_fast, r_fast, mu_fast)
			t_stop = time.clock()
			omega[radius][i] = difn.gyro(B[radius][i])
			t[radius][i] = t_stop - t_start
			error[radius][i] = np.abs(np.round((omega[radius][i]-omega_perfect[i])/omega_perfect[i],decimals=4))*100
	table_array = [['radius','error','time for 41x41x41']]
	for radius in range(1,r_max):
		row = [str(radius)]
		sum_t = 0
		sum_err = 0
		for i in range(len(r_test)):
			sum_err += error[radius][i]
			sum_t += t[radius][i]
			print radius,i,(str(B[radius][i]))
		row.append(str(sum_err/np.float(len(r_test)))[:5]+' %')
		row.append(ui.s_to_hms(sum_t*41*41*41/np.float(len(r_test)))) #time for 41x41x41 iterations
		table_array.append(row)
	t_end = time.clock()
	
	return ui.menu([
	['q','back to dipole menu',dipole,'']
	],ui.table(table_array)+'Convergence test completed in '+ui.s_to_hms(t_end-t_begin))
	

def vcrystal_size():
	a = ui.inputscreen('Type radius of virtual crystal sphere (units of a):','int',0,eqmin=False)
	if a is not False:
		update_value('dipole','r_sphere',a)
	return dipole

def n_points():
	dipole_data = load_current('dipole')
	for axis in ['a','b','c']:
		if dipole_data.has_key('n_'+axis):
			a = ui.inputscreen('Number of points on the '+axis+'-axis (blank for '+str(dipole_data['n_'+axis])+'):','int',0,eqmin=False,notblank=False)
		else:
			a = ui.inputscreen('Number of points on the '+axis+'-axis:','int',0,eqmin=False,notblank=True)
		if a is not False:
			update_value('dipole','n_'+axis,a)
	return dipole

def calculate_dipole():
	dipole_data = load_current('dipole')
	#check there's a radius and number of points set
	if dipole_data.has_key('r_sphere') and dipole_data.has_key('n_a') and dipole_data.has_key('n_b') and dipole_data.has_key('n_c'):
		#start the v_meta metadata dictionary
		v_meta = {'title':ui.inputscreen('Please enter a title for your virtual crystal file:','str',notblank=True)}
		v_filename = ui.inputscreen('Please enter a filename for your output files:','str',notblank=True)
		update_value('dipole', 'current_filename', v_filename)
		radius = dipole_data['r_sphere']
		n = [dipole_data['n_a'],dipole_data['n_b'],dipole_data['n_c']]
		a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
		#make the vcrystal
		print 'Creating virtual crystal (r = '+str(radius)+'a)...'
		v_meta['R'] = str(radius)+'a'
		v_meta['shape'] = 'sphere'
		L,r,q,mu,name,r_whatisthis = difn.make_crystal(radius,a,alpha,r_atoms,m_atoms,k_atoms, q_atoms, name_atoms,type='magnetic') #999whatisthis
		#save the vcrystal
		print 'Saving virtual crystal (output/'+v_filename+'-vcrystal.tsv)...'
		attr = []
		for i in range(len(r)):
			attr.append([r[i][0],r[i][1],r[i][2],name[i],mu[i][0],mu[i][1],mu[i][2],q[i]])
		csc_properties = ['r_x','r_y','r_z','element','mu_x','mu_y','mu_z','q']
		csc.write(v_meta,csc_properties,attr,'output/'+v_filename+'-vcrystal.tsv')
		#kill the attributes variable as it may be quite big, and is no longer needed
		del(attr)
		#get the magnetic unit cell size
		L = difn.mag_unit_cell_size(k_atoms)
		#create a file ready to receive the output
		dipole_field_filename =  'output/'+v_filename+'-dipole-field.tsv'
		csc_properties = ['rho_x','rho_y','rho_z','r_x','r_y','r_z','B_x','B_y','B_z','omega']
		d_meta = {'title': v_meta['title'], 'n_a': n[0], 'n_b': n[1], 'n_c': n[2], 'vcrystal': v_filename+'-vcrystal.tsv'}
		file = csc.begin(d_meta,csc_properties,dipole_field_filename)
		#loop over points in that number of unit cells
		print 'Calculating dipole fields...'
		r_fast = difast.reshape_array(r)
		mu_fast = difast.reshape_array(mu)
		t_start = time.clock() 
		for i in range(n[0]):
			r_frac_x = np.float(i)/np.float(n[0]) * L[0]
			r_test_x = r_frac_x * a_cart[0]
			for j in range(n[1]):
				r_frac_y = np.float(j)/np.float(n[1]) * L[1]
				r_test_y = r_frac_y * a_cart[1]
				for k in range(n[2]):
					r_frac_z = np.float(k)/np.float(n[2]) * L[2]
					#print r_frac_x,r_frac_y,r_frac_z
					r_test = r_test_x +r_test_y + r_frac_z * a_cart[2] #don't calculate r_test_z to maximise efficiency...
					#B = difn.calculate_dipole(r_test, r, mu) #the old function
					r_test_fast = difast.reshape_vector(r_test)
					B = difast.calculate_dipole(r_test_fast, r_fast, mu_fast)
					omega = difn.gyro(B)
					#only write to the file if the result is not invalid, caused by being on top of a moment
					if not np.isnan(omega):
						csc.append([r_frac_x,r_frac_y,r_frac_z,r_test[0],r_test[1],r_test[2],B[0],B[1],B[2],omega],file)
			frac_done = np.float(i+1)/(n[0]+1)
			t_elapsed = (time.clock()-t_start)
			t_remain = (1-frac_done)*t_elapsed/frac_done
			print str(round(frac_done*100,1))+'% done in '+ui.s_to_hms(t_elapsed)+'...approximately '+ui.s_to_hms(t_remain)+' remaining'
			final_message = 'Calculation completed in '+ui.s_to_hms(t_elapsed)
	else:
		final_message = 'Please ensure you have set a vcrystal radius and a number of points.'
	return ui.menu([
	['q','back to dipole menu',dipole,'']
	],final_message)

def calculate_dipole_near_muonophile():
	close_min = 1.0e-10**2 #angstroms, for testing
	bond_min = 1.0e-10**2 #angstroms, for testing
	bond_max = 1.2e-10**2 #angstroms, for testing
	bond_element = 'C'
	dipole_data = load_current('dipole')
	if dipole_data.has_key('r_sphere') and dipole_data.has_key('n_a') and dipole_data.has_key('n_b') and dipole_data.has_key('n_c'):
		#start the v_meta metadata dictionary
		v_meta = {'title':ui.inputscreen('Please enter a title for your virtual crystal file:','str',notblank=True)}
		v_filename = ui.inputscreen('Please enter a filename for your output files:','str',notblank=True)
		update_value('dipole', 'current_filename', v_filename)

		print 'Loading crystal structure...'
		#get crystal structure and identify muonophiles
		# import the crystal structure
		a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
		L = difn.mag_unit_cell_size(k_atoms)
		r_atoms = difn.zero_if_close(r_atoms)
		r_unit,q_unit,mu_unit,names_unit = difn.make_para_crystal(a_cart, r_atoms, m_atoms, k_atoms, q_atoms, name_atoms,[0,0,0], L)
		#then delete all atoms outside the magnetic unit cell
		r_unit,q_unit,mu_unit,names_unit = difn.make_crystal_trim_para(r_unit,q_unit,mu_unit,names_unit,a_cart,L)
		r_muonophile = []
		r_other = []
		for i in range(len(r_unit)):
			if names_unit[i] == bond_element:
				r_muonophile.append(r_unit[i])
			else:
				r_other.append(r_unit[i])
		r_unit = difast.reshape_array(r_unit)
		r_muonophile = difast.reshape_array(r_muonophile)
		r_other = difast.reshape_array(r_other)

		radius = dipole_data['r_sphere']
		n = [dipole_data['n_a'],dipole_data['n_b'],dipole_data['n_c']]
		#make the vcrystal
		print 'Creating virtual crystal (r = '+str(radius)+'a)...'
		v_meta['R'] = str(radius)+'a'
		v_meta['shape'] = 'sphere'
		L,r,q,mu,name,r_whatisthis = difn.make_crystal(radius,a,alpha,r_atoms,m_atoms,k_atoms, q_atoms, name_atoms,type='magnetic') #999whatisthis
		#save the vcrystal
		print 'Saving virtual crystal (output/'+v_filename+'-vcrystal.tsv)...'
		attr = []
		for i in range(len(r)):
			attr.append([r[i][0],r[i][1],r[i][2],name[i],mu[i][0],mu[i][1],mu[i][2],q[i]])
		csc_properties = ['r_x','r_y','r_z','element','mu_x','mu_y','mu_z','q']
		csc.write(v_meta,csc_properties,attr,'output/'+v_filename+'-vcrystal.tsv')
		#kill the attributes variable as it may be quite big, and is no longer needed
		del(attr)
		#get the magnetic unit cell size
		L = difn.mag_unit_cell_size(k_atoms)
		#create a file ready to receive the output
		dipole_field_filename =  'output/'+v_filename+'-dipole-field.tsv'
		csc_properties = ['rho_x','rho_y','rho_z','r_x','r_y','r_z','B_x','B_y','B_z','omega']
		d_meta = {'title': v_meta['title'], 'n_a': n[0], 'n_b': n[1], 'n_c': n[2], 'vcrystal': v_filename+'-vcrystal.tsv'}
		file = csc.begin(d_meta,csc_properties,dipole_field_filename)
		#loop over points in that number of unit cells
		print 'Calculating dipole fields...'
		r_fast = difast.reshape_array(r)
		mu_fast = difast.reshape_array(mu)
		
		for i in range(10):
			print 'Generating positions...('+str(i)+'/1)'
			#generate many random positions
			r_frac = np.random.random((1000000,3)) #999 *L somehow!!
			#   10,000,000 seemed to result in RAM issues--near-crashing pagefile usage, and, if a second calculation
			#   was attempted with the same instance of MmCalc, the program would crash with a MemoryError
			#   The fewer times this is done, the faster since this bit is a highly-optimised NumPy loop. Thus,
			#   1,000,000 is the current compromise, and is looped over.
			#convert them to absolute coordinates
			r_dip = np.dot(r_frac,a_cart)
			r_dip = difast.reshape_array(r_dip)
			r_frac = difast.reshape_array(r_frac)
			#then throw away the useles ones
			keep = np.ones(len(r_dip[0]),np.bool) #will the position survive? Start all true...
			#print np.shape(r_dip),np.shape(r_unit),np.shape(r_unit[:,0])
			for i in range(len(r_other[0])):
				r_rel = r_dip-np.reshape(r_other[:,i],(3,1)) #find how far the dipole field point is from all the atoms 998 why does this need reshaping to go from (3,) to (3,1)?
				keep = np.bitwise_and(keep,(np.sum(r_rel*r_rel, 0)>close_min)) #if any of them is closer than near, set this to false to discard. Using bitwise_and means that only continual 'true's will result in an array element not being discarded in a moment
			keep_close = np.zeros(len(r_dip[0]),np.bool) #start a new array to check if positions are close enough to muonophiles
			for i in range(len(r_muonophile[0])):
				r_rel = r_dip-np.reshape(r_muonophile[:,i],(3,1))
				keep = np.bitwise_and(keep,(np.sum(r_rel*r_rel, 0)>bond_min)) #make sure you're not too close to a muonophile either
				keep_close = np.bitwise_or(keep_close,(np.sum(r_rel*r_rel, 0)<bond_max)) #the 'not further than x from a muonophile' condition starts all false and is then bitwise_or because it doesn't matter which muonophile you're not more than x from
			keep = np.bitwise_and(keep,keep_close)
			r_dip = np.compress(keep,r_dip,axis=1) #discard those dipole field points too close to atoms
			r_frac = np.compress(keep,r_frac,axis=1)
			n = np.sum(keep)*100 #999 make this work!!
			t_start = time.clock()
			for i in range(len(r_dip[0])):
				B = difast.calculate_dipole(np.reshape(r_dip[:,i],(3,1)), r_fast, mu_fast)
				omega = difn.gyro(B)
				#only write to the file if the result is not invalid, caused by being on top of a moment
				if not np.isnan(omega):
					csc.append([r_frac[0,i],r_frac[1,i],r_frac[2,i],r_dip[0,i],r_dip[1,i],r_dip[2,i],B[0],B[1],B[2],omega],file)
				if i%100000 == 0:
					frac_done = np.float(i+1)/(n)
					t_elapsed = (time.clock()-t_start)
					t_remain = (1-frac_done)*t_elapsed/frac_done
					print str(round(frac_done*100,1))+'% done in '+ui.s_to_hms(t_elapsed)+'...approximately '+ui.s_to_hms(t_remain)+' remaining'
		csc.close(file)
		final_message = 'Calculation completed in '+ui.s_to_hms(t_elapsed)
	else:
		final_message = 'Please ensure you have set a vcrystal radius and a number of points.'
	return ui.menu([
	['q','back to dipole menu',dipole,'']
	],final_message)

def csc_to_dipole_field(field):
	r = []
	B = []
	omega = []
	for point in field:
		r.append(point['r'])
		B.append(point['B'])
		omega.append(point['omega'])
	return r,B,omega

def omega_minmax_str_explode(array):
	if float(len(array))/2.0 != int(float(len(array))/2.0):
		return False,'Please enter pairs of minima and maxima...the number of entries should be a multiple of 2. eg 3.5,4.5,10,11'
	output = []
	a_prev = False
	for a in array:
		if a_prev is not False:
			if a > a_prev:
				try:
					output.append([float(a_prev),float(a)])
					a_prev = False
				except:
					return False,'Every value must be a valid floating-point number. Either '+a+' or '+a_prev+' is not.'
			else:
				return False,'Every second value must be larger than the previous value. eg 3.5,4.5,10,11'
		else:
			a_prev = a
	return True, output
	
def omega_minmax_to_string(omega_minmax):
	string = ''
	for minmax in omega_minmax:
		string += str(minmax[0])+'-'+str(minmax[1])+';'
	return string[:-1] #trim the excess ;

def draw_dipole():
	global visual_window
	global visual_window_contents
	dipole_data = load_current('dipole')
	draw_data = load_current('draw')
	if dipole_data.has_key('current_filename'):
		default_filename = dipole_data['current_filename']
	else:
		default_filename = ''
	dipole_filename,title,values = get_csc('output','-dipole-field.tsv',default_filename,'of your dipole field file')
	update_value('dipole', 'current_filename', dipole_filename)
	if draw_data.has_key('omega_minmax'):
		omega_minmax_to_draw = ui.inputscreen('Please enter a comma-separated list of omega_min,omega_max,min,max,min,max… (MHz, blank for \''+omega_minmax_to_string(draw_data['omega_minmax'])+' MHz\'):','floatlist',notblank=False,validate=omega_minmax_str_explode)
		if omega_minmax_to_draw is False:
			omega_minmax_to_draw = draw_data['omega_minmax']
	else:
		omega_minmax_to_draw = ui.inputscreen('Please enter a comma-separated list of omega_min,omega_max,min,max,min,max… to draw (MHz):','floatlist',0,notblank=True,validate=omega_minmax_str_explode)
	r,B,omega = csc_to_dipole_field(values)
	draw_magnetic_unit_cell()
	omega_maxmax = 0. #the largest maximum specified
	omega_minmin = 99.999e99 #and the smallest minimum
	for i in range(len(omega_minmax_to_draw)): #loop through to find them
		omega_minmax_to_draw[i][0] = omega_minmax_to_draw[i][0]*1e6 #turn it into Hz while you're at it
		omega_minmax_to_draw[i][1] = omega_minmax_to_draw[i][1]*1e6 
		if omega_minmax_to_draw[i][1] > omega_maxmax:
			omega_maxmax = omega_minmax_to_draw[i][1]
		if omega_minmax_to_draw[i][0] < omega_minmin:
			omega_minmin = omega_minmax_to_draw[i][0]
	B_minmin = omega_minmin / difn.gamma_mu #convert back to B by dividing by M(Hz) and gyromagnetic ratio
	B_maxmax = omega_maxmax / difn.gamma_mu
	B_max = np.zeros(3,np.float)
	B_min = np.zeros(3,np.float) #since the magnitude comparison is done with omega, no need to make this non-zero
	omega_max = 0
	omega_min = 9.999e99 #ie inconceivably large so everything is smaller than it
	B_sum = np.zeros(3,np.float)
	omega_sum = 0
	B_to_draw = []
	r_to_draw = []
	for i in range(len(B)):
		if omega[i] > omega_max:
			omega_max = omega[i]
			B_max = B[i]
		elif omega[i] < omega_min:
			omega_min = omega[i]
			B_min = B[i]
		B_sum += B[i]
		omega_sum += omega[i]
		for minmax in omega_minmax_to_draw:
			if minmax[0] < omega[i] and minmax[1] > omega[i]:
				B_to_draw.append(B[i])
				r_to_draw.append(r[i])
	B_mean = B_sum / len(B)
	omega_mean = omega_sum / len(omega)
	dipole_info = 'omega_max = '+str(omega_max/1000000.) +' MHz (B_max = '+str(B_max)+' T)'+lang.newline
	dipole_info += 'omega_min = '+str(omega_min/1000000.) +' MHz (B_min = '+str(B_min)+' T)'+lang.newline
	dipole_info += 'omega_mean = '+str(omega_mean/1000000.) +' MHz (B_mean = '+str(B_mean)+' T)'+lang.newline
	B_min_mod = difn.modulus(B_min)
	B_max_mod = difn.modulus(B_max)
	#draw this stuff
	scale = draw_data['scale']
	visual_window_contents['dipole_field'] = didraw.vector_field(r_to_draw,B_to_draw,B_minmin,B_maxmax,'rainbow',0.2,scale)

	return ui.menu([
	['q','back to dipole menu',dipole,'']
	],dipole_info)

def histo_freq():
	menu_data = {}
	dipole_data = load_current('dipole')
	if dipole_data.has_key('current_filename'):
		menu_data['filename'] = dipole_data['current_filename']
	else:
		menu_data['filename'] = lang.red+'not set'+lang.reset
	if dipole_data.has_key('histo_min') and dipole_data.has_key('histo_max') and dipole_data.has_key('histo_bins'): #only possible to have one set without the other after a crash or something weird...
		menu_data['binning'] = 'min='+str(dipole_data['histo_min'])+' MHz, max='+str(dipole_data['histo_max'])+' MHz, bins='+str(dipole_data['histo_bins'])
	else:
		menu_data['binning'] = lang.red+'not set'+lang.reset
	menuoptions = [
	['f','field filename',histo_filename,menu_data['filename']],
	['b','binning options',histo_binning,menu_data['binning']],
	]
	if dipole_data.has_key('current_filename') and dipole_data.has_key('histo_min') and dipole_data.has_key('histo_max') and dipole_data.has_key('histo_bins'):
		menuoptions.append(['h','save histogram',histo_save,''])
		menuoptions.append(['l','save list of frequencies',histo_save_raw,''])
		menuoptions.append(['n','save list of frequencies with positions too near to atoms excluded',histo_save_raw_near,''])
		menuoptions.append(['o','save list of frequencies with positions an angstrom from O',histo_save_raw_near_muonophile,''])
		menuoptions.append(['r','write R script for kernel density estimation on a list of frequencies',histo_save_r,''])
	menuoptions.append(['q','back to dipole menu',dipole,''])
	return ui.menu(menuoptions,ui.heading('Frequency histogram menu'))

def histo_filename():
	dipole_data = load_current('dipole')
	if dipole_data.has_key('current_filename'):
		default_filename = dipole_data['current_filename']
	else:
		default_filename=''
	directory = 'output'
	suffix = '-dipole-field.tsv'
	filename = ui.get_filename(directory,suffix,default_filename,file_description='of your dipole field file')
	update_value('dipole','current_filename',filename)
	return histo_freq

def histo_binning():
	dipole_data = load_current('dipole')
	#get the minimum
	if dipole_data.has_key('histo_min'):
		min = ui.inputscreen('Minimum frequency for histogram (MHz) (blank for '+str(dipole_data['histo_min'])+'):','float',0,eqmin=True,notblank=False)
	else:
		min = ui.inputscreen('Minimum frequency for histogram (MHz):','float',0,eqmin=True,notblank=True)
	if min is not False:
		update_value('dipole','histo_min',min)
	#get the maximum--make sure it's greater than the minimum!
	if dipole_data.has_key('histo_max') and dipole_data['histo_max'] > min:
		max = ui.inputscreen('Maximum frequency for histogram (MHz) (blank for '+str(dipole_data['histo_max'])+'):','float',min,eqmin=False,notblank=False)
	else:
		max = ui.inputscreen('Minimum frequency for histogram (MHz):','float',min,eqmin=False,notblank=True)
	if max is not False:
		update_value('dipole','histo_max',max)
	#get the number of bins
	if dipole_data.has_key('histo_bins'):
		bins = ui.inputscreen('Number of bins (blank for '+str(dipole_data['histo_bins'])+'):','int',0,eqmin=False,notblank=False)
	else:
		bins = ui.inputscreen('Number of bins:','int',0,eqmin=False,notblank=True)
	if bins is not False:
		update_value('dipole','histo_bins',bins)
	return histo_freq

def histo_save():
	print 'Initialising...'
	dipole_data = load_current('dipole')
	dipole_filename = dipole_data['current_filename']+'-dipole-field.tsv'
	meta,properties,f = csc.begin_read('output/'+dipole_filename)
	min = dipole_data['histo_min']*1e6
	max = dipole_data['histo_max']*1e6 #x1,000,000 for MHz --> Hz
	bins = dipole_data['histo_bins']
	binwidth = (max-min)/bins
	histo = np.zeros(bins,np.int)
	not_eof = True
	total = 0
	print 'Reading file...'
	while not_eof:
		if total%1000000 == 0:
			print 'line '+str(total)+'...',
		values,error = csc.readline(f,properties)
		if error == 'EOF':
			not_eof = False
		elif error == None:
			total += 1 #it's a new datapoint whatever happens
			#if it's within the range, shove it into the histogram
			if values['omega'] >= min and values['omega'] <= max:
				histo[np.int((values['omega']-min)/binwidth)] += 1
	csc.close(f)
	#now to write the histogram file...
	meta_out = {}
	meta_out['title'] = meta['title']
	meta_out['dipole_filename'] = dipole_filename
	meta_out['histo_min'] = dipole_data['histo_min']
	meta_out['histo_max'] = dipole_data['histo_max']
	meta_out['histo_bins'] = dipole_data['histo_bins']
	meta_out['histo_total'] = total #total number of field points taken
	properties_out = ['f','pdf','n']
	filename = 'output/'+dipole_data['current_filename'] + '-frequency-histogram.tsv'
	output = csc.begin(meta_out,properties_out,filename)
	#work out the prefactor to turn number of counts into a probability density
	n2p = 1/(binwidth*total) #ie divide by bin width and total number
	for i in range(bins):
		bin_centre = min+(i+0.5)*binwidth
		csc.append([bin_centre,n2p*histo[i],histo[i]],output)
	csc.close(output)
	return histo_freq

#this is the old version of this function, which opened the entire CSC file at once. This was predictably slow and MemoryError-prone with large files.
#~ def histo_save():
	#~ print 'Writing file...',
	#~ dipole_data = load_current('dipole')
	#~ dipole_filename,title,values = get_csc('output','-dipole-field.tsv',dipole_data['current_filename'],'of your dipole field file')
	#~ r,B,omega = csc_to_dipole_field(values)
	#~ histo,bin_edges = np.histogram(omega, bins=dipole_data['histo_bins'], range=(dipole_data['histo_min']*1e6,dipole_data['histo_max']*1e6)) #x1,000,000 for MHz > Hz
	#~ print len(histo),len(bin_edges)
	#~ attr = []
	#~ #work out the prefactor to turn number of counts into a probability density
	#~ n2p = 1/((bin_edges[1]-bin_edges[0])*len(r)) #ie divide by bin width and total number
	#~ #make an array of bin middles and probability densities
	#~ if len(histo)==len(bin_edges): #Ubuntu (so I guess old NumPy) seems to spit out the bin middles by default!
		#~ for i in range(len(histo)): #so do it the easy way if the arrays are the same size
			#~ attr.append([bin_edges[i], n2p*histo[i]])
	#~ else:
		#~ for i in range(len(histo)): #but average the edges of the bins if not
			#~ attr.append([(bin_edges[i]+bin_edges[i+1])/2., n2p*histo[i]])
	#~ meta = {}
	#~ meta['title'] = title
	#~ meta['dipole_filename'] = dipole_filename
	#~ meta['histo_min'] = dipole_data['histo_min']
	#~ meta['histo_max'] = dipole_data['histo_max']
	#~ meta['histo_bins'] = dipole_data['histo_bins']
	#~ meta['histo_total'] = len(r) #total number of field points taken
	#~ properties = ['f','n']
	#~ filename = 'output/'+dipole_data['current_filename'] + '-frequency-histogram.tsv'
	#~ if csc.write(meta,properties,attr,filename):
		#~ print 'success!'
	#~ else:
		#~ print 'failure! For some reason?! Try again?' #this won't display for long enough to be useful 998
	#~ return histo_freq

def histo_save_raw():
	print 'Writing file...',
	dipole_data = load_current('dipole')
	dipole_filename,title,values = get_csc('output','-dipole-field.tsv',dipole_data['current_filename'],'of your dipole field file')
	r,B,omega = csc_to_dipole_field(values)
	min = dipole_data['histo_min']*1e6
	max = dipole_data['histo_max']*1e6 #x1,000,000 for MHz --> Hz
	omega_to_export = []
	for i in range(len(omega)):
		if omega[i] > min and omega[i] < max:
			omega_to_export.append([omega[i]])
	meta = {}
	meta['title'] = title
	meta['dipole_filename'] = dipole_filename
	meta['desc'] = 'Just the frequencies from '+dipole_filename+' for further processing'
	properties = ['#f'] #slightly hackily calls this #f because then R won't fall over when it reads it
	filename = 'output/'+dipole_data['current_filename'] + '-frequencies-raw.tsv'
	if csc.write(meta,properties,omega_to_export,filename):
		print 'success!'
	else:
		print 'failure! For some reason?! Try again?' #this won't display for long enough to be useful 998
	return histo_freq
	
def histo_save_r():
	print 'Writing file...',
	dipole_data = load_current('dipole')
	filename = 'output/'+dipole_data['current_filename'] + '-frequencies-kernel.r'
	f = open(filename,'w')
	f.write('''omega = scan("'''+dipole_data['current_filename'] + '-frequencies-raw.tsv'+'''", what=numeric(0), comment.char = "#")
d <- density(omega)
x <- data.frame(d[1],d[2])
write.table(x,sep = "\\t",file = "'''+dipole_data['current_filename'] + '-frequencies-kde.tsv'+'")')
	f.close()
	return histo_freq

def histo_save_raw_near():
	neardists = np.array([0,0.1,0.2,0.5,0.8,1.,1.1,1.2,1.3,1.4,1.5,2.])*1e-10 #angstroms, for testing
	dipole_data = load_current('dipole')
	print 'Reading dipole field file...',
	meta,properties,f = csc.begin_read('output/'+dipole_data['current_filename']+'-dipole-field.tsv')
	min = dipole_data['histo_min']*1e6
	max = dipole_data['histo_max']*1e6 #x1,000,000 for MHz --> Hz
	#then import the crystal structure
	a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
	L = difn.mag_unit_cell_size(k_atoms)
	r_atoms = difn.zero_if_close(r_atoms)
	r_unit,q_unit,mu_unit,names_unit = difn.make_para_crystal(a_cart, r_atoms, m_atoms, k_atoms, q_atoms, name_atoms,[0,0,0], L)
	#then delete all atoms outside the magnetic unit cell
	r_unit,q_unit,mu_unit,names_unit = difn.make_crystal_trim_para(r_unit,q_unit,mu_unit,names_unit,a_cart,L)
	r_unit = difast.reshape_array(r_unit)
	not_eof = True
	#open the files to write to:
	outputs = []
	meta_out = {}
	meta_out['title'] = meta['title']
	meta_out['dipole_filename'] = 'output/'+dipole_data['current_filename']+'-dipole-field.tsv'
	properties_out = ['#f'] #slightly hackily calls this #f because then R won't fall over when it reads it
	for i in range(len(neardists)):
		meta['desc'] = 'Frequencies from '+meta_out['dipole_filename']+' with positions closer than '+str(neardists[i])+' m to an atom removed'
		outputs.append(csc.begin(meta_out,properties_out,'output/'+dipole_data['current_filename']+'-frequencies-raw-near-removed-'+str(neardists[i])+'.tsv'))
	j = 0
	while not_eof:
		j += 1
		if j%1000 == 0:
			print 'line '+str(j)+'...',
		values,error = csc.readline(f,properties)
		if error == 'EOF':
			not_eof = False
		elif error == None:
			r_dip = difast.reshape_vector(values['r'])
			r_rel = r_unit-r_dip
			#include = np.ones(len(neardists),np.bool) #is the distance relative to an atom far enough? Start all true...
			for i in range(len(neardists)):
				if (np.sum(r_rel*r_rel, 0)>neardists[i]**2).all(): #only keep it if they're all greater!
					csc.append([values['omega']],outputs[i])
	csc.close(f)
	for i in range(len(neardists)):
		csc.close(outputs[i])
	return histo_freq

def histo_save_raw_near_muonophile():
	bond_min = 1.1e-10**2 #angstroms, for testing
	bond_max = 1.4e-10**2 #angstroms, for testing
	bond_element = 'F'
	dipole_data = load_current('dipole')
	print 'Reading dipole field file...',
	meta,properties,f = csc.begin_read('output/'+dipole_data['current_filename']+'-dipole-field.tsv')
	min = dipole_data['histo_min']*1e6
	max = dipole_data['histo_max']*1e6 #x1,000,000 for MHz --> Hz
	#then import the crystal structure
	a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
	L = difn.mag_unit_cell_size(k_atoms)
	r_atoms = difn.zero_if_close(r_atoms)
	r_unit,q_unit,mu_unit,names_unit = difn.make_para_crystal(a_cart, r_atoms, m_atoms, k_atoms, q_atoms, name_atoms,[0,0,0], L)
	#then delete all atoms outside the magnetic unit cell
	r_unit,q_unit,mu_unit,names_unit = difn.make_crystal_trim_para(r_unit,q_unit,mu_unit,names_unit,a_cart,L)
	r_muonophile = []
	for i in range(len(r_unit)):
		if names_unit[i] == bond_element:
			r_muonophile.append(r_unit[i])
	r_unit = difast.reshape_array(r_unit)
	r_muonophile = difast.reshape_array(r_muonophile)
	not_eof = True
	#open the files to write to:
	meta_out = {}
	meta_out['title'] = meta['title']
	meta_out['dipole_filename'] = 'output/'+dipole_data['current_filename']+'-dipole-field.tsv'
	meta['desc'] = 'Frequencies from '+meta_out['dipole_filename']+' between 0.9 and 1.1 angstroms from an oxygen, and not less than 0.9 angstroms from other stuff'
	properties_out = ['rho_x','rho_y','rho_z','r_x','r_y','r_z','B_x','B_y','B_z','omega']
	#output = csc.begin(meta_out,properties_out,'output/'+dipole_data['current_filename']+'-frequencies-raw-near-O.tsv')
	output = csc.begin(meta_out,properties_out,'output/'+dipole_data['current_filename']+'-near-O-dipole-field.tsv')
	j = 0
	t_start = time.clock()
	while not_eof:
		j += 1
		if j%1000 == 0:
			print 'line '+str(j)+'...',
		values,error = csc.readline(f,properties)
		if error == 'EOF':
			not_eof = False
		elif error == None:
			r_dip = difast.reshape_vector(values['r'])
			r_rel = r_unit-r_dip
			if (np.sum(r_rel*r_rel, 0)>bond_min).all(): #only keep it if they're all greater!
				r_rel = r_muonophile-r_dip #redo this to be fom muonophiles
				if (np.sum(r_rel*r_rel, 0)<bond_max).any(): #and if it's less than max from any muon-lover
					vals_list = [values['rho_x'],values['rho_y'],values['rho_z'],values['r'][0],values['r'][1],values['r'][2],values['B'][0],values['B'][1],values['B'][2],values['omega']]
					csc.append(vals_list,output)
	csc.close(f)
	csc.close(output)
	t_elapsed = time.clock()-t_start
	return ui.menu([
	['q','back to dipole menu',histo_freq,'']
	],'List of frequencies written in '+ui.s_to_hms(t_elapsed))

# This old version of the function throws a memoryerror on reading large files. Is there any hope for it? 998
# Its advantage is that it loads the file and then does all processing in fast, smart NumPy.
#~ def histo_save_raw_near():
	#~ neardists = np.array([0.1,0.2,0.5,0.8,1.,1.5,2.])*1e-10 #angstroma, for testing
	#~ dipole_data = load_current('dipole')
	#~ print 'Reading dipole field file...',
	#~ dipole_filename,title,values = get_csc('output','-dipole-field.tsv',dipole_data['current_filename'],'of your dipole field file')
	#~ r_dip,B,omega = csc_to_dipole_field(values)
	#~ print 'excluding positions too near to atoms...',
	#~ min = dipole_data['histo_min']*1e6
	#~ max = dipole_data['histo_max']*1e6 #x1,000,000 for MHz --> Hz
	#~ r_dip = difast.reshape_array(r_dip)
	#~ omega = np.reshape(omega,(1,len(omega)))
	#~ #then import the crystal structure
	#~ a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
	#~ L = difn.mag_unit_cell_size(k_atoms)
	#~ r_atoms = difn.zero_if_close(r_atoms)
	#~ r_unit,q_unit,mu_unit,names_unit = difn.make_para_crystal(a_cart, r_atoms, m_atoms, k_atoms, q_atoms, name_atoms,[0,0,0], L)
	#~ #then delete all atoms outside the magnetic unit cell
	#~ r_unit,q_unit,mu_unit,names_unit = difn.make_crystal_trim_para(r_unit,q_unit,mu_unit,names_unit,a_cart,L)
	#~ r_unit = difast.reshape_array(r_unit)
	#~ for near in neardists:
		#~ discard = np.ones(len(r_dip[0]),np.bool) #is the distance relative to an atom too close? Start all false...
		#~ #print np.shape(r_dip),np.shape(r_unit),np.shape(r_unit[:,0])
		#~ for i in range(len(r_unit[0])):
			#~ r_rel = r_dip-np.reshape(r_unit[:,i],(3,1)) #find how far the dipole field point is from all the atoms 998 why does this need reshaping to go from (3,) to (3,1)?
			#~ #print np.shape(discard),np.shape((np.sqrt(np.sum(r_rel*r_rel, 0))>near))
			#~ discard = np.bitwise_and(discard,(np.sqrt(np.sum(r_rel*r_rel, 0))>near)) #if any of them is closer than near, set this to false to discard. Using bitwise_or means that only continual 'true's will result in an array element not being discarded in a moment
			#~ #print np.sqrt(np.sum(r_rel*r_rel, 0))>1e-10
		#~ #exit()
		#~ #print 'omegashape1',np.shape(omega),np.shape(discard)
		#~ omega = np.compress(discard,omega,axis=1) #discard those dipole field points too close to atoms
		#~ r_dip = np.compress(discard,r_dip,axis=1) #discard those dipole field points too close to atoms
		#~ r_unit = np.compress(discard,r_unit,axis=1) #discard those dipole field points too close to atoms
		#~ #print 'omegashape',np.shape(omega)
		#~ print 'writing file...'
		#~ omega_to_export = []
		#~ for i in range(len(omega_far[0])):
			#~ if omega[0][i] > min and omega[0][i] < max:
				#~ omega_to_export.append([omega[0][i]])
		#~ meta = {}
		#~ meta['title'] = title
		#~ meta['dipole_filename'] = dipole_filename
		#~ meta['desc'] = 'Frequencies from '+dipole_filename+' with positions closer than '+str(near)+' m to an atom removed'
		#~ properties = ['#f'] #slightly hackily calls this #f because then R won't fall over when it reads it
		#~ filename = 'output/'+dipole_data['current_filename'] + '-frequencies-raw-near-removed-'+str(near*1e10)+'.tsv'
		#~ if csc.write(meta,properties,omega_to_export,filename):
			#~ print 'success!'
		#~ else:
			#~ print 'failure! For some reason?! Try again?' #this won't display for long enough to be useful 998
	#~ return histo_freq

#999 this whole function is a hack, make it good if it's worth it
def dipole_symmetry_eqv2():
	dipole_data = load_current('dipole')
	crystal_data = load_current('crystal')
	print 'Getting symmetry generators...',
	transform, translate = sg.get_generators(crystal_data['space_group'], crystal_data['space_group_setting'])
	n_transforms=len(transform)
	r_gen = np.zeros((n_transforms,3),np.float) #initialise an array for the generated positions
	#build vcrystal -- 999 this should load the vcrystal originally used 999 and I should make 'build and save vcrystal' a function of its own
	radius = dipole_data['r_sphere']
	n = [dipole_data['n_a'],dipole_data['n_b'],dipole_data['n_c']]
	a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
	#make the vcrystal
	print 'Creating virtual crystal (r = '+str(radius)+'a)...'
	L,r,q,mu,name,r_whatisthis = difn.make_crystal(radius,a,alpha,r_atoms,m_atoms,k_atoms, q_atoms, name_atoms,type='magnetic') #999whatisthis
	r_fast = difast.reshape_array(r)
	mu_fast = difast.reshape_array(mu)
	print 'Reading dipole field file...',
	#~ meta,properties,f = csc.begin_read('output/'+dipole_data['current_filename']+'-dipole-field.tsv')
	meta,properties,f = csc.begin_read('output/Ba2NaOsO6-FM111-highres-2-dipole-field.tsv')
	min = 3.8*1e6
	max = 4.0*1e6 #x1,000,000 for MHz --> Hz
	#then import the crystal structure
	not_eof = True
	#open the files to write to:
	meta_out = {}
	meta_out['title'] = meta['title']
	meta_out['dipole_filename'] = 'output/'+dipole_data['current_filename']+'-dipole-field.tsv'
	meta['desc'] = 'Frequencies from '+meta_out['dipole_filename']+' between 0.9 and 1.1 angstroms from an oxygen, and not less than 0.9 angstroms from other stuff'
	properties_out = ['rho_x','rho_y','rho_z','r_x','r_y','r_z','omega_1','omega_2'] #998 include number of symmetry-eqv points?
	#output = csc.begin(meta_out,properties_out,'output/'+dipole_data['current_filename']+'-frequencies-raw-near-O.tsv')
	#output = csc.begin(meta_out,properties_out,'output/Ba2NaOsO6-FM111-highres-2-dipole-field-symeqv.tsv')
	#~ output = csc.begin(meta_out,properties_out,'output/'+dipole_data['current_filename']+'-near-O-dipole-field.tsv')
	
	#999
	searchmin=1.4e6
	searchmax=1.6e6
	min=0
	max=5e6
	bins=100
	
	
	binwidth = (max-min)/bins
	histo = np.zeros(bins,np.int)
	total = 0
	t_start = time.clock()
	while not_eof and total < 100001:
		print total
		values,error = csc.readline(f,properties)
		if error == 'EOF':
			not_eof = False
		elif error == None:
			if values['omega'] > searchmin and values['omega'] < searchmax: #only do this for values we're keen on
				r_dip = np.array([values['rho_x'],values['rho_y'],values['rho_z']],np.float)
				omega = np.array([values['rho_x'],values['rho_y'],values['rho_z']],np.float)
				for j in range(n_transforms):
					r_gen[j] = sg.trans(r_dip,transform[j],translate[j]) #create the new, symmetry-equivalent positions
				#check for duplicates 999 make this a function in sg
				r_out = []
				for i in range(len(r_gen)):
					#only check the subsequent values to discard, such that the first of each is kept
					keep = True
					for j in range(len(r_gen)-i-1):
						#if it's damn close - 999 how damn close? (can't just use equality because of rounding errors)
						if np.all(np.less(r_gen[i],r_gen[i+j+1] + 0.001)) and  np.all(np.greater(r_gen[i],r_gen[i+j+1] - 0.001)):
							keep = False
					if keep:
						r_gen_abs=r_gen[i][0]*a_cart[0]+r_gen[i][1]*a_cart[1]+r_gen[i][2]*a_cart[2]
						r_out.append(r_gen_abs)
				#~ draw_draw() #this draws the symmetry eqv positions
				#~ global visual_window
				#~ global visual_window_contents
				#~ draw_data = load_current('draw')
				#~ didraw.points(r_out,draw_data['scale'])
				#~ return draw
				#calculate dipole fields at eqv positions
				for i in range(len(r_out)):
					r_test_fast = difast.reshape_vector(r_out[i])
					B = difast.calculate_dipole(r_test_fast, r_fast, mu_fast)
					omega_2 = difn.gyro(B)
					#vals_list = [values['rho_x'],values['rho_y'],values['rho_z'],values['r'][0],values['r'][1],values['r'][2],values['omega'],omega_2]
					#csc.append(vals_list,output)
					total += 1 #it's a new datapoint whatever happens
					#if it's within the range, shove it into the histogram
					if values['omega'] >= min and values['omega'] <= max:
						histo[np.int((values['omega']-min)/binwidth)] += 1
	csc.close(f)
	#now to write the histogram file...
	meta_out = {}
	meta_out['title'] = meta['title']
	#meta_out['dipole_filename'] = dipole_filename #999
	meta_out['histo_min'] = dipole_data['histo_min']
	meta_out['histo_max'] = dipole_data['histo_max']
	meta_out['histo_bins'] = dipole_data['histo_bins']
	meta_out['histo_total'] = total #total number of field points taken
	properties_out = ['f','pdf','n']
	#~ filename = 'output/'+dipole_data['current_filename'] + '-frequency-histogram.tsv'
	filename = 'output/Ba2NaOsO6-FM111-highres-2-dipole-field-symeqv.tsv'#999
	output = csc.begin(meta_out,properties_out,filename)
	#work out the prefactor to turn number of counts into a probability density
	n2p = 1/(binwidth*total) #ie divide by bin width and total number
	for i in range(bins):
		bin_centre = min+(i+0.5)*binwidth
		csc.append([bin_centre,n2p*histo[i],histo[i]],output)
	csc.close(output)
	t_elapsed = time.clock()-t_start
	return ui.menu([
	['q','back to dipole menu',dipole,'']
	],'Symmetry-equivalent comparison written in '+ui.s_to_hms(t_elapsed))

#999 this whole function is a hack, make it good if it's worth it
def dipole_symmetry_eqv():
	dipole_data = load_current('dipole')
	crystal_data = load_current('crystal')
	print 'Getting symmetry generators...',
	transform, translate = sg.get_generators(crystal_data['space_group'], crystal_data['space_group_setting'])
	n_transforms=len(transform)
	r_gen = np.zeros((n_transforms,3),np.float) #initialise an array for the generated positions
	#build vcrystal -- 999 this should load the vcrystal originally used 999 and I should make 'build and save vcrystal' a function of its own
	radius = dipole_data['r_sphere']
	n = [dipole_data['n_a'],dipole_data['n_b'],dipole_data['n_c']]
	a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
	#make the vcrystal
	print 'Creating virtual crystal (r = '+str(radius)+'a)...'
	L,r,q,mu,name,r_whatisthis = difn.make_crystal(radius,a,alpha,r_atoms,m_atoms,k_atoms, q_atoms, name_atoms,type='magnetic') #999whatisthis
	r_fast = difast.reshape_array(r)
	mu_fast = difast.reshape_array(mu)
	print 'Reading dipole field file...',
	#~ meta,properties,f = csc.begin_read('output/'+dipole_data['current_filename']+'-dipole-field.tsv')
	meta,properties,f = csc.begin_read('output/CuBF4-AFM7-nearHF2-mags-dipole-field.tsv')
	min = 0*1e6
	max = 10*1e6 #x1,000,000 for MHz --> Hz
	#then import the crystal structure
	not_eof = True
	#open the files to write to:
	meta_out = {}
	meta_out['title'] = meta['title']
	meta_out['dipole_filename'] = 'output/'+dipole_data['current_filename']+'-dipole-field.tsv'
	meta['desc'] = 'Frequencies from '+meta_out['dipole_filename']+' with sym eqv near HF2'
	properties_out = ['rho_x','rho_y','rho_z','r_x','r_y','r_z','omega_1','omega_2'] #998 include number of symmetry-eqv points?
	#output = csc.begin(meta_out,properties_out,'output/'+dipole_data['current_filename']+'-frequencies-raw-near-O.tsv')
	#output = csc.begin(meta_out,properties_out,'output/Ba2NaOsO6-FM111-highres-2-dipole-field-symeqv.tsv')
	#~ output = csc.begin(meta_out,properties_out,'output/'+dipole_data['current_filename']+'-near-O-dipole-field.tsv')
	
	#999
	min=0
	max=30e6
	bins=300
	
	
	binwidth = (max-min)/bins
	#histo = np.zeros(bins,np.int) #not done like this any more
	total = 0
	t_start = time.clock()
	omega_x = []
	omega_y = []
	while not_eof and total < 100001:
		print total
		values,error = csc.readline(f,properties)
		if error == 'EOF':
			not_eof = False
		elif error == None:
			if values['omega'] > min and values['omega'] < max: #only do this for values we're keen on
				r_dip = np.array([values['rho_x'],values['rho_y'],values['rho_z']],np.float)
				omega = np.array([values['rho_x'],values['rho_y'],values['rho_z']],np.float)
				for j in range(n_transforms):
					r_gen[j] = sg.trans(r_dip,transform[j],translate[j]) #create the new, symmetry-equivalent positions
				#check for duplicates 999 make this a function in sg
				r_out = []
				for i in range(len(r_gen)):
					#only check the subsequent values to discard, such that the first of each is kept
					keep = True
					for j in range(len(r_gen)-i-1):
						#if it's damn close - 999 how damn close? (can't just use equality because of rounding errors)
						if np.all(np.less(r_gen[i],r_gen[i+j+1] + 0.001)) and  np.all(np.greater(r_gen[i],r_gen[i+j+1] - 0.001)):
							keep = False
					if keep:
						r_gen_abs=r_gen[i][0]*a_cart[0]+r_gen[i][1]*a_cart[1]+r_gen[i][2]*a_cart[2]
						r_out.append(r_gen_abs)
				#~ draw_draw() #this draws the symmetry eqv positions
				#~ global visual_window
				#~ global visual_window_contents
				#~ draw_data = load_current('draw')
				#~ didraw.points(r_out,draw_data['scale'])
				#~ return draw
				#calculate dipole fields at eqv positions
				for i in range(len(r_out)):
					r_test_fast = difast.reshape_vector(r_out[i])
					B = difast.calculate_dipole(r_test_fast, r_fast, mu_fast)
					omega_2 = difn.gyro(B)
					#vals_list = [values['rho_x'],values['rho_y'],values['rho_z'],values['r'][0],values['r'][1],values['r'][2],values['omega'],omega_2]
					#csc.append(vals_list,output)
					total += 1 #it's a new datapoint whatever happens
					#if it's within the range, shove it into the histogram
					if omega_2 >= min and omega_2 <= max:
						total += 1
						omega_x.append(values['omega'])
						omega_y.append(omega_2)
	csc.close(f)
	#create histogram
	H,xbins,ybins=np.histogram2d(omega_x, omega_y, bins=bins)
	#now to write the histogram file...
	meta_out = {}
	meta_out['title'] = meta['title']
	#meta_out['dipole_filename'] = dipole_filename #999
	meta_out['histo_min'] = dipole_data['histo_min']
	meta_out['histo_max'] = dipole_data['histo_max']
	meta_out['histo_bins'] = dipole_data['histo_bins']
	meta_out['histo_total'] = total #total number of field points taken
	properties_out = ['f_in','f_out','pdf','n']
	#~ filename = 'output/'+dipole_data['current_filename'] + '-frequency-histogram.tsv'
	filename = 'output/CuBF4-AFM7-nearHF2-dipole-field-symeqv2dhisto.tsv' #999
	output = csc.begin(meta_out,properties_out,filename)
	#work out the prefactor to turn number of counts into a probability density
	n2p = 1/(binwidth*binwidth*total) #ie divide by bin area and total number
	for i in range(bins):
		for j in range(bins):
			csc.append([xbins[i],ybins[j],H[i,j]*n2p,H[i,j]],output)
	csc.close(output)
	t_elapsed = time.clock()-t_start
	return ui.menu([
	['q','back to dipole menu',dipole,'']
	],'Symmetry-equivalent comparison written in '+ui.s_to_hms(t_elapsed))

def draw_freq():
	global visual_window
	global visual_window_contents
	dipole_data = load_current('dipole')
	draw_data = load_current('draw')
	dipole_filename,title,values = get_csc('output','-dipole-field.tsv',dipole_data['current_filename'],'of your dipole field file')
	update_value('dipole', 'current_filename', dipole_filename)
	r,B,omega = csc_to_dipole_field(values)
	draw_magnetic_unit_cell()
	B_max = np.zeros(3,np.float)
	B_min = np.zeros(3,np.float) #since the magnitude comparison is done with omega, no need to make this non-zero
	omega_max = 0
	omega_min = 9.999e99 #ie inconceivably large so everything is smaller than it
	B_sum = np.zeros(3,np.float)
	omega_sum = 0
	for i in range(len(B)):
		if omega[i] > omega_max:
			omega_max = omega[i]
			B_max = B[i]
		elif omega[i] < omega_min:
			omega_min = omega[i]
			B_min = B[i]
		B_sum += B[i]
		omega_sum += omega[i]
	B_mean = B_sum / len(B)
	omega_mean = omega_sum / len(omega)
	dipole_info = 'omega_max = '+str(omega_max/1000000.) +' MHz (B_max = '+str(B_max)+' T)'+lang.newline
	dipole_info += 'omega_min = '+str(omega_min/1000000.) +' MHz (B_min = '+str(B_min)+' T)'+lang.newline
	dipole_info += 'omega_mean = '+str(omega_mean/1000000.) +' MHz (B_mean = '+str(B_mean)+' T)'+lang.newline
	B_min_mod = difn.modulus(B_min)
	B_max_mod = difn.modulus(B_max)
	#draw this stuff
	scale = draw_data['scale']
	visual_window_contents['dipole_frequency'] = didraw.scalar_field(r,omega,omega_min,omega_max,'rainbow',scale)
	
	return ui.menu([
	['q','back to dipole menu',dipole,'']
	],dipole_info)

def draw_default_scale():
	crystal_data = load_current("crystal")
	#get appropriate multiplier for nanometres, angstroms, metres
	if crystal_data['length_unit'] == 'n':
		unit = difn.nano
	elif crystal_data['length_unit'] == 'a':
		unit = difn.angstrom
	else:
		unit = 1.0
	a = difn.triclinic([crystal_data['a'],crystal_data['b'],crystal_data['c']],np.array([crystal_data['alpha'],crystal_data['beta'],crystal_data['gamma']]))*unit
	return didraw.scale(a)

def draw_initialise():
	draw_data = load_current('draw')
	#if there is no scale, set one
	if not draw_data.has_key('scale'):
		draw_data['scale'] = draw_default_scale()
		draw_data['scale_default'] = True
	#if it's not set but it was default before, recalculate it in case any sizes have been updated
	elif draw_data.has_key('scale_default') and draw_data['scale_default']:
		draw_data['scale'] = draw_default_scale()
	save_current('draw',draw_data)
	#if there is no colour key, set one
	if not draw_data.has_key('atom_colours'):
		draw_data['atom_colours'] = 'e'
	if not draw_data.has_key('moments'):
		draw_data['moments'] = True
	if not draw_data.has_key('unitcell'):
		draw_data['unitcell'] = True
	if not draw_data.has_key('L'):
		draw_data['L'] = [1,1,1]
	if not draw_data.has_key('auto_redraw'):
		draw_data['auto_redraw'] = True
	if not draw_data.has_key('stereo_3d'):
		draw_data['stereo_3d'] = 'n'
	if not draw_data.has_key('field_visible'):
		draw_data['field_visible'] = False
	if not draw_data.has_key('field_colours'):
		draw_data['field_colours'] = 'rainbow'
	save_current('draw',draw_data)

def draw():
	draw_initialise()
	#read in draw temp file
	draw_data = load_current("draw")
	if draw_data['auto_redraw']:
		draw_draw()
	#stuff to append to menu items if it's set
	menu_data = {}
	if draw_data['scale_default']:
		menu_data['scale'] = lang.grey + str(draw_data['scale']) + ' [default]' + lang.reset
	else:
		menu_data['scale'] = lang.grey + str(draw_data['scale']) + lang.reset
	if draw_data['atom_colours'] == 'e':
		menu_data['atom_colours'] = 'by element'
	elif draw_data['atom_colours'] == 'c':
		menu_data['atom_colours'] = 'by charge'
	if draw_data.has_key('atoms'):
		menu_data['atom_custom'] = ''
		for atom in draw_data['atoms']:
			print atom[0]
			menu_data['atom_custom'] += atom[0]+', '
		menu_data['atom_custom'] = menu_data['atom_custom'][:-2]
	elif not draw_data.has_key('atoms') or len(draw_data['atoms']) ==0:
		menu_data['atom_custom'] = 'none set'
	#is drawing moments on or off?
	if draw_data['moments']:
		menu_data['moments'] = 'currently on'
		menu_data['moments_opposite'] = 'off'
	else:
		menu_data['moments'] = 'currently off'
		menu_data['moments_opposite'] = 'on'
	#is drawing the white unit cell outline on or off?
	if draw_data['unitcell']:
		menu_data['unitcell'] = 'currently on'
		menu_data['unitcell_opposite'] = 'off'
	else:
		menu_data['unitcell'] = 'currently off'
		menu_data['unitcell_opposite'] = 'on'
	#is auto redraw on or off?
	if draw_data['auto_redraw']:
		menu_data['auto_redraw'] = 'currently on'
		menu_data['auto_redraw_opposite'] = 'off'
	else:
		menu_data['auto_redraw'] = 'currently off'
		menu_data['auto_redraw_opposite'] = 'on'
	#is field on or off?
	if draw_data['field_visible']:
		menu_data['field'] = draw_data['field_filename']
	else:
		menu_data['field'] = 'off'
	menu_data['unitcells'] = str(draw_data['L'])
	if draw_data['stereo_3d'] == 'n':
		menu_data['stereo_3d'] = 'off'
	elif draw_data['stereo_3d'] == 'r':
		menu_data['stereo_3d'] = 'red-cyan'
	elif draw_data['stereo_3d'] == 'b':
		menu_data['stereo_3d'] = 'red-blue'
	else:
		menu_data['stereo_3d'] = 'error' #can't see why this would happen, but it's better than the program crashing
	#the menu
	menuoptions = [['s','scale',draw_scale,menu_data['scale']],
	['c','atom colours',draw_atom_colours,menu_data['atom_colours']],
	['t','customise atoms',draw_customise_atoms,menu_data['atom_custom']],
	['m','moments '+menu_data['moments_opposite'],draw_moments_onoff,menu_data['moments']],
	['b','unit cell boundary '+menu_data['unitcell_opposite'],draw_unitcell_onoff,menu_data['unitcell']],
	['a','auto redraw '+menu_data['auto_redraw_opposite'],draw_auto_redraw_onoff,menu_data['auto_redraw']]]
	if not draw_data['auto_redraw']:
		menuoptions.append(['d','manual redraw',manual_redraw,''])
	menuoptions.append(['u','unit cells',draw_unitcells,menu_data['unitcells']])
	menuoptions.append(['f','field',draw_field,menu_data['field']])
#	['r','field repeat',b,menu_data['b']],
	menuoptions.append(['3','3D stereo',draw_3d,menu_data['stereo_3d']])
	menuoptions.append(['v','save settings',draw_save,''])
	menuoptions.append(['l','load settings',draw_load,''])
	if visual_window is not None: #only provide this option if there's something to export
		menuoptions.append(['e','export image to POV-ray',draw_povexport,''])
	menuoptions.append(['q','back to main menu',main_menu,''])
	return ui.menu(menuoptions)

def draw_moments_onoff():
	return option_toggle('draw','moments',draw)

def draw_unitcell_onoff():
	return option_toggle('draw','unitcell',draw)
	
def draw_auto_redraw_onoff():
	return option_toggle('draw','auto_redraw',draw)

def manual_redraw():
	print 'Redrawing...'
	draw_draw()
	return draw
	
def draw_unitcells():
	a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
	L = difn.mag_unit_cell_size(k_atoms)
	Lstr = str(L[0])+'x'+str(L[1])+'x'+str(L[2])
	a = ui.option([
	['c','crystallographic unit cell',False,'1x1x1'],
	['m','magnetic unit cell',False,Lstr], #999
	['x','custom',False,'']
	])
	#if it's not blank, update the value
	if a == 'c':
		update_value('draw','L',[1,1,1])
	elif a == 'm':
		update_value('draw','L',list(L))
	elif a == 'x':
		userL = ui.inputscreen(' Enter T_x,T_y,T_z:','intlist',1,number=3)
		update_value('draw','L',userL)
	return draw

def draw_scale():
	crystal_data = load_current("draw")
	scale_default = draw_default_scale()
	a = ui.inputscreen('Type new scale (m) (blank for default, '+str(scale_default)+'):','float',notblank=False)
	#blank => default
	if a is False:
		update_value('draw','scale',scale_default)
		update_value('draw','scale_default',True)
	#not blank => change val
	else:
		update_value('draw','scale',a)
		update_value('draw','scale_default',False)
	return draw

def draw_atom_colours():
	a = ui.option([
	['e','by element',False,''],
	['c','by electric charge',False,''] #999
#	['m','by moment size',False]
	])
	#if it's not blank, update the value
	if a != '':
		update_value('draw','atom_colours',a)
	return draw

def draw_atoms_table():
	#load (and print out) any already-existent atom data
	draw_data = load_current('draw')
	if draw_data.has_key('atoms'):
		atoms = draw_data['atoms']
		atoms_table_array = []
		atoms_table_array.append(['#','element','colour','size','opacity'])
		i = 1
		for atom in atoms:
			print atom
			atom_row = []
			atom_row.append(str(i))
			atom_row.append(str(atom[0])) #element
			#if it's visible
			if atom[1] == 'yes':
				if atom[2] is not False: #colour
					atom_row.append(str(atom[2]))
				else:
					atom_row.append('[default]')
				if atom[3] == 'd': #if atom size is default
					atom_row.append('[default]') #size
				else:
					if atom[3] == 'r':
						size_unit = ''
					elif atom[3] == 'n':
						size_unit = ' nm'
					elif atom[3] == 'm':
						size_unit = ' m'
					else:
						size_unit = ' '+lang.angstrom
					atom_row.append(str(atom[4])+size_unit) #size
				if atom[5] is not False: #opacity
					atom_row.append(str(atom[5]))
				else:
					atom_row.append('[default]')
			else:
				atom_row.append('[hidden]')
				atom_row.append('[hidden]')
				atom_row.append('[hidden]')
			atoms_table_array.append(atom_row)
			i += 1
		return ui.table(atoms_table_array)
	else:
		return ''

def draw_customise_atoms():
	draw_data = load_current('draw')
	if draw_data['auto_redraw']:
		draw_draw()
	#if there are atoms
	if draw_data.has_key('atoms') and len(draw_data['atoms']) != 0:
		return ui.menu([
		['a','add custom atom',draw_customise_add,''],
		['d','delete custom atom',draw_customise_delete,''],
		['e','edit custom atom',draw_customise_edit,''],
		['q','back to visualisation menu',draw,'']
		],draw_atoms_table())
	#if none has been set yet
	else:
		return ui.menu([
		['a','add custom atom',draw_customise_add,''],
		['q','back to visualisation menu',draw,'']
		])

def draw_customise_add():
	newatom=[]
	#998 make a way to get these all on one screen
	newatom.append(ui.inputscreen('                     element:','string'))
	newatom.append(ui.inputscreen('              visible? (y/n):','yn'))
	#only need to get values for other stuff if the atom is visible
	if newatom[1] == 'yes':
		newatom.append(ui.inputscreen(' colour (0,0,0) <= (R,G,B) <= (255,255,255), blank for default:','intlist',0,255,number=3))
		newatom.append(ui.option([
			['d','default size',False,'0.05 x scale'],
			['r','relative to 0.05 x scale',False,''],
			['n','nm',False,'nanometre'],
			['m','m',False,'metre'],
			['a',lang.angstrom,False,'angstrom']
			], 'Choose an atomic size unit:'))
		#if it's not the default, get a number
		if newatom[3] != 'd':
			newatom.append(ui.inputscreen('   size:','float',0,eqmin=False,notblank=True))
		#if it is default, no size number required
		else:
			newatom.append(False)
		newatom.append(ui.inputscreen('opacity (blank for default):','float',0,1))
	#if creating an invisible atom, add defaults to other fields
	else:
		newatom.append(False) #default colour
		newatom.append('d') #default size
		newatom.append(False) #numerical size not needed
		newatom.append(False) #default opacity
	#load the old atoms
	draw_data = load_current('draw')
	if draw_data.has_key('atoms'):
		atoms = draw_data['atoms']
	else:
		atoms = []
	atoms.append(newatom)
	update_value('draw','atoms',atoms)
	return draw_customise_atoms

def draw_customise_delete():
	draw_data = load_current('draw')
	atoms = draw_data['atoms']
	atoms_data = draw_atoms_table()
	if len(atoms) > 1:
		query = 'Delete which customisation? (1-'+str(len(atoms))+', blank to cancel)'
	else:
		query =  'There is only one customisation. Enter 1 to confirm deletion, or leave blank to cancel:'
	kill_me = ui.inputscreen(query,'int',1,len(atoms))
	if kill_me is not False:
		del atoms[kill_me-1]
		update_value('draw','atoms',atoms)
	return draw_customise_atoms

def draw_customise_edit():
	draw_data = load_current('draw')
	atoms = draw_data['atoms']
	atoms_data = draw_atoms_table()
	if len(atoms) > 1:
		query = 'Edit which atom? (1-'+str(len(atoms))+')'
		edit_me = ui.inputscreen(query,'int',1,len(atoms),text=atoms_data) - 1 #arrays start at zero
	else:
		edit_me = 0
	atom = []
	atom.append(ui.inputscreen('          element (blank for '+atoms[edit_me][0]+'):','string'))
	if atom[0] is False:
		atom[0] = atoms[edit_me][0]
	if atoms[edit_me][1]:
		default_val = 'yes'
	else:
		default_val = 'no'
	atom.append(ui.inputscreen(' visible? (y/n, blank for '+default_val+'):','yn'))
	if atom[1] is False:
		atom[1] = default_val
	#only need to get values for other stuff if the atom is visible
	if atom[1] == 'yes':
		atom.append(ui.inputscreen(' colour 0,0,0 <= R,G,B <= 255,255,255 or blank for default:','intlist',0,255,number=3))
		atom.append(ui.option([
			['d','default size',False,'0.05 x scale'],
			['r','relative to 0.05 x scale',False,''],
			['n','nm',False,'nanometre'],
			['m','m',False,'metre'],
			['a',lang.angstrom,False,'angstrom']
			], 'Choose an atomic size unit:'))
		#if it's not the default, get a number
		if atom[3] != 'd':
			atom.append(ui.inputscreen('   size:','float',0,eqmin=False,notblank=True))
		#if it is default, no size number required
		else:
			atom.append(False)
		atom.append(ui.inputscreen(' opacity (blank for default):','float',0,1))
	for i in range(len(atom)):
		atoms[edit_me][i] = atom[i]
	update_value('draw','atoms',atoms)
	return draw_customise_atoms

def draw_field():
	draw_data = load_current('draw')
	menu_data = {}
	if draw_data.has_key('field_filename'):
		menu_data['filename'] = draw_data['field_filename']
	else:
		menu_data['filename'] = lang.red+'not set'+lang.reset
	if draw_data.has_key('omega_minmax'):
		menu_data['omega_minmax'] = omega_minmax_to_string(draw_data['omega_minmax'])+' MHz'
	else:
		menu_data['omega_minmax'] = lang.red+'not set'+lang.reset
	if draw_data.has_key('field_colours'):
		if draw_data['field_colours'] == 'rainbow': #or other valid values
			menu_data['field_colours'] = draw_data['field_colours']
		else:
			menu_data['field_colours'] = lang.red+'not set'+lang.reset #can't see how this would happen, but better than a crash!
	else:
		menu_data['field_colours'] = lang.red+'not set'+lang.reset #can't see how this would happen, but better than a crash!
	menuoptions = [
	['f','filename',draw_field_filename,menu_data['filename']],
	['r','range(s)',draw_field_ranges,menu_data['omega_minmax']],
	['c','colours',draw_field_colours,menu_data['field_colours']]
	]
	if draw_data.has_key('field_filename') and draw_data.has_key('omega_minmax'):
		if draw_data['field_visible']:
			visible_menu_text = 'do not draw'
			visible_menu_info = 'currently shown'
		else:
			visible_menu_text = 'draw'
			visible_menu_info = 'currently hidden'
		menuoptions.append(['d',visible_menu_text,draw_field_yesno,visible_menu_info])
	menuoptions.append(['q','back to visualisation menu',draw,''])
	return ui.menu(menuoptions,ui.heading('Field visualisation menu'))
	
def draw_field_filename():
	draw_data = load_current('draw')
	if draw_data.has_key('field_filename'):
		default_filename = draw_data['field_filename']
	else:
		default_filename=''
	directory = 'output'
	suffix = '-dipole-field.tsv'
	filename = ui.get_filename(directory,suffix,default_filename,file_description='of your dipole field file')
	update_value('draw','field_filename',filename)
	return draw_field

def draw_field_colours():
	a = ui.option([
	['r','rainbow',False,'']
	])
	#if it's not blank, update the value
	if a == 'r':
		update_value('draw','field_colours','rainbow')
	return draw_field

def draw_field_ranges():
	draw_data = load_current('draw')
	if draw_data.has_key('omega_minmax'):
		omega_minmax_to_draw = ui.inputscreen('Please enter a comma-separated list of omega_min,omega_max,min,max,min,max… (MHz, blank for \''+omega_minmax_to_string(draw_data['omega_minmax'])+' MHz\'):','floatlist',notblank=False,validate=omega_minmax_str_explode) #[1:-1] is a dirty way to trim the brackets
	else:
		omega_minmax_to_draw = ui.inputscreen('Please enter a comma-separated list of omega_min,omega_max,min,max,min,max… to draw (MHz):','floatlist',0,notblank=True,validate=omega_minmax_str_explode)
	update_value('draw','omega_minmax',omega_minmax_to_draw)
	return draw_field

def draw_field_yesno():
	return option_toggle('draw','field_visible',draw_field)

def draw_3d():
	a = ui.option([
	['n','no stereo',False,''],
	['r','red-cyan',False,'requires red-cyan 3D specs'],
	['b','red-blue',False,'requires red-blue 3D specs'],
	['y','yellow-blue',False,'requires yellow-blue 3D specs']
	])
	#if it's not blank, update the value
	if a != '':
		update_value('draw','stereo_3d',a)
	return draw

def draw_save():
	return save_output('draw','visualisation settings','output','-visual',draw)

def draw_load():
	return load_output('draw','visualisation settings','output','-visual',draw)

def draw_povexport():
	global visual_window
	global visual_window_contents
	doexport = False
	while True:
		directory = 'output'
		filename = ui.inputscreen('Please enter a filename for your POV-ray file:','str',notblank=True)
		full_filename = directory+'/'+filename+'.pov'
		if os.path.exists(full_filename):
			if ui.inputscreen('File \''+full_filename+'\' exists. Overwrite?','yn') == 'yes':
				doexport = True
				break
		else:
			doexport = True
			break
	if doexport:
		print 'Exporting to POV-Ray...'
		povexport.export(display=visual_window, filename=full_filename, include_list=None, xy_ratio=4./3., custom_text='', shadowless=True)
	return draw

def muhelp():
	return ui.menu([
	['q','back to main menu',main_menu,'']
	],'See http://andrewsteele.co.uk/physics/mmcalc/docs/ for documentation.'+
	lang.newline+'Alternatively, contact the author at mmcalc@andrewsteele.co.uk')

def main():
	current_menu = main_menu
	while 1:
		current_menu = current_menu()

#starting the main loop boots up the whole program
main()