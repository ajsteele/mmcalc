# coding=utf-8
# MmCalc--a muon-orientated dipole field calculating program
# http://andrewsteele.co.uk/mmcalc/
# VERSION 1.1.development

# this code is commented with markers for things which need improving/would be nice. Simply search for the numbers.
# 999 - need
# 998 - would be nice

# import these standard Python modules
import os
import platform
import time
import re              # regular expressions

# import mmcalc files
import ui              # user interface functions
import langen as lang  # the internationalisation file...change langen to a different filename, but always import as lang
import config          # configuration values

# numpy needs to be installed
# 998 - should this try to import Numeric? Does that work too?
try:
	import numpy as np
except:
	ui.fatalerror(lang.err_numpy)

# JSON support is only built-in by default after Python 2.6
try:
	import simplejson as json
except ImportError:
	try:
		import json
	except:
		ui.fatalerror(lang.err_json)

# PyCifRW reads and writes CIF files, and is optional because it's tricky to install
try:
	import CifFile
	cif_support = True
except ImportError:
	cif_support = False #this flag indicates that the import cif option should not be included on the crystal menu

# these modules are all distributed with MmCalc so should just work...
import sg
import difn
import difast
import didraw
import csc
import povexport

# clear the console
ui.clear()

# initialise global variables for the visualisation window
visual_window = None
visual_window_contents = None

# first-run initialisation: check for the presence of the current/ and
# output/ directories, and create them if absent.
for dir in [config.current_dir,config.output_dir]:
    if not(os.path.isdir(dir)):
        os.mkdir(dir)

# from http://effbot.org/zone/python-list.htm this finds all occurrences of value in a Python list
# it's a generator--hence use of yield--and so should be used as in for stuff in findall(L, x) etc...
def findall(L, value, start=0):
	i = start - 1
	try:
		i = L.index(value, i+1)
		yield i
	except ValueError:
		pass

# JSON is not able to serialise complex number objects. These custom functions change any errant complex numbers into a dictionary, which JSON can encode
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
	if os.path.exists(config.current_dir+'/'+'session'+'.json'):
		allstuff = json_custom_load(config.current_dir+'/'+'session'+'.json')
		allstuff[variablename] = stuff
	else:
		allstuff={variablename:stuff}
	json_custom_save(config.current_dir+'/'+'session'+'.json',allstuff)

def load_current(variablename):
	#check if the file exists
	if os.path.exists(config.current_dir+'/'+'session'+'.json'):
		stuff = json_custom_load(config.current_dir+'/'+'session'+'.json')
		if stuff.has_key(variablename):
			return stuff[variablename]
	#if not, just return a blank dictionary
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
	return True

def option_toggle(dictionaryname,key,goto):
	data = load_current("draw")
	if data[key]:
		a = False
	else:
		a = True
	update_value(dictionaryname,key,a)
	return goto

# get_length_unit
# --------------------------
# Turns the stored string representing which length unit to use into a premultiplication factor and a human-readable string.
# ---
# INPUT
# stored_val = the string stored...usually passed as crystal_data['length_unit'], which can be 'n', 'a' or 'm'
# ---
# OUTPUT
# the premultiplier = 1e-9, 1e-10 or 1
# human-readable form = nm, angstrom symbol or m
def get_length_unit(stored_val):
	if stored_val == 'n':
		return difn.nano, lang.nm
	elif stored_val == 'a':
		return difn.angstrom, lang.angstrom
	else:
		return 1.0, lang.m

# labels2elements
# --------------------------
# Receives a list of atom labels (eg F1, Cu124 etc) and returns just the element string at the beginning, or the string itself if there is no element-like string present.
# ---
# INPUT
# names = a list of atoms' names
# ---
# OUTPUT
# names = cleaned-up list of atom element names
def labels2elements(names):
	element_pattern = re.compile('[A-Z][a-z]?') #matches a capital, optionally followed by a lower-case
	#go through the names, stripping anything which doesn't match
	for i in range(len(names)):
		element_name = element_pattern.match(names[i]).group(0)
		#only update if an element name is found...
		if element_name is not None:
			names[i] = element_name
	return names

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
			menu_data['length_unit'] = lang.nm
		elif crystal_data['length_unit'] == 'm':
			menu_data['length_unit'] = lang.m
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
	menu = [
	['s','space group',space_group,menu_data['space_group']],
	['u','length unit',length_unit,menu_data['length_unit']],
	['a','a',a,menu_data['a']],
	['b','b',b,menu_data['b']],
	['c','c',c,menu_data['c']],
	['1',lang.alpha,alpha,menu_data['alpha']],
	['2',lang.beta,beta,menu_data['beta']],
	['3',lang.gamma,gamma,menu_data['gamma']],
	['t','atoms',atoms_menu,menu_data['atoms']],
	['m','magnetic properties',magnetic_properties_menu,''],
	['d','draw crystal',draw_crystal,''],
	['v','save crystal',save_crystal,''],
	['l','load crystal',load_crystal,'']
	]
	if cif_support:
		menu.append(['i','import CIF',import_cif,''])
	menu.append(['q','back to main menu',main_menu,''])
	return ui.menu(menu)

def import_cif():
	if ui.inputscreen('Do you wish to unload current crystal structure?','yn') == 'yes':
		error = ''
		while True:
			filename = ui.inputscreen('Enter CIF filename to load:','str',notblank=True,text=error)
			full_filename = config.output_dir+'/'+filename
			if os.path.exists(full_filename):
				break
			else:
				error = lang.red+'File '+full_filename+' does not exist.'+lang.reset
	cif_file = CifFile.ReadCif(full_filename)
	cifblock = []
	for block in cif_file.items():
		# if it's got the items we need in the block
		block_has_all_keys = False #presume initially that it doesn't
		if (cif_file[block[0]].has_key('_symmetry_space_group_number') or cif_file[block[0]].has_key('_symmetry_space_group_name_H-M')):
			needed_keys = ['_atom_site_label','_cell_length_a','_cell_length_b','_cell_length_c','_cell_angle_alpha','_cell_angle_beta','_cell_angle_gamma']
			block_has_all_keys = True
			for k in needed_keys:
				if not cif_file[block[0]].has_key(k):
					block_has_all_keys = False
					break
		if block_has_all_keys:
			cifblock.append(block[0])
	
	crystal_data = {}
	# if there are no good blocks
	if len(cifblock) == 0:
		return ui.menu([
		['q','back to crystal menu',crystal,'']
		],'There are no suitable blocks in the CIF provided.')
	# if there are multiple blocks which validate naively as above, offer the user a choice
	elif len(cifblock) > 1:
		options = []
		for i in range(len(cifblock)):
			options.append([str(i),cifblock[i],False,''])
		options.append('There are several blocks of data in the CIF which seem to be appropriate. Please choose one.')
		a = ui.option(options,notblank=True)
		cifblock = cif_file[cifblock[i-1]]
	# otherwise, no choice is necessary
	else:
		cifblock = cif_file[cifblock[0]]

	# loop through a,b,c,alpah etc and get their values
	nononnumchars = re.compile('[0-9.]+') #need to remove brackets if there are any to make it floatable
	crystal_data['length_unit'] = 'n'
	crystal_data['a'] = float(nononnumchars.match(cifblock['_cell_length_a']).group(0))/10. #divide by ten to turn angstroms (the standard) into nm
	crystal_data['b'] = float(nononnumchars.match(cifblock['_cell_length_b']).group(0))/10.
	crystal_data['c'] = float(nononnumchars.match(cifblock['_cell_length_c']).group(0))/10.
	crystal_data['alpha'] = float(nononnumchars.match(cifblock['_cell_angle_alpha']).group(0))
	crystal_data['beta'] = float(nononnumchars.match(cifblock['_cell_angle_beta']).group(0))
	crystal_data['gamma'] = float(nononnumchars.match(cifblock['_cell_angle_gamma']).group(0))

	space_group_valid = False
	space_group_number = False
	space_group_HM = False
	# try for space group number: probably the safest way to extract the space group
	if cifblock.has_key('_symmetry_space_group_number'):
		#look up the space group
		space_group_number = cifblock['_symmetry_space_group_number']
		space_group_valid, error = sg_validate(space_group_number)
		space_group = sg.get_sg(space_group_number)
	#if there's no space group number, try the Hermann-Mauguin symbol
	if space_group_valid is False and cifblock.has_key('_symmetry_space_group_name_H-M'):
		# check the space group works
		space_group_HM = cifblock['_symmetry_space_group_name_H-M']
		space_group_valid, error = sg_validate(space_group_HM)
		space_group = sg.get_sg(space_group_HM)
	#if one of those worked and returned a valid space group
	if space_group_valid is not False:
		#turn it into a space group name and number
		if len(space_group) > 1:
			#if the choice is 'unique axis b' or 'unique axis c', the program can work this out on its own!
			if space_group[0]['setting'] == 'unique axis b':
				if crystal_data['beta'] != 90:
					setting = 1
				else: #if not, or if the test doesn't work, guess unique axis c
					setting = 2
			else:
				setting = choose_setting(space_group)
		else:
			setting = 1
		space_group = space_group[setting-1] # subtract 1 because Python indices start at 0
	else:
		#throw an error and ask the user for help
		sginfo = ''
		if space_group_number is not False:
			sginfo += 'Number: '+space_group_number+lang.newline
		if space_group_HM is not False:
			sginfo += 'Symbol: '+space_group_HM+lang.newline
		space_group = ui.inputscreen('Type a space group name or number:',validate=sg_validate,notblank=True,text='The space group information in the CIF is not intelligible to me! Here is what the CIF says, can you please tell me what it means?'+lang.newline+lang.newline+sginfo)
		#turn it into a space group name and number
		space_group = sg.get_sg(space_group)
		if len(a) > 1:
			setting = choose_setting(space_group)
		else:
			setting = 1
		space_group = space_group[setting-1] # subtract 1 because Python indices start at 0
	
	crystal_data['space_group'] = space_group['number']
	crystal_data['space_group_name'] = space_group['name']
	crystal_data['space_group_setting'] = space_group['setting']
	
	#ask user if they want elements or labels to be imported
	#999
	
	
	# loop through the atoms and collect their info
	crystal_data['atoms'] = []
	for i in range(len(cifblock['_atom_site_label'])):
		crystal_data['atoms'].append([cifblock['_atom_site_label'][i],float(nononnumchars.match(cifblock['_atom_site_fract_x'][i]).group(0)),float(nononnumchars.match(cifblock['_atom_site_fract_y'][i]).group(0)),float(nononnumchars.match(cifblock['_atom_site_fract_z'][i]).group(0)),0])
		#set charge to zero because CIF file doesn't tell you that...
	
	save_current('crystal',crystal_data)
	
	return crystal

def crystal_length(axis):
	#998 more complex constraints based on space group?
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
		return np.int(ui.option(spacegroups_menu,True),'This space group ('+spacegroups[0]['name']+') has multiple settings. Please choose the appropriate one.')

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
			atom_row.append(atom[0]) # element
			atom_row.append(str(atom[1])) # x
			atom_row.append(str(atom[2])) # y
			atom_row.append(str(atom[3])) # z
			atom_row.append(ui.charge_str(atom[4])) # q
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
	atom.append(ui.inputscreen('    element (blank for '+str(atoms[edit_me-1][0])+'):','string',newscreen=False))
	atom.append(ui.inputscreen('          x (blank for '+str(atoms[edit_me-1][1])+'):','float',0,1,newscreen=False))
	atom.append(ui.inputscreen('          y (blank for '+str(atoms[edit_me-1][2])+'):','float',0,1,newscreen=False))
	atom.append(ui.inputscreen('          z (blank for '+str(atoms[edit_me-1][3])+'):','float',0,1,newscreen=False))
	atom.append(ui.inputscreen('       q (e) (blank for '+str(atoms[edit_me-1][4])+'):','int',newscreen=False))
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
			row.append(ui.complex_str(component))
		table_array.append(row)
		i += 1
	return ui.table(table_array)

def generated_atoms_table(crystal_data):
	#load (and print out) any already-existent atom data
	if crystal_data.has_key('generated_atoms'):
		atoms = crystal_data['generated_atoms']
		properties = crystal_data['generated_atoms_properties']
		atoms_table_array = []
		atoms_table_array.append(['#','element','x','y','z','q','m','k']) #998 lang.bold+'m'+lang.reset,lang.bold+'k'+lang.reset]) #it would be nice to make this bold, but the column length counter doesn't ignore control codes at the moment so they just appear as ellipses
		for i in range(len(atoms)):
			atom_row = []
			atom_row.append(str(i+1))
			atom_row.append(atoms[i][0]) # element
			atom_row.append(str(atoms[i][1])) # x
			atom_row.append(str(atoms[i][2])) # y
			atom_row.append(str(atoms[i][3])) # z
			atom_row.append(ui.charge_str(atoms[i][4])) # q
			atom_row.append(ui.list_str(properties[i][0])) # m
			atom_row.append(ui.list_str(properties[i][1])) # k
			atoms_table_array.append(atom_row)
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

def add_m():
	newm=[]
	newm.append(ui.inputscreen(lang.add_mx,'complex',notblank=True,newscreen=False))
	newm.append(ui.inputscreen(lang.add_my,'complex',notblank=True,newscreen=False))
	newm.append(ui.inputscreen(lang.add_mz,'complex',notblank=True,newscreen=False))
	#load the old atoms
	crystal_data = load_current('crystal')
	if crystal_data.has_key('m'):
		m = crystal_data['m']
	else:
		m = []
	m.append(newm)
	update_value('crystal','m',m)
	#and go through adding 1 to any references to k-vectors in the atoms
	for i in range(len(crystal_data['generated_atoms_properties'])):
		n_vectors = len(crystal_data['generated_atoms_properties'][i][0])
		if n_vectors >0:
			for j in range(n_vectors):
				crystal_data['generated_atoms_properties'][i][1][j] += 1
	update_value('crystal','generated_atoms_properties',crystal_data['generated_atoms_properties'])
	return magnetic_properties_menu
	
def add_k():
	newk=[]
	#998 is it always true that |k|/pi <= 0.5 because it should be in the first BZ?
	newk.append(ui.inputscreen(lang.add_kx,'complex',notblank=True,newscreen=False))
	newk.append(ui.inputscreen(lang.add_kx,'complex',notblank=True,newscreen=False))
	newk.append(ui.inputscreen(lang.add_kx,'complex',notblank=True,newscreen=False))
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
			#and go through removing references to that m-vector, the corresponding k-vector, and subtracting 1 from any references to k-vectors in the atoms
			for i in range(len(crystal_data['generated_atoms_properties'])):
				n_vectors = len(crystal_data['generated_atoms_properties'][i][0])
				if n_vectors > 0:
					for j in findall(crystal_data['generated_atoms_properties'][i][0],kill_me):
						del crystal_data['generated_atoms_properties'][i][0][j] #delete m item on list
						del crystal_data['generated_atoms_properties'][i][1][j] #delete corresponding k
					n_vectors = len(crystal_data['generated_atoms_properties'][i][0]) #re-measure after deletions
					for j in range(n_vectors):
						#if the m-vector value is greater than the one just deleted, subtract 1
						if crystal_data['generated_atoms_properties'][i][0][j] > kill_me:
							crystal_data['generated_atoms_properties'][i][0][j] -= 1
						# all k numbers are > m numbers, so subtract 1 regardless
						crystal_data['generated_atoms_properties'][i][1][j] -= 1
			update_value('crystal','generated_atoms_properties',crystal_data['generated_atoms_properties'])
		else:
			del k[kill_me-len(m)-1]
			update_value('crystal','k',k)
			#go through removing references to that k-vector and the corresponding m-vector
			for i in range(len(crystal_data['generated_atoms_properties'])):
				n_vectors = len(crystal_data['generated_atoms_properties'][i][0])
				if n_vectors > 0:
					for j in findall(crystal_data['generated_atoms_properties'][i][1],kill_me):
						del crystal_data['generated_atoms_properties'][i][1][j] #delete k item on list
						del crystal_data['generated_atoms_properties'][i][0][j] #delete corresponding m
					#if the k-vector value is greater than the one just deleted, subtract 1
					n_vectors = len(crystal_data['generated_atoms_properties'][i][0]) #re-measure after deletions
					for j in range(n_vectors):
						if crystal_data['generated_atoms_properties'][i][1][j] > kill_me:
							crystal_data['generated_atoms_properties'][i][1][j] -= 1
			update_value('crystal','generated_atoms_properties',crystal_data['generated_atoms_properties'])
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
			newm.append(ui.inputscreen(lang.edit_mx_1+str(m[edit_me-1][0])+lang.edit_m_2,'complex',newscreen=False))
			newm.append(ui.inputscreen(lang.edit_my_1+str(m[edit_me-1][1])+lang.edit_m_2,'complex',newscreen=False))
			newm.append(ui.inputscreen(lang.edit_mz_1+str(m[edit_me-1][2])+lang.edit_m_2,'complex',newscreen=False))
			for i in range(len(newm)):
				if newm[i] is not False:
					m[edit_me-1][i] = newm[i]
			update_value('crystal','m',m)
		else:
			newk = []
			newk.append(ui.inputscreen(lang.edit_kx_1+str(k[edit_me-len(m)-1][0])+lang.edit_k_2,'complex',newscreen=False))
			newk.append(ui.inputscreen(lang.edit_ky_1+str(k[edit_me-len(m)-1][1])+lang.edit_k_2,'complex',newscreen=False))
			newk.append(ui.inputscreen(lang.edit_kz_1+str(k[edit_me-len(m)-1][2])+lang.edit_k_2,'complex',newscreen=False))
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
	if edit_me is not False:
		#the actual internal array starts at zero, so subtract the offset
		edit_me -= 1
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
	atoms_names = labels2elements(atoms_names)
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
	names_i = labels2elements(names_i)
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
	'atoms_mu':didraw.vector_field(r_i,mu_i,0,0,'white','proportional',scale)}
	update_value('draw','scale',scale)
	
def draw_draw(silent='False'):
	global visual_window
	global visual_window_contents
	draw_data = load_current('draw')
	L = draw_data['L']
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
	names_i = labels2elements(names_i)
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
	# change the camera direction if necessary
	if draw_data.has_key('camera_direction'):
		draw_change_camera_direction(draw_data['camera_direction'],True)
	visual_window.visible = True
	visual_window.center = ((a_cart[0]*L[0]+a_cart[1]*L[1]+a_cart[2]*L[2])*0.5)
	visual_window_contents = {}
	if draw_data['unitcell']:
		if not silent:
			ui.message('Drawing unit cell boundary...')
		visual_window_contents['unitcell'] = didraw.unitcell_init(a_cart,scale)
	if True: #you can't currently turn off atoms 999
		if not silent:
			ui.message('Drawing atoms...')
		visual_window_contents['atoms']= didraw.draw_atoms(r_i,names_i,q_i,mu_i,draw_data['atom_colours'],scale,atom_custom)
	if draw_data['moments']:
		if not silent:
			ui.message('Drawing magnetic moments...')
		visual_window_contents['atoms_mu'] = didraw.vector_field(r_i,mu_i,0,0,'fadetoblack','proportional',scale)
	#if the field is visible, load it and draw it
	if draw_data['field_visible']:
		title, values, error = csc.read(config.output_dir+'/'+draw_data['field_filename']+'-dipole-field.tsv') #998 do something with error?
		if not silent:
			ui.message('Drawing dipole field of '+'\''+title+'\'...')
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
			if ui.inputscreen('Your chosen minimum and maximum values will result in '+str(len(r_to_draw))+' field points being drawn. I strongly suggest you don\'t. Continue?','yn',newscreen=False) == 'no':
				do_draw = False #stop drawing the if user doesn't want computer-crippling-ness
			else:
				if ui.inputscreen('Drawing '+str(len(r_to_draw))+' points is REALLY NOT RECOMMENDED. Sure?','yn',newscreen=False) == 'no':
					do_draw = False #stop drawing the if user doesn't want computer-crippling-ness
		elif len(r_to_draw) > 10000:
			if ui.inputscreen('Your chosen minimum and maximum values will result in '+str(len(r_to_draw))+' field points being drawn. This may cause your computer to run slowly. Continue?','yn',newscreen=False) == 'no':
				do_draw = False #stop drawing the if user doesn't want computer-crippling-ness
		if do_draw:
			visual_window_contents['dipole_field'] = didraw.vector_field(r_to_draw,B_to_draw,B_minmin,B_maxmax,draw_data['field_colours'],0.2,scale)
	if draw_data.has_key('bonds') and draw_data['bonds_visible']:
		if not silent:
			ui.message('Drawing bonds...')
		bonds_to_draw = generate_bonds()
		# though this uses the speed of numpy arrays, we can't do the whole thing with them because they force you to
		#predefine a type, and don't allow you to change array dimensions. The problem with this is that some elements can
		#be a vector, some a scalar, and some a boolean, eg colour can be [r,g,b] or False
		visual_window_contents['bonds'] = didraw.bonds(bonds_to_draw,scale)
	# kill any atoms and bonds on death row
	if draw_data.has_key('kill') and len(draw_data['kill']) > 0:
		if not silent:
			ui.message('Killing unnecessary objects...')
		for death in draw_data['kill']:
			if death[0]=='atom':
				draw_kill_atom(death[1])
			elif death[0]=='bond':
				draw_kill_bond(death[1])
			elif death[0]=='atom_mass' or death[0]=='bond_mass':
				draw_kill_mass_do(death)

def draw_magnetic_unit_cell_from_crystal():
	draw_magnetic_unit_cell()
	return draw_crystal

def save_crystal():
	return save_output('crystal','crystal structure',config.output_dir,'-crystal-structure',crystal)

def load_crystal():
	return load_output('crystal','crystal structure',config.output_dir,'-crystal-structure',crystal)

# dipole
# --------------------------
# The dipole menu for setting up and performing dipole field calculations
def dipole():
	dipole_data = load_current('dipole')
	crystal_data = load_current('crystal')
	menu_data = {}
	if dipole_data.has_key('r_sphere'):
		menu_data['v_size'] = 'r='+str(dipole_data['r_sphere'])
	else:
		menu_data['v_size'] = lang.red+'not set'+lang.reset
	if dipole_data.has_key('pointgen'):
		if dipole_data['pointgen'] == 'g':
			menu_data['points'] = 'grid; n_a='+str(dipole_data['n_a'])+', n_b='+str(dipole_data['n_b'])+', n_c='+str(dipole_data['n_c'])
		elif dipole_data['pointgen'] == 'm':
			menu_data['points'] = 'Monte Carlo; n='+str(dipole_data['n_monte'])
		elif dipole_data['pointgen'] == 's':
			if dipole_data.has_key('points'):
				menu_data['points'] = str(len(dipole_data['points']))+' specified manually'
			else:
				menu_data['points'] = ''
	else:
		menu_data['points'] = lang.red+'not set'+lang.reset
	if dipole_data.has_key('constraints') and len(dipole_data['constraints']) > 0 and crystal_data.has_key('length_unit'):
		length_unit, length_unit_name = get_length_unit(crystal_data['length_unit'])
		menu_data['constraints'] = constraints_readable(dipole_data['constraints'],length_unit_name)
	else:
		menu_data['constraints'] = lang.red+'not set'+lang.reset

	return ui.menu([
#	['s','vcrystal shape',dipole_vcrystal_shape,'only spherical possible at the moment'],#998 is there any point in this?
	['c','convergence test',dipole_convergence_test,''],
	['z','vcrystal size',dipole_vcrystal_size,menu_data['v_size']],
	['p','points',dipole_points,menu_data['points']],
	['m','muon site constraints',dipole_constraints,menu_data['constraints']],
	['e','evaluate dipole field by direct summation',calculate_dipole,''],
#	['s','symmetry eqv',dipole_symmetry_eqv,''], #998
	['d','draw dipole field',draw_dipole,''],
#	['f','draw frequencies',draw_freq,''], #998
	['h','histogram of frequencies',histo_freq,''],
	['q','back to main menu',main_menu,'']
	])

def dipole_vcrystal_shape():
	pass #998 add this feature?

#999 check this function actually works!!
#998 merge with Monte Carlo NumPy function?
#998 apply constraints if they're set?
def generate_random_position(r,a,tolerance):
	sorted = False
	tolerance2 = tolerance*tolerance
	while not(sorted):
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

# dipole_convergence_test
# --------------------------
# A UI function on the dipole menu
# ---
# Try a range of different virtual crystal sizes to evaluate accuracy and time taken for each size
# 998 - allow some user-specification of which sizes to try?
# 998 - allow user-specified points to test?
def dipole_convergence_test():
	global visual_window
	global visual_window_contents
	t_begin = time.clock()
	#draw_data = load_current('draw') #doesn't seem to be used? 999
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
	scale = draw_default_scale()
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
		# create vcrystal
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
			'atoms':didraw.draw_atoms(r,name,q,mu,'e',scale,{}), # draw completely standard, coloured by element etc, to avoid hiding points
			}
		# do dipole fields at the various points
		for i in range(len(r_test)):
			t_start = time.clock()
			r_test_fast = difast.reshape_vector(r_test[i]) #998 bit inefficient to calculate this every time
			B[radius][i] = difast.calculate_dipole(r_test_fast, r_fast, mu_fast)
			t_stop = time.clock()
			omega[radius][i] = difn.gyro(B[radius][i])
			t[radius][i] = t_stop - t_start
			error[radius][i] = np.abs(np.round((omega[radius][i]-omega_perfect[i])/omega_perfect[i],decimals=4))*100
	table_array = [[lang.conv_vcrystal_radius,lang.conv_error,lang.conv_time_estimate]]
	for radius in range(1,r_max):
		row = [str(radius)]
		sum_t = 0
		sum_err = 0
		for i in range(len(r_test)):
			sum_err += error[radius][i]
			sum_t += t[radius][i]
		row.append(str(sum_err/np.float(len(r_test)))[:5]+' %')
		row.append(ui.s_to_hms(sum_t*lang.conv_n_points/np.float(len(r_test)))) #time for 1,000,000 iterations
		table_array.append(row)
	t_end = time.clock()
	
	return ui.menu([
	['q','back to dipole menu',dipole,'']
	],ui.table(table_array)+'Convergence test completed in '+ui.s_to_hms(t_end-t_begin))

# dipole_vcrystal_size
# --------------------------
# A user input function on the dipole menu
# ---
# Specify the size of the virtual crystal to use in dipole field calculations by direct summation
# 998 - allow user to specify lengths in units other than a
# 998 - allow different vcrystal shapes?
def dipole_vcrystal_size():
	a = ui.inputscreen('Type radius of virtual crystal sphere (units of a):','int',0,eqmin=False)
	if a is not False:
		update_value('dipole','r_sphere',a)
	return dipole

# dipole_points
# --------------------------
# A user input function on the dipole menu
# ---

# Obtain both the method of points generation (on a grid, or Monte Carlo), and how many points to use
# 998 - also specify how many unit cells here? eg magnetic, crystal, other...
#straight_to_point allows jumping straight to the specify points menu if that's the user's method of point selection
#it's set to false when you request this dipole_points menu from within specify_points so you get to select a new option...
def dipole_points(straight_to_point = True): 
	dipole_data = load_current('dipole')
	# if it's unset, or it's set to grid or MC, offer up the conventional set of options
	if not straight_to_point or not dipole_data.has_key('pointgen') or dipole_data['pointgen'] == 'g' or dipole_data['pointgen'] == 'm':
		pointgen = ui.option([
				['g','grid',False,''],
				['m','Monte Carlo',False,''],
				['s','specify single points',False,'']
				], 'Choose a method of point generation:')
		update_value('dipole','pointgen',pointgen)
		if pointgen == 'g':
				for axis in ['a','b','c']:
					if dipole_data.has_key('n_'+axis):
						a = ui.inputscreen('Number of points on the '+axis+'-axis (blank for '+str(dipole_data['n_'+axis])+'):','int',0,eqmin=False,notblank=False)
					else:
						a = ui.inputscreen('Number of points on the '+axis+'-axis:','int',0,eqmin=False,notblank=True)
					if a is not False:
						update_value('dipole','n_'+axis,a)
		elif pointgen == 'm':
			if dipole_data.has_key('n_monte'):
				a = ui.inputscreen('Number of points to evaluate (blank for '+str(dipole_data['n_monte'])+'):','int',0,eqmin=False,notblank=False)
			else:
				a = ui.inputscreen('Number of points to evaluate:','int',0,eqmin=False,notblank=True)
			if a is not False:
				update_value('dipole','n_monte',a)
		# if they want to specify points, take them there
		elif pointgen == 's':
			return dipole_points_specify
	# if they've specified points, take them there by default
	else:
		return dipole_points_specify
	return dipole

# this is a kludge to call dipole_points with False from within the menus in dipole_points_specify
# putting dipole_points(False) into the menu executes the function
# 998 is there a better way?
def dipole_points_notstraight():
	return dipole_points(False)

def dipole_points_table():
	#load (and print out) any already-existent atom data
	dipole_data = load_current('dipole')
	if dipole_data.has_key('points'):
		points = dipole_data['points']
		points_table_array = []
		points_table_array.append(['#','x','y','z'])
		i = 1
		for point in points:
			point_row = []
			point_row.append(str(i))
			point_row.append(str(point[0])) # x
			point_row.append(str(point[1])) # y
			point_row.append(str(point[2])) # z
			points_table_array.append(point_row)
			i += 1
		return ui.table(points_table_array)
	else:
		return ''

def dipole_points_specify():
	dipole_data = load_current('dipole')
	#if there are atoms
	if dipole_data.has_key('points') and len(dipole_data['points']) != 0:
		return ui.menu([
		['a','add point',add_point,''],
		['d','delete point',delete_point,''],
		['x','generate points by different method',dipole_points_notstraight,''],
		['q','back to dipole menu',dipole,'']
		],dipole_points_table())
	#if none has been set yet
	else:
		return ui.menu([
		['a','add point',add_point,''],
		['x','generate points by different method',dipole_points_notstraight,'']
		])

def add_point():
	newpoint = ui.inputscreen('  x, y, z (fractional coordinates, separated by commas):','floatlist',notblank=True,number=3)
	#load the old atoms
	dipole_data = load_current('dipole')
	if dipole_data.has_key('points'):
		points = dipole_data['points']
	else:
		points = []
	points.append(newpoint)
	update_value('dipole','points',points)
	return dipole_points_specify

def delete_point():
	dipole_data = load_current('dipole')
	points = dipole_data['points']
	points_data = dipole_points_table()
	if len(points) > 1:
		query = 'Delete which point? (1-'+str(len(points))+', blank to cancel)'
	else:
		query =  'There is only one point. Enter 1 to confirm deletion, or leave blank to cancel:'
	kill_me = ui.inputscreen(query,'int',1,len(points))
	if kill_me is not False:
		del points[kill_me-1]
		update_value('dipole','points',points)
	return dipole_points_specify

# generate_grid
# --------------------------
# Generates a 3D grid of equally-spaced-in-fractional-coordinates points in the unit cell.
# ---
# INPUT
# a_cart = array of three three-component vectors: the primitive translation vectors in cartesian coordinates (m)
# L = three-component array describing the volume of the grid to be generated, eg 1x1x1 implies crystallographic unit cell; other values could include magnetic unit cell or arbitrary choice
# n = three-component array of number of points in the grid
# fenceposts = Boolean: whether to include the edge at 1 as well as at zero. eg False => 0,0.25,0.5,0.75; True => 0,0.25,0.5,0.75,1
# ---
# OUTPUT
# grid_frac = the grid in fractional coordinates
# grid_cart = the grid in Cartesian real-space coordinates
#
# 999 redo this as a NumPy loop for speed
def generate_grid(a_cart,L,n,fenceposts=False):
	if fenceposts:
		m = [n[0]+1,n[1]+1,n[2]+1]
	else:
		m = n
	grid_frac = np.zeros((m[0]*m[1]*m[2],3),np.float)
	grid_cart = np.zeros((m[0]*m[1]*m[2],3),np.float)
	for i in range(m[0]):
		r_frac_x = np.float(i)/np.float(n[0]) * L[0]
		r_test_x = r_frac_x * a_cart[0]
		for j in range(m[1]):
			r_frac_y = np.float(j)/np.float(n[1]) * L[1]
			r_test_y = r_frac_y * a_cart[1]
			for k in range(m[2]):
				r_frac_z = np.float(k)/np.float(n[2]) * L[2]
				grid_frac[i+j*m[1]+k*m[2]*m[1]] = [r_frac_x,r_frac_y,r_frac_z]
				grid_cart[i+j*m[1]+k*m[2]*m[1]] = r_test_x + r_test_y + r_frac_z * a_cart[2]
				#print grid_frac[i+j*m[1]+k*m[2]*m[1]],grid_cart[i+j*m[1]+k*m[2]]
	grid_frac = difast.reshape_array(grid_frac)
	grid_cart = difast.reshape_array(grid_cart)
	return grid_frac,grid_cart

# generate_monte
# --------------------------
# Generates random positions in the unit cell.
# ---
# INPUT
# a_cart = array of three three-component vectors: the primitive translation vectors in cartesian coordinates (m)
# L = three-component array describing the volume of the over which the random points are to be generated, eg 1x1x1 implies crystallographic unit cell; other values could include magnetic unit cell or arbitrary choice
# ---
# OUTPUT
# r_frac = the positions in fractional coordinates
# r_cart = the positions in Cartesian real-space coordinates
def generate_monte(a_cart,L,n):
	#if you're asking to generate a RAM-crippling number of points, reduce it
	if n > config.n_pos_at_a_time:
		n = config.n_pos_at_a_time
	#generate n_pos_at_a_time random positions...see config.py
	r_frac = np.random.random((n,3)) #999 *L
	#convert them to absolute coordinates
	r_cart = np.dot(r_frac,a_cart)
	r_frac = difast.reshape_array(r_frac)
	r_cart = difast.reshape_array(r_cart)
	return r_frac,r_cart

# apply_constraints
# --------------------------
# Applies constraints to an array of positions and discards those which fall outside the allowed regions.
# ---
# INPUT
# r_frac = (N,3) difast-shape array of fractional coordinates
# r_cart = (N,3) difast-shape array of Cartesian coordinates (m)
# constraints = Python list of atoms and minimum and maximum distances
# ---
# OUTPUT
# r_frac = the positions in fractional coordinates
# r_cart = the positions in Cartesian real-space coordinates
def apply_constraints(r_frac,r_cart,r_constraints,constraints_min,constraints_max):
	keep = np.ones(len(r_cart[0]),np.bool) #is it far enough away? Start all true...
	keep_close = np.zeros(len(r_cart[0]),np.bool) #is it close enough? Start all false...
	#  go through, eradicating points which don't satisfy the constraints
	for i in range(len(r_constraints[0])):
		r_rel = r_cart-np.reshape(r_constraints[:,i],(3,1)) #find how far the dipole field point is from all the atoms
		#                                ^^ 998 why does this need reshaping to go from (3,) to (3,1)?
		if constraints_min[i] is not False:
			keep = np.bitwise_and(keep,(np.sum(r_rel*r_rel, 0)>constraints_min[i]**2)) #make sure you're not too close an atom
		if constraints_max[i] is not False:
			keep_close = np.bitwise_or(keep_close,(np.sum(r_rel*r_rel, 0)<constraints_max[i]**2)) #the 'not further than x from atom i' condition starts all false and is then bitwise_or because it doesn't matter which atom you're not more than x from
	keep = np.bitwise_and(keep,keep_close)
	#discard those dipole field points too close and far from to atoms, and return the abridged r_frac and r_cart
	return np.compress(keep,r_frac,axis=1), np.compress(keep,r_cart,axis=1)

# dipole_constraints_table
# --------------------------
# A table-generating function used within dipole_constraints
# ---
# OUTPUT
# A table of existing constraints on muon site as a string; nothing if no constraints are set; an error if no length unit has been specified
def dipole_constraints_table():
	#load (and print out) any already-existent constraints
	crystal_data = load_current('crystal')
	dipole_data = load_current('dipole')
	if crystal_data.has_key('length_unit'):
		if crystal_data['length_unit'] == 'n':
			length_unit = lang.nm
		elif crystal_data['length_unit'] == 'm':
			length_unit = lang.m
		elif crystal_data['length_unit'] == 'a':
			length_unit = lang.angstrom
		
		if dipole_data.has_key('constraints'):
			constraints = dipole_data['constraints']
			constraints_table_array = []
			constraints_table_array.append(['#','element','d_min ('+length_unit+')','d_max ('+length_unit+')'])
			i = 1
			for constraint in constraints:
				constraint_row = []
				constraint_row.append(str(i))
				constraint_row.append(constraint[0])
				if constraint[1] is False:
					constraint_row.append('0')
				else:
					constraint_row.append(str(constraint[1]))
				if constraint[2] is False:
					constraint_row.append(lang.infinity)
				else:
					constraint_row.append(str(constraint[2]))
				constraints_table_array.append(constraint_row)
				i += 1
			return ui.table(constraints_table_array)
		else:
			return ''
	else:
		return lang.err_no_length_unit #filling in this is silly if there's no length unit set

# dipole_constraints
# --------------------------
# A user input menu on the dipole menu
# ---
# Prints a table of current constraints on the muon site if there are any, and allows the user to add, edit or delete constraints
# 998 - add something for specifying ions with a certain charge etc?
# 998 - add fuzzier constraints, eg Gaussian edges etc?
def dipole_constraints():
	dipole_data = load_current('dipole')
	#if there are constraints
	if dipole_data.has_key('constraints') and len(dipole_data['constraints']) != 0:
		return ui.menu([
		['a','add constraint',dipole_constraint_add,''],
		['d','delete constraint',dipole_constraint_delete,''],
		['e','edit constraint',dipole_constraint_edit,''],
		['v','visualise volume satisfying constraints',dipole_constraints_draw,''],
		['f','calculate fractional volume satisfying constraints',dipole_constraints_volume,''],
		['q','back to dipole menu',dipole,'']
		],dipole_constraints_table())
	#if none has been set yet
	else:
		return ui.menu([
		['a','add constraint',dipole_constraint_add,''],
		['q','back to dipole menu',dipole,'']
		])

# dipole_constraint_add
# --------------------------
# A user input function on the dipole constraints menu
# ---
# Gets a new constraint on the muon position by taking an element and specifying how far ones is allowed to be from that element
def dipole_constraint_add():
	newconstraint=[]
	#998 make a way to get these all on one screen
	newconstraint.append(ui.inputscreen('                     element:','string',notblank=True))
	crystal_data = load_current('crystal')
	if crystal_data.has_key('length_unit'):
		length_unit, length_unit_name = get_length_unit(crystal_data['length_unit'])
	else:
		length_unit_name = lang.red+'length unit not defined'+lang.reset
	newconstraint.append(ui.inputscreen('            d_min ('+length_unit_name+"):",'float',0,eqmin=True,notblank=True))
	newconstraint.append(ui.inputscreen('            d_max ('+length_unit_name+", 'n' for no constraint):",'float_or_string',newconstraint[1],eqmin=False,notblank=True)) #can't be less than d_min, which is newconstraint[1]
	#if these are set to no constraint, then set the actual values to Boolean false
	if newconstraint[1] == 0:
		newconstraint[1] = False
	if newconstraint[2] == 'n':
		newconstraint[2] = False
	#load the old atoms
	dipole_data = load_current('dipole')
	if dipole_data.has_key('constraints'):
		constraints = dipole_data['constraints']
	else:
		constraints = []
	constraints.append(newconstraint)
	update_value('dipole','constraints',constraints)
	return dipole_constraints

# dipole_constraint_delete
# --------------------------
# A user input function on the dipole constraints menu
# ---
# Deletes a constraint on the muon position
def dipole_constraint_delete():
	dipole_data = load_current('dipole')
	constraints = dipole_data['constraints']
	constraints_data = dipole_constraints_table()
	if len(constraints) > 1:
		query = 'Delete which constraint? (1-'+str(len(constraints))+', blank to cancel)'
	else:
		query =  'There is only one constraint. Enter 1 to confirm deletion, or leave blank to cancel:'
	kill_me = ui.inputscreen(query,'int',1,len(constraints))
	if kill_me is not False:
		del constraints[kill_me-1]
		update_value('dipole','constraints',constraints)
	return dipole_constraints

# dipole_constraint_edit
# --------------------------
# A user input function on the dipole constraints menu
# ---
# Edits a constraint on the muon position
def dipole_constraint_edit():
	dipole_data = load_current('dipole')
	constraints = dipole_data['constraints']
	constraints_data = dipole_constraints_table()
	if len(constraints) > 1:
		query = 'Edit which constraint? (1-'+str(len(constraints))+')'
		edit_me = ui.inputscreen(query,'int',1,len(constraints),text=constraints_data) - 1 #arrays start at zero
	else:
		edit_me = 0
	#make readable the pre-existing constraints
	if constraints[edit_me][1] == False:
		constraint_min = '0'
	else:
		constraint_min = str(constraints[edit_me][1])
	if constraints[edit_me][2] == False:
		constraint_max = lang.infinity
	else:
		constraint_max = str(constraints[edit_me][2])
	constraint=[]
	#998 make a way to get these all on one screen
	constraint.append(ui.inputscreen('               element (blank for '+constraints[edit_me][0]+'):','string',notblank=False))
	if constraint[0] is False:
		constraint[0] = constraints[edit_me][0]
	#get the length unit
	crystal_data = load_current('crystal')
	if crystal_data.has_key('length_unit'):
		length_unit, length_unit_name = get_length_unit(crystal_data['length_unit'])
	else:
		length_unit_name = lang.red+'length unit not defined'+lang.reset
	constraint.append(ui.inputscreen('         d_min (blank for '+constraint_min+' '+length_unit_name+"):",'float',0,eqmin=True,notblank=False))
	constraint.append(ui.inputscreen('          d_max (blank for '+constraint_max+' '+length_unit_name+", 'n' for no constraint):",'float_or_string',constraint[1],eqmin=False,notblank=False)) #can't be less than d_min, which is constraint[1]
	#if these are set to no constraint, then set the actual values to Boolean false
	if constraint[1] is 0:
		constraint[1] = False
	elif constraint[1] is False:
		constraint[1] = constraints[edit_me][1]
	if constraint[2] == 'n':
		constraint[2] = False
	elif constraint[2] is False:
		constraint[2] = constraints[edit_me][2]
	#update the values
	constraints[edit_me] = constraint
	update_value('dipole','constraints',constraints)
	return dipole_constraints

def dipole_constraints_draw():
	ui.message(lang.drawing_crystal_unit_cell)
	#load visual window stuff
	global visual_window
	global visual_window_contents
	crystal_data = load_current('crystal')
	dipole_data = load_current('dipole')
	draw_data = load_current('draw')
	draw_crystal_unit_cell()
	#draw constrained positions
	ui.message(lang.drawing_constrained_positions)
	length_unit, length_unit_name = get_length_unit(crystal_data['length_unit'])
	a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
	L = [1,1,1]
	r_atoms = difn.zero_if_close(r_atoms)
	r_unit,q_unit,mu_unit,names_unit = difn.make_para_crystal(a_cart, r_atoms, m_atoms, k_atoms, q_atoms, name_atoms,[0,0,0], L)
	#then delete all atoms outside the relevant unit cell(s)
	r_unit,q_unit,mu_unit,names_unit = difn.make_crystal_trim_para(r_unit,q_unit,mu_unit,names_unit,a_cart,L)
	r_frac,r_cart = generate_grid(a_cart,L,[30,30,30],fenceposts=True) # including edges far from origin 
	#r_frac,r_cart = generate_monte(a_cart,L,1000)
	constraint_r,constraint_min,constraint_max = get_constraints(r_unit,names_unit,dipole_data['constraints'],length_unit)
	r_frac,r_cart = apply_constraints(r_frac,r_cart,constraint_r,constraint_min,constraint_max)
	#turn it back from difast format, slightly hackily... 998 can we avoid this?
	r_draw = []
	for i in range(len(r_cart[0])):
		r_draw.append([r_cart[0][i],r_cart[1][i],r_cart[2][i]])
	#draw this stuff
	scale = draw_default_scale()
	visual_window_contents['constrained_positions'] = didraw.points(r_draw,scale)
	return dipole_constraints

def dipole_constraints_volume():
	ui.message(lang.please_wait)
	crystal_data = load_current('crystal')
	dipole_data = load_current('dipole')
	draw_data = load_current('draw')
	length_unit, length_unit_name = get_length_unit(crystal_data['length_unit'])
	a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
	L = [1,1,1]
	r_atoms = difn.zero_if_close(r_atoms)
	r_unit,q_unit,mu_unit,names_unit = difn.make_para_crystal(a_cart, r_atoms, m_atoms, k_atoms, q_atoms, name_atoms,[0,0,0], L)
	#then delete all atoms outside the relevant unit cell(s)
	r_unit,q_unit,mu_unit,names_unit = difn.make_crystal_trim_para(r_unit,q_unit,mu_unit,names_unit,a_cart,L)
	r_frac,r_cart = generate_grid(a_cart,L,[100,100,100])
	n_full_vol = len(r_frac[0])
	#r_frac,r_cart = generate_monte(a_cart,L,1000)
	constraint_r,constraint_min,constraint_max = get_constraints(r_unit,names_unit,dipole_data['constraints'],length_unit)
	r_frac,r_cart = apply_constraints(r_frac,r_cart,constraint_r,constraint_min,constraint_max)
	n_constraint_vol = len(r_frac[0])
	if n_constraint_vol != 0:
		final_message = 'Points satisfying the constraints occupy about '+str(np.float(n_constraint_vol)/n_full_vol*100)+'% of the unit cell. To obtain approximately x points in your final histogram, generate a grid containing '+str(np.round(np.float(n_full_vol)/n_constraint_vol,3))+'x points [('+str(np.int(np.ceil((np.float(n_full_vol)/n_constraint_vol)**(1./3.))))+'x)^3 in the cubic case].'
	else:
		final_message = lang.err_constraints_too_harsh
	return ui.menu([
	['q','back to dipole menu',dipole_constraints,'']
	],final_message)

def constraints_readable(constraints,length_unit_name):
	constraints_readable = ''
	for j in range(len(constraints)):
		#if there's a min and a max, write min < d < max,
		if constraints[j][1] is not False and constraints[j][2] is not False:
			constraints_readable += str(constraints[j][1])+' < '+'d_'+constraints[j][0] + ' < ' + str(constraints[j][2]) + '; '
		#if there's a max, write d < max,
		elif constraints[j][2] is not False:
			constraints_readable += 'd_'+constraints[j][0] + ' < ' + str(constraints[j][2]) + '; '
		#if there's a min, write d > min,
		else:
			constraints_readable += 'd_'+constraints[j][0] + ' > ' + str(constraints[j][1]) + '; '
	return constraints_readable[:-2]+' '+length_unit_name #subtract final comma, and add length unit name

def get_constraints(r_unit,names_unit,constraints,length_unit):
	constraint_r = []
	constraint_min = []
	constraint_max = []
	#is there an 'all atoms' constraint?
	constraint_all = False
	for j in range(len(constraints)):
		if constraints[j][0] == 'all':
			constraint_all = True
			if constraints[j][1] is not False:
				constraint_all_min = constraints[j][1]*length_unit
			else:
				constraint_all_min = False
			if constraints[j][2] is not False:
				constraint_all_max = constraints[j][2]*length_unit
			else:
				constraint_all_max = False
			break
	#go through each atom and note the constraints associated with it
	for i in range(len(r_unit)):
		element_found = False
		#loop though to see if the element has a constraint defined
		for j in range(len(constraints)):
			if names_unit[i] == constraints[j][0]:
				constraint_r.append(r_unit[i])
				constraint_min.append(constraints[j][1]*length_unit)
				constraint_max.append(constraints[j][2]*length_unit)
				element_found = True
				#print names_unit[i],constraint_r[-1],constraint_min[-1],constraint_max[-1]
				break #escape the loop if the element has a constraint defined
		if not(element_found): #if the atom's specific element wasn't found
			if constraint_all: #and if there is a catch-all constraint
				constraint_r.append(r_unit[i])
				constraint_min.append(constraint_all_min)
				constraint_max.append(constraint_all_max)
				#print names_unit[i],constraint_r[-1],constraint_min[-1],constraint_max[-1]
	#reshape the array of constrained positions for fast execution
	constraint_r = difast.reshape_array(constraint_r)
	return constraint_r,constraint_min,constraint_max

# This function is in need of streamlining--there's a lot of duplication betwen generating the points on a grid and generating them Monte Carlo
def calculate_dipole():
	dipole_data = load_current('dipole')
	crystal_data = load_current('crystal')
	# is it either set to generate points on a grid, and are the grid dimensions set, or is it set to Monte Carlo with a specified n?
	if dipole_data.has_key('r_sphere') and crystal_data.has_key('length_unit') and ((dipole_data.has_key('pointgen') and dipole_data['pointgen'] == 'g' and dipole_data.has_key('n_a') and dipole_data.has_key('n_b') and dipole_data.has_key('n_c')) or (dipole_data.has_key('pointgen') and dipole_data['pointgen'] == 'm' and dipole_data.has_key('n_monte'))) or (dipole_data.has_key('pointgen') and dipole_data['pointgen'] == 's'):
		#if so, calculate!
		#start the v_meta metadata dictionary
		v_meta = {'title':ui.inputscreen('Please enter a title for your output files:','str',notblank=True)}
		v_filename = ui.inputscreen('Please enter a filename for your output files:','str',notblank=True)
		update_value('dipole', 'current_filename', v_filename)
		#get crystal structure
		print 'Loading crystal structure...'
		a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
		L = difn.mag_unit_cell_size(k_atoms)
		r_atoms = difn.zero_if_close(r_atoms)
		r_unit,q_unit,mu_unit,names_unit = difn.make_para_crystal(a_cart, r_atoms, m_atoms, k_atoms, q_atoms, name_atoms,[0,0,0], L)
		#then delete all atoms outside the relevant unit cell(s)
		r_unit,q_unit,mu_unit,names_unit = difn.make_crystal_trim_para(r_unit,q_unit,mu_unit,names_unit,a_cart,L)
		constraints = False
		#if there are constraints set...
		if dipole_data.has_key('constraints') and len(dipole_data['constraints']) > 0:
			#load constraints
			constraints = dipole_data['constraints']
			#load length unit
			length_unit,length_unit_name = get_length_unit(crystal_data['length_unit'])
			#now identify atoms and associated constraints
			constraint_r,constraint_min,constraint_max = get_constraints(r_unit,names_unit,constraints,length_unit)
			v_meta['constraints'] = constraints_readable(constraints,length_unit_name)
		# ===make the vcrystal=== #
		radius = dipole_data['r_sphere']
		ui.message('Creating virtual crystal (r = '+str(radius)+'a)...')
		v_meta['R'] = str(radius)+'a'
		v_meta['shape'] = 'sphere'
		L,r,q,mu,name,r_whatisthis = difn.make_crystal(radius,a,alpha,r_atoms,m_atoms,k_atoms, q_atoms, name_atoms, type='magnetic') #999whatisthis
		#save the vcrystal
		ui.message('Saving virtual crystal ('+config.output_dir+'/'+v_filename+'-vcrystal.tsv)...')
		attr = []
		for i in range(len(r)):
			attr.append([r[i][0],r[i][1],r[i][2],name[i],mu[i][0],mu[i][1],mu[i][2],q[i]])
		csc_properties = ['r_x','r_y','r_z','element','mu_x','mu_y','mu_z','q']
		csc.write(v_meta,csc_properties,attr,config.output_dir+'/'+v_filename+'-vcrystal.tsv')
		#kill the attributes variable as it may be quite big, and is no longer needed
		del(attr)
		
		ui.message('Calculating dipole fields...')
		#get the magnetic unit cell size
		L = difn.mag_unit_cell_size(k_atoms)
		#create a file ready to receive the output
		dipole_field_filename =  config.output_dir+'/'+v_filename+'-dipole-field.tsv'
		r_fast = difast.reshape_array(r)
		mu_fast = difast.reshape_array(mu)

		runningtotal = 0 #this stores the number of valid positions calculated so far
		t_start = time.clock()
		t_gen = 0
		t_dip = 0
		#if we're generating points on a grid
		if dipole_data['pointgen'] == 'g':
			n_grid = [dipole_data['n_a'],dipole_data['n_b'],dipole_data['n_c']]
			csc_properties = ['rho_x','rho_y','rho_z','r_x','r_y','r_z','B_x','B_y','B_z','omega']
			d_meta = {'title': v_meta['title'], 'pointgen': 'grid', 'n_a': n_grid[0], 'n_b': n_grid[1], 'n_c': n_grid[2], 'vcrystal': v_filename+'-vcrystal.tsv'}
			if constraints is not False:
				d_meta['constraints'] = v_meta['constraints']
			file = csc.begin(d_meta,csc_properties,dipole_field_filename)
			t_gen_start = time.clock()
			#generate n_pos_at_a_time random positions...see config.py
			r_frac,r_dip = generate_grid(a_cart,L,n_grid)
			#throw some away, if necessary
			if constraints is not False:
				r_frac,r_dip = apply_constraints(r_frac,r_dip,constraint_r,constraint_min,constraint_max)
			# if there are no remaining points after applying constraints
			if r_frac.shape[1] == 0:
				return ui.menu([
				['q','back to dipole menu',dipole,'']
				],lang.err+lang.err_constraints_too_harsh)
			points_to_try = len(r_dip[0])
			t_gen += time.clock() - t_gen_start
			t_dip_start = time.clock()
			for i in range(points_to_try):
				B = difast.calculate_dipole(np.reshape(r_dip[:,i],(3,1)), r_fast, mu_fast)
				omega = difn.gyro(B)
				#only write to the file if the result is not invalid, caused by being on top of a moment
				if not np.isnan(omega):
					csc.append([r_frac[0,i],r_frac[1,i],r_frac[2,i],r_dip[0,i],r_dip[1,i],r_dip[2,i],B[0],B[1],B[2],omega],file)
				if (i+1)%10000 == 0:
					#every so often, print out how far through we are
					frac_done = np.float(i)/points_to_try
					t_elapsed = time.clock()-t_start
					t_remain  = (1-frac_done)*t_elapsed/frac_done
					print str(round(frac_done*100,1))+'% done in '+ui.s_to_hms(t_elapsed)+'...approximately '+ui.s_to_hms(t_remain)+' remaining'
			t_dip += time.clock() - t_dip_start
			t_elapsed = time.clock()-t_start
			csc.close(file)
			final_message = 'Calculation completed in '+ui.s_to_hms(t_elapsed)
		#if the points come pre-specified
		elif dipole_data['pointgen'] == 's':
			csc_properties = ['rho_x','rho_y','rho_z','r_x','r_y','r_z','B_x','B_y','B_z','omega']
			d_meta = {'title': v_meta['title'], 'pointgen': 'manual', 'vcrystal': v_filename+'-vcrystal.tsv'}
			if constraints is not False:
				d_meta['constraints'] = v_meta['constraints']
			file = csc.begin(d_meta,csc_properties,dipole_field_filename)
			t_gen_start = time.clock()
			#generate n_pos_at_a_time random positions...see config.py
			r_frac = np.array(dipole_data['points'])
			r_dip  = np.empty(r_frac.shape,np.float)
			for i in range(len(r_frac)): #998 could probably do with with numpy tensordot or something to speed it up
				r_dip[i] = difn.frac2abs(r_frac[i],a_cart)
			#throw some away, if necessary
			r_frac = difast.reshape_array(r_frac)
			r_dip  = difast.reshape_array(r_dip)
			if constraints is not False:
				r_frac,r_dip = apply_constraints(r_frac,r_dip,constraint_r,constraint_min,constraint_max)
			# if there are no remaining points after applying constraints
			if r_frac.shape[1] == 0:
				return ui.menu([
				['q','back to dipole menu',dipole,'']
				],lang.err+lang.err_constraints_too_harsh)
			points_to_try = len(r_dip[0])
			t_gen += time.clock() - t_gen_start
			t_dip_start = time.clock()
			for i in range(points_to_try):
				B = difast.calculate_dipole(np.reshape(r_dip[:,i],(3,1)), r_fast, mu_fast)
				omega = difn.gyro(B)
				#only write to the file if the result is not invalid, caused by being on top of a moment
				if not np.isnan(omega):
					csc.append([r_frac[0,i],r_frac[1,i],r_frac[2,i],r_dip[0,i],r_dip[1,i],r_dip[2,i],B[0],B[1],B[2],omega],file)
				if (i+1)%10000 == 0:
					#every so often, print out how far through we are
					frac_done = np.float(i)/points_to_try
					t_elapsed = time.clock()-t_start
					t_remain  = (1-frac_done)*t_elapsed/frac_done
					print str(round(frac_done*100,1))+'% done in '+ui.s_to_hms(t_elapsed)+'...approximately '+ui.s_to_hms(t_remain)+' remaining'
			t_dip += time.clock() - t_dip_start
			t_elapsed = time.clock()-t_start
			csc.close(file)
			final_message = 'Calculation completed in '+ui.s_to_hms(t_elapsed)
		#otherwise, we must be generating points Monte Carlo
		else:
			csc_properties = ['omega'] #if it's MC, don't record positions or field directions, just frequencies
			n_positions = dipole_data['n_monte']
			d_meta = {'title': v_meta['title'], 'pointgen': 'Monte Carlo', 'n': n_positions, 'vcrystal': v_filename+'-vcrystal.tsv'}
			if constraints is not False:
				d_meta['constraints'] = v_meta['constraints']
			file = csc.begin(d_meta,csc_properties,dipole_field_filename)
			while runningtotal < n_positions:
				t_gen_start = time.clock()
				#generate n_pos_at_a_time random positions...see config.py
				r_frac,r_dip = generate_monte(a_cart,L,config.n_pos_at_a_time)
				#throw some away, if necessary
				if constraints is not False:
					r_frac,r_dip = apply_constraints(r_frac,r_dip,constraint_r,constraint_min,constraint_max)
				# if there are no remaining points after applying constraints
				if r_frac.shape[1] == 0:
					return ui.menu([
					['q','back to dipole menu',dipole,'']
					],lang.err+lang.err_constraints_too_harsh)
				runningtotal += len(r_dip[0])
				if runningtotal < n_positions: #if we've not made it to the number of positions yet
					points_to_try = len(r_dip[0]) #just do them all
				else:
					points_to_try = len(r_dip[0]) - (runningtotal - n_positions) #if not, 
				t_gen += time.clock() - t_gen_start
				t_dip_start = time.clock()
				for i in range(points_to_try):
					B = difast.calculate_dipole(np.reshape(r_dip[:,i],(3,1)), r_fast, mu_fast)
					omega = difn.gyro(B)
					#only write to the file if the result is not invalid, caused by being on top of a moment
					if not np.isnan(omega):
						csc.append([omega],file)
				t_dip += time.clock() - t_dip_start
				#every recalculation, print out how far through we are
				frac_done = np.float(runningtotal)/n_positions
				t_elapsed = (time.clock()-t_start)
				t_remain  = (1-frac_done)*t_elapsed/frac_done
				print str(round(frac_done*100,1))+'% done in '+ui.s_to_hms(t_elapsed)+'...approximately '+ui.s_to_hms(t_remain)+' remaining'
		csc.close(file)
		final_message = 'Calculation completed in '+ui.s_to_hms(t_elapsed)
		if config.verbose and t_elapsed > 0: #prevents divide by zero crash
			#verbose output also displays the proportion of time spent generating the random positions versus calculating dipole fields
			final_message += ' ('+ui.s_to_hms(t_gen)+' ['+str(round(t_gen/t_elapsed*100,1))+'%] spent generating positions, '+ui.s_to_hms(t_dip)+' ['+str(round(t_dip/t_elapsed*100,1))+'%] spent calculating dipole fields)'
	else:
		final_message = 'Before calculating dipole fields, you need to set a vcrystal radius, whether to generate points on a grid or Monte Carlo and a number of points to sample, and a length unit in the crystal menu to apply any muon site constraints. Please ensure all of those are properly set and try again.'
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
	dipole_filename,title,values = get_csc(config.output_dir,'-dipole-field.tsv',default_filename,'of your dipole field file')
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
	menuoptions.append(['q','back to dipole menu',dipole,''])
	return ui.menu(menuoptions,ui.heading('Frequency histogram menu'))

def histo_filename():
	dipole_data = load_current('dipole')
	if dipole_data.has_key('current_filename'):
		default_filename = dipole_data['current_filename']
	else:
		default_filename=''
	directory = config.output_dir
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
		max = ui.inputscreen('Maximum frequency for histogram (MHz):','float',min,eqmin=False,notblank=True)
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
	meta,properties,f = csc.begin_read(config.output_dir+'/'+dipole_filename)
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
			print 'line '+str(total)+'...'
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
	filename = config.output_dir+'/'+dipole_data['current_filename'] + '-frequency-histogram.tsv'
	output = csc.begin(meta_out,properties_out,filename)
	#work out the prefactor to turn number of counts into a probability density
	n2p = 1/(binwidth*total) #ie divide by bin width and total number
	for i in range(bins):
		bin_centre = min+(i+0.5)*binwidth
		csc.append([bin_centre,n2p*histo[i],histo[i]],output)
	csc.close(output)
	return histo_freq

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
	meta,properties,f = csc.begin_read(config.output_dir+'/Ba2NaOsO6-FM111-highres-2-dipole-field.tsv')
	min = 3.8*1e6
	max = 4.0*1e6 #x1,000,000 for MHz --> Hz
	#then import the crystal structure
	not_eof = True
	#open the files to write to:
	meta_out = {}
	meta_out['title'] = meta['title']
	meta_out['dipole_filename'] = config.output_dir+'/'+dipole_data['current_filename']+'-dipole-field.tsv'
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
	filename = config.output_dir+'/Ba2NaOsO6-FM111-highres-2-dipole-field-symeqv.tsv'#999
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
	meta,properties,f = csc.begin_read('output/Ba2NaOsO6-FM111-highres-2-dipole-field.tsv')
	min = 3.8*1e6
	max = 4.0*1e6 #x1,000,000 for MHz --> Hz
	#then import the crystal structure
	not_eof = True
	#open the files to write to:
	meta_out = {}
	meta_out['title'] = meta['title']
	meta_out['dipole_filename'] = config.output_dir+'/'+dipole_data['current_filename']+'-dipole-field.tsv'
	meta['desc'] = 'Frequencies from '+meta_out['dipole_filename']+' between 0.9 and 1.1 angstroms from an oxygen, and not less than 0.9 angstroms from other stuff'
	properties_out = ['rho_x','rho_y','rho_z','r_x','r_y','r_z','omega_1','omega_2'] #998 include number of symmetry-eqv points?
	#output = csc.begin(meta_out,properties_out,'output/'+dipole_data['current_filename']+'-frequencies-raw-near-O.tsv')
	#output = csc.begin(meta_out,properties_out,'output/Ba2NaOsO6-FM111-highres-2-dipole-field-symeqv.tsv')
	#~ output = csc.begin(meta_out,properties_out,'output/'+dipole_data['current_filename']+'-near-O-dipole-field.tsv')
	
	#999
	min=0
	max=5e6
	bins=100
	
	
	binwidth = (max-min)/bins
	#histo = np.zeros(bins,np.int) #not done like this any more
	total = 0
	t_start = time.clock()
	omega_x = []
	omega_y = []
	while not_eof and total < 1000001:
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
	filename = 'output/Ba2NaOsO6-FM111-highres-2-dipole-field-symeqv2dhisto.tsv' #999
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
	dipole_filename,title,values = get_csc(config.output_dir,'-dipole-field.tsv',dipole_data['current_filename'],'of your dipole field file')
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
	if not draw_data.has_key('bonds_visible'):
		draw_data['bonds_visible'] = True
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
	if draw_data['bonds_visible'] and draw_data.has_key('bonds') and len(draw_data['bonds']) > 0:
		menu_data['bonds'] = ''
		for bond in draw_data['bonds']:
			menu_data['bonds'] += bond[0]+'-'+bond[1]+', '
		menu_data['bonds'] = menu_data['bonds'][:-2]
	else:
		menu_data['bonds'] = 'off'
	menu_data['unitcells'] = str(draw_data['L'])
	if draw_data.has_key('camera_direction'):
		menu_data['draw_view'] = str(draw_data['camera_direction'])
	else:
		menu_data['draw_view'] = 'z'
	if draw_data['stereo_3d'] == 'n':
		menu_data['stereo_3d'] = 'off'
	elif draw_data['stereo_3d'] == 'r':
		menu_data['stereo_3d'] = 'red-cyan'
	elif draw_data['stereo_3d'] == 'b':
		menu_data['stereo_3d'] = 'red-blue'
	else:
		menu_data['stereo_3d'] = 'error' #can't see why this would happen, but it's better than the program crashing
	if draw_data.has_key('kill'):
		menu_data['kill'] = str(len(draw_data['kill']))+" 'little accidents'"
	else:
		menu_data['kill'] = 'none...yet'
	#the menu
	menuoptions = [['s','scale',draw_scale,menu_data['scale']],
	['c','atom colours',draw_atom_colours,menu_data['atom_colours']],
	['t','customise atoms',draw_customise_atoms,menu_data['atom_custom']],
	['m','moments '+menu_data['moments_opposite'],draw_moments_onoff,menu_data['moments']],
	['i','unit cell boundary '+menu_data['unitcell_opposite'],draw_unitcell_onoff,menu_data['unitcell']],
	['a','auto redraw '+menu_data['auto_redraw_opposite'],draw_auto_redraw_onoff,menu_data['auto_redraw']]]
	if not draw_data['auto_redraw']:
		menuoptions.append(['d','manual redraw',manual_redraw,''])
	menuoptions.append(['u','unit cells',draw_unitcells,menu_data['unitcells']])
	menuoptions.append(['f','field',draw_field,menu_data['field']])
	menuoptions.append(['b','bonds',draw_bonds,menu_data['bonds']])
#	['r','field repeat',b,menu_data['b']],
	if visual_window is not None: #only provide these options if there's an existing window
		menuoptions.append(['w','view options',draw_view,menu_data['draw_view']])
		menuoptions.append(['3','3D stereo',draw_3d,menu_data['stereo_3d']])
	menuoptions.append(['v','save settings',draw_save,''])
	menuoptions.append(['l','load settings',draw_load,''])
	if visual_window is not None: #only provide these options if there's an existing window
		menuoptions.append(['k','kill objects',draw_kill,menu_data['kill']])
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
		userL = ui.inputscreen(' Enter T_x,T_y,T_z (blank to cancel):','intlist',1,number=3)
		if userL is not False:
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
						size_unit = ' '+lang.nm
					elif atom[3] == 'm':
						size_unit = ' '+lang.m
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
	directory = config.output_dir
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

# draw_bonds
# --------------------------
# A user input menu on the visualisation menu
# ---
# Draws bonds between atoms specified
def draw_bonds():
	draw_data = load_current('draw')
	if draw_data['auto_redraw']:
		draw_draw()
	#if there are constraints
	if draw_data.has_key('bonds') and len(draw_data['bonds']) != 0:
		if draw_data['bonds_visible']:
			visible_menu_text = 'do not draw'
			visible_menu_info = 'currently shown'
		else:
			visible_menu_text = 'draw'
			visible_menu_info = 'currently hidden'
		return ui.menu([
		['a','add bond',draw_bonds_add,''],
		['d','delete bond',draw_bonds_delete,''],
		['e','edit bond',draw_bonds_edit,''],
		['v',visible_menu_text,draw_bonds_yesno,visible_menu_info],
		['q','back to visualisation menu',draw,'']
		],draw_bonds_table())
	#if none has been set yet
	else:
		return ui.menu([
		['a','add bond',draw_bonds_add,''],
		['q','back to visualisation menu',draw,'']
		])

# generate_bonds
# --------------------------
# A function called by the bonds menu
# ---
# Uses from and to values to loop through the atoms defined in the crystal menu and find coordinates
# Then generates equivalent positions using sg.gen_unit_cell
def generate_bonds():
	crystal_data = load_current('crystal')
	length_unit, length_unit_name = get_length_unit(crystal_data['length_unit'])
	draw_data = load_current('draw')
	a,alpha,a_cart,r_atoms,q_atoms,m_atoms,k_atoms,name_atoms = stored_unit_cell()
	L = draw_data['L']
	atoms_r = difn.zero_if_close(r_atoms)
	r_i,q_i,mu_i,names_i = difn.make_para_crystal(a_cart, r_atoms, m_atoms, k_atoms, q_atoms, name_atoms,[0,0,0], L)
	#then delete all atoms outside the draw size
	r_i,q_i,mu_i,names_i = difn.make_crystal_trim_para(r_i,q_i,mu_i,names_i,a_cart,L)
	elements_i = labels2elements(names_i)
	bonds_output = []
	for bond in draw_data['bonds']:
		#if 'from' has no suffix eg it's Cu not Cu2, and is therefore just a general element
		if bond[0] == labels2elements([bond[0]]): #hackishly, this is passed as a one-item list because labels2elements accepts lists 998 fix this!
			from_general = True
		else:
			from_general = False
		if bond[1] == labels2elements([bond[1]]):
			to_general = True
		else:
			to_general = False
		
		bonds_from = []
		bonds_to = []
		for i in range(len(r_i)):
			if from_general: #if the bond name has no numerical suffix eg Cu not Cu2
				if elements_i[i] == bond[0]: #then check it against the elements with numerical suffices subtracted, ie Cu2 > Cu
					bonds_from.append(r_i[i]) #append the coordinates
			else: #otherwise
				if names_i[i] == bond[0]: #test it against the full atom label eg Cu2
					bonds_from.append(r_i[i])
			if to_general:
				if elements_i[i] == bond[1]:
					bonds_to.append(r_i[i])
			else: #otherwise
				if names_i[i] == bond[1]:
					bonds_to.append(r_i[i])
		
		for bond_from in bonds_from:
			for bond_to in bonds_to:
				length = (bond_from[0]-bond_to[0])**2+(bond_from[1]-bond_to[1])**2+(bond_from[2]-bond_to[2])**2
				if length > 0 and length < (bond[2]*length_unit)**2: #if the length is nonzero and not above the maximum specified
					bonds_output.append([bond_from,bond_to,bond[3],bond[4],bond[5]]) #from, to, colour and radius
	#~ #check for doubled-up bonds      998 add this
	#~ for i in range(len(bonds_output)-1,-1,-1): # from (number of bonds)-1 to zero, ie array indices
		#~ for j in range(len(bonds_output)-i-1,len(bonds_output)): # from where we are to the end
			#~ if bonds_output[i][0] == bonds_output[j][0]
	return bonds_output

def draw_bonds_yesno():
	return option_toggle('draw','bonds_visible',draw_bonds)

# draw_bonds_table
# --------------------------
# A table-generating function used within draw_bonds
# ---
# OUTPUT
# A table of existing bonds to be drawn as a string; nothing if no bonds are defined; an error if no length unit has been specified
def draw_bonds_table():
	#load (and print out) any already-existent constraints
	crystal_data = load_current('crystal')
	draw_data = load_current('draw')
	if crystal_data.has_key('length_unit'):
		if crystal_data['length_unit'] == 'n':
			length_unit = lang.nm
		elif crystal_data['length_unit'] == 'm':
			length_unit = lang.m
		elif crystal_data['length_unit'] == 'a':
			length_unit = lang.angstrom
		
		if draw_data.has_key('bonds'):
			bonds = draw_data['bonds']
			bonds_table_array = []
			bonds_table_array.append(['#','from','to','l_max ('+length_unit+')','colour','radius'])
			i = 1
			for bond in bonds:
				bond_row = []
				bond_row.append(str(i))
				bond_row.append(bond[0])
				bond_row.append(str(bond[1]))
				#if constraint[2] is False:
				#	constraint_row.append(lang.infinity)
				#else:
				bond_row.append(str(bond[2]))
				if bond[3] is not False: #colour
					bond_row.append(str(bond[3]))
				else:
					bond_row.append('[default]')
				bonds_table_array.append(bond_row)
				if bond[4] == 'd': #if atom size is default
					bond_row.append('[default]') #size
				else:
					if bond[4] == 'r':
						size_unit = ''
					elif bond[4] == 'n':
						size_unit = ' '+lang.nm
					elif bond[4] == 'm':
						size_unit = ' '+lang.m
					else:
						size_unit = ' '+lang.angstrom
					bond_row.append(str(bond[5])+size_unit) #size
				i += 1
			return ui.table(bonds_table_array)
		else:
			return ''
	else:
		return lang.err_no_length_unit #filling in this is silly if there's no length unit set

# draw_bonds
# --------------------------
# A user input function on the draw bonds menu
# ---
# Gets a new bond by enquiring which atoms to draw it between, plus a maximum length
def draw_bonds_add():
	newbond=[]
	newbond.append(ui.inputscreen('                from:','string',notblank=True))
	newbond.append(ui.inputscreen('                  to:','string',notblank=True,newscreen=False))
	crystal_data = load_current('crystal')
	if crystal_data.has_key('length_unit'):
		length_unit, length_unit_name = get_length_unit(crystal_data['length_unit'])
	else:
		length_unit_name = lang.red+'length unit not defined'+lang.reset
	newbond.append(ui.inputscreen('        max length: ('+length_unit_name+"):",'float',0,eqmin=False,notblank=True,newscreen=False))
	newbond.append(ui.inputscreen(' colour (0,0,0) <= (R,G,B) <= (255,255,255), blank for default:','intlist',0,255,number=3))
	newbond.append(ui.option([
		['d','default size',False,'0.01 x scale'],
		['r','relative to 0.01 x scale',False,''],
		['n','nm',False,'nanometre'],
		['m','m',False,'metre'],
		['a',lang.angstrom,False,'angstrom']
		], 'Choose a bond size unit:'))
	#if it's not the default, get a number
	if newbond[4] != 'd':
		newbond.append(ui.inputscreen('   size:','float',0,eqmin=False,notblank=True))
	#if it is, just append False, we don't need a length
	else:
		newbond.append(False)
	#load the old bonds
	draw_data = load_current('draw')
	if draw_data.has_key('bonds'):
		bonds = draw_data['bonds']
	else:
		bonds = []
	bonds.append(newbond)
	update_value('draw','bonds',bonds)
	return draw_bonds

# dipole_bonds_delete
# --------------------------
# A user input function on the dipole constraints menu
# ---
# Deletes a constraint on the muon position
def draw_bonds_delete():
	draw_data = load_current('draw')
	bonds = draw_data['bonds']
	bonds_data = draw_bonds_table()
	if len(bonds) > 1:
		query = 'Delete which bond? (1-'+str(len(bonds))+', blank to cancel)'
	else:
		query =  'There is only one bond. Enter 1 to confirm deletion, or leave blank to cancel:'
	kill_me = ui.inputscreen(query,'int',1,len(bonds))
	if kill_me is not False:
		del bonds[kill_me-1]
		update_value('draw','bonds',bonds)
	return draw_bonds

# dipole_bonds_edit
# --------------------------
# A user input function on the visualise > bonds menu
# ---
# Edits a bond
def draw_bonds_edit():
	draw_data = load_current('draw')
	bonds = draw_data['bonds']
	bonds_data = draw_bonds_table()
	if len(bonds) > 1:
		query = 'Edit which bond? (1-'+str(len(bonds))+', blank to cancel)'
		edit_me = ui.inputscreen(query,'int',1,len(bonds),text=bonds_data,notblank=False) - 1 #arrays start at zero
		if edit_me is False:
			return draw_bonds
	else:
		edit_me = 0
	#make readable the pre-existing constraints
	bond=[]
	bond.append(ui.inputscreen('             from (blank for '+bonds[edit_me][0]+'):','string',notblank=False))
	bond.append(ui.inputscreen('               to (blank for '+bonds[edit_me][1]+'):','string',notblank=False,newscreen=False))
	#get the length unit
	crystal_data = load_current('crystal')
	if crystal_data.has_key('length_unit'):
		length_unit, length_unit_name = get_length_unit(crystal_data['length_unit'])
	else:
		length_unit_name = lang.red+'length unit not defined'+lang.reset
	bond.append(ui.inputscreen('         max length (blank for '+str(bonds[edit_me][2])+' '+length_unit_name+"):",'float',0,eqmin=True,notblank=False,newscreen=False))
	bond.append(ui.inputscreen(' colour 0,0,0 <= R,G,B <= 255,255,255 or blank for default:','intlist',0,255,number=3,newscreen=False))
	bond.append(ui.option([
		['d','default size',False,'0.01 x scale'],
		['r','relative to 0.01 x scale',False,''],
		['n','nm',False,'nanometre'],
		['m','m',False,'metre'],
		['a',lang.angstrom,False,'angstrom']
		], 'Choose a bond size unit:'))
	#if it's not the default, get a number
	if bond[4] != 'd':
		bond.append(ui.inputscreen('   size:','float',0,eqmin=False,notblank=True))
	#if it is, just append False, we don't need a length
	else:
		bond.append(False)
	#set blank values to defaults
	if bond[0] is False:
		bond[0] = bonds[edit_me][0]
	if bond[1] is False:
		bond[1] = bonds[edit_me][1]
	if bond[2] is False:
		bond[2] = bonds[edit_me][2]
	#if these are set to no constraint, then set the actual values to Boolean false
	#update the values
	bonds[edit_me] = bond
	update_value('draw','bonds',bonds)
	return draw_bonds

def draw_kill():
	draw_data = load_current('draw')
	menu_data={}
	if draw_data.has_key('kill'):
		menu_data['kill'] = 'Currently storing '+str(len(draw_data['kill']))+' post-drawing kills.'+lang.newline
	else:
		menu_data['kill'] = 'No deaths reported.'
	return ui.menu([
	['k','kill',draw_kill_kill,'passes control to 3D window'],
	['m','mass kill',draw_kill_mass,'passes control to 3D window'],
	['r','reset',draw_kill_reset,''],
	['q','back to visualisation menu',draw,''],
	], 
	menu_data['kill']
	)
	return draw

#allows the user to kill atoms and bonds by clicking on them
def draw_kill_kill():
	global visual_window
	global visual_window_contents
	draw_data = load_current('draw')
	ui.message_screen('Kill!!'+lang.newline+lang.newline+'Control has been passed to the 3D window. Click on atoms or bonds to delete them, and press q in the 3D window when done.'+lang.newline+lang.newline+'undo     ctrl-z'+lang.newline+'quit     q'+lang.newline+'reset    r')
	if draw_data.has_key('kill'):
		kill_list = draw_data['kill']
	else:
		kill_list=[]
	#start the continual loop awaiting mouse info
	while True:
		event = didraw.get_event(visual_window)
		if event['type'] == 'click':
			if event['event'].pick is not None:
				#go through the atoms to see if it's one of them
				atomnumber = None
				for i in range(len(visual_window_contents['atoms'])):
					if event['event'].pick == visual_window_contents['atoms'][i]:
						atomnumber = i
						draw_kill_atom(i)
						kill_list.append(['atom',i])
						break
				#if it's not an atom
				if atomnumber is None:
					#if it's not an atom, maybe it was a bond
					bondnumber = None
					for i in range(len(visual_window_contents['bonds'])):
						if event['event'].pick == visual_window_contents['bonds'][i]:
							bondnumber = i
							draw_kill_bond(i)
							kill_list.append(['bond',i])
							break
		if event['type'] == 'keypress': #is there a keyboard event waiting to be processed?
			if event['event'] == 'ctrl+z':
				#undo the last deletion by redrawing with n-1 instructions
				kill_list = kill_list[:-1]
				update_value('draw','kill',kill_list)
				draw_draw(silent='True')
			elif event['event'] == 'r':
				kill_list=[]
				draw_kill_reset(return_val=True)
			elif event['event'] == 'q':
				#update the list of atoms to be killed
				update_value('draw','kill',kill_list)
				#and return to the kill menu
				return draw_kill

#allows the user to kill atoms and bonds by clicking on them
def draw_kill_mass():
	global visual_window
	global visual_window_contents
	draw_data = load_current('draw')
	ui.message_screen('Mass kill!!!!'+lang.newline+lang.newline+'Control has been passed to the 3D window. Click on atoms or bonds to delete all atoms and bonds touching it, and press q in the 3D window when done.'+lang.newline+lang.newline+'undo     ctrl-z'+lang.newline+'quit     q'+lang.newline+'reset    r')
	if draw_data.has_key('kill'):
		kill_list = draw_data['kill']
	else:
		kill_list=[]
	#start the continual loop awaiting mouse info
	while True:
		event = didraw.get_event(visual_window)
		if event['type'] == 'click':
			if event['event'].pick is not None:
				#go through the atoms to see if it's one of them
				atomnumber = None
				bondnumber = None
				for i in range(len(visual_window_contents['atoms'])):
					if event['event'].pick == visual_window_contents['atoms'][i]:
						atomnumber = i
						kill_list.append(['atom_mass',i])
						break
				#if it's not an atom
				if atomnumber is None:
					#if it's not an atom, maybe it was a bond
					for i in range(len(visual_window_contents['bonds'])):
						if event['event'].pick == visual_window_contents['bonds'][i]:
							bondnumber = i
							kill_list.append(['bond_mass',i])
							break
				if atomnumber is not None or bondnumber is not None:
					draw_kill_mass_do(kill_list[-1])
		if event['type'] == 'keypress': #is there a keyboard event waiting to be processed?
			if event['event'] == 'ctrl+z':
				#undo the last deletion by redrawing with n-1 instructions
				#998 this is obviously a pretty slow way of doing it...would be better just to undo the last instruction
				kill_list = kill_list[:-1]
				update_value('draw','kill',kill_list)
				draw_draw(silent='True')
			elif event['event'] == 'r':
				kill_list=[]
				draw_kill_reset(return_val=True)
			elif event['event'] == 'q':
				#update the list of atoms to be killed
				update_value('draw','kill',kill_list)
				#and return to the kill menu
				return draw_kill

#deletes all kills
#if no return_val is sent, go back to the kill menu
#if one is set (eg True) just return that
def draw_kill_reset(return_val=draw_kill):
	draw_data = load_current('draw')
	if draw_data.has_key('kill'):
		del draw_data['kill']
		save_current('draw',draw_data)
	draw_draw(silent=True)
	return return_val

def draw_kill_atom(atomnumber):
	global visual_window_contents
	#kill the atom
	didraw.hide(visual_window_contents['atoms'][atomnumber])
	#and kill off any associated bonds
	for i in range(len(visual_window_contents['bonds'])):
		#if either the bond's position is the same, or position + axis, ie the other end, is the same
		#making a proper approx_equal for vectors would be good
		if (difn.approx_equal(visual_window_contents['atoms'][atomnumber].pos[0],visual_window_contents['bonds'][i].pos[0]) and difn.approx_equal(visual_window_contents['atoms'][atomnumber].pos[1],visual_window_contents['bonds'][i].pos[1]) and difn.approx_equal(visual_window_contents['atoms'][atomnumber].pos[2],visual_window_contents['bonds'][i].pos[2])) or (difn.approx_equal(visual_window_contents['atoms'][atomnumber].pos[0],visual_window_contents['bonds'][i].pos[0]+visual_window_contents['bonds'][i].axis[0]) and difn.approx_equal(visual_window_contents['atoms'][atomnumber].pos[1],visual_window_contents['bonds'][i].pos[1]+visual_window_contents['bonds'][i].axis[1]) and difn.approx_equal(visual_window_contents['atoms'][atomnumber].pos[2],visual_window_contents['bonds'][i].pos[2]+visual_window_contents['bonds'][i].axis[2])):
			didraw.hide(visual_window_contents['bonds'][i])
	return True

def draw_kill_bond(bondnumber):
	global visual_window_contents
	#kill the bond
	didraw.hide(visual_window_contents['bonds'][bondnumber])
	return True

def numpyfree_thing(a,b):
	for i in range(len(a)):
		a[i]*=b[i]
	return a

def draw_kill_mass_do(start):
	global visual_window_contents
	if start[0]=='bond_mass':
		#both ends
		newkillpos = np.array([visual_window_contents['bonds'][start[1]].pos,visual_window_contents['bonds'][start[1]].pos+visual_window_contents['bonds'][start[1]].axis])
		visual_window_contents['bonds'][start[1]].visible = False
	elif start[0]=='atom_mass':
		#just the centre
		newkillpos = np.array([visual_window_contents['atoms'][start[1]].pos])
		visual_window_contents['atoms'][start[1]].visible = False
	
	# This section is done in terms of all objects in the visual window.
	# This means it doesn't update the visual_window_contents array stored by MmCalc.
	# This is not currently a problem, but may become one if more complex drawing
	# functionality is implemented.
	visual_objects = visual_window.objects
	visual_objects_type = np.array([i.__class__.__name__ for i in visual_window.objects],np.str) #class names are box, cylinder etc
	visual_objects_position = np.array([i.pos for i in visual_window.objects])
	visual_objects_axis = np.array([i.axis for i in visual_window.objects])
	
	#~ for i in range(len(visual_objects_position)):
		#~ print visual_objects_type[i],visual_objects_position[i],visual_objects_axis[i],visual_objects[i].visible
	
	# Do objects of that type have an axis? (currently only cylinders and not-cylinders...)
	# Axis for objects without one is typically (0,0,1): this is problematic because most lengths
	# in the visual window are in nm or so! Hence we need to remove those objects
	visual_objects_hasaxis = (visual_objects_type == 'cylinder')
	#print visual_objects_hasaxis.shape,visual_objects_position.shape,visual_objects_axis.shape
	visual_objects_otherend = visual_objects_position + numpyfree_thing(visual_objects_axis,visual_objects_hasaxis) #multiplying by visual_objects_hasaxis simply sets that term to zero for objects which don't have one...so otherend = position. This causes some double-counting.
	
	
	while len(newkillpos) > 0:
		print 'and again',newkillpos
		for i in range(len(newkillpos)):
			totaldeathlist = np.zeros(len(visual_objects),np.bool) #start all false--no-one has to die
			#~ visual_objects_visible = [j.visible for j in visual_objects] #we only want to delete to objects which are still visible
			#are any of the objects near the killpos being searched for and still visible?
			deathlist = np.logical_or(np.abs((visual_objects_position-newkillpos[i]).sum(axis=1)) < 1e-13,np.abs((visual_objects_otherend-newkillpos[i]).sum(axis=1)) < 1e-13)
			#~ deathlist = np.logical_and(np.logical_or(np.abs((visual_objects_position-newkillpos[i]).sum(axis=1)) < 1e-13,np.abs((visual_objects_otherend-newkillpos[i]).sum(axis=1)) < 1e-13),visual_objects_visible)
			
			
			#hide those marked for deletion
			for j in np.nonzero(deathlist)[0]: #nonzero returns an n-tuple for n-dimensional arrays; ours is only one long, so choose the first (and only) element
				print j
				visual_objects[j].visible = False
			
			#and add new casualties to the total death list this round
			totaldeathlist = np.logical_or(totaldeathlist,deathlist)
		
		#construct a new list of positions to kill
		newkillpos = np.append(np.compress(totaldeathlist,visual_objects_position,axis=0),np.compress(totaldeathlist,visual_objects_otherend,axis=0))
	print 'done'
	return True

#at the moment, this menu just has simple camera direction settings
def draw_view():
	global visual_window
	a = ui.option([
	['x','Cartesian x',False,''],
	['y','Cartesian y',False,''],
	['z','Cartesian z',False,'default']
	],'Choose a direction for the camera to look along')
	#if it's just a letter, update the value
	if a == 'x' or a == 'y' or a == 'z':
		update_value('draw','camera_direction',a)
		draw_change_camera_direction(a,draw)
	return draw

# Visual defines the 'forward' and 'up' properties of the visual window thus:
# http://vpython.org/contents/docs/visual/display.html
def draw_change_camera_direction(direction,returnto):
	#if it's a list, it's a custom direction and it's already defined
	if direction.__class__.__name__ == 'list':
		view = direction
	elif direction == 'x':
		view = [-1,0,0]
		sky  = [0,0,1]
	elif direction == 'y':
		view = [0,-1,0]
		sky  = [1,0,0]
	elif direction == 'z': #the default...
		view = [0,0,-1]
		sky  = [0,1,0]
	#and rotate it to the chosen direction with the chosen up vector
	global visual_window
	visual_window.forward = view
	visual_window.up      = sky
	
	return returnto

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
	return save_output('draw','visualisation settings',config.output_dir,'-visual',draw)

def draw_load():
	return load_output('draw','visualisation settings',config.output_dir,'-visual',draw)

def draw_povexport():
	global visual_window
	global visual_window_contents
	doexport = False
	while True:
		directory = config.output_dir
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