# coding=utf-8

import os
import sys
import numpy

import langen as lang
import config

width = config.console_width
write = sys.stdout.write

def clear():
	os.system(lang.clearcommand)
	
def get_user_input(q):
	return raw_input(q+' ')
	
def get_menu_input():
	return raw_input(lang.chooseoption+' ')

#word-wrap functon
#cheers to http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/148061
def wrap(text, width):
	return reduce(lambda line, word, width=width: '%s%s%s' %
				(line,
					' \n'[(len(line)-line.rfind('\n')-1
						+ len(word.split('\n',1)[0]
								) >= width)],
						word),
					text.split(' ')
				)

def message(text):
	write(wrap(text,width)+lang.newline)
	return True

def quit():
	exit()

def fatalerror(err):
	print lang.red + lang.bold + 'FATAL ERROR!' + lang.reset + '\n' + wrap(err, width)
	quit()

def title():
	version = "v1.0" #998 how to get hold of this from mmcalc main program variable called version?
	write(lang.bold + lang.underline + lang.gold + lang.bgblack + ' ' + lang.muon + ' ' + lang.reset +
	lang.red + lang.bold + lang.underline + ' ' + lang.programname + '  ' + lang.reset + lang.red + lang.underline + lang.url + " "*(width-len(lang.muon+lang.programname+lang.url+lang.version)-5) + lang.reset +
	lang.underline + lang.version + lang.reset + lang.newline*2)
	
def heading(text):
	return lang.newline + "="*(int((width-len(text)-2)/2)) + ' ' + text + ' ' + "="*(int((width-len(text)-2)/2)) + lang.newline

def draw_menu(menu):
	for [key,name,function,info] in menu:
		menuitem = ' ('+key.upper() + ')  ' + name
		if info == '':
			print menuitem
		else:
			padding = ' ('
			ending = ')'
			if len(info) > width - len(menuitem+padding+ending):
				info = info[:(width-len(menuitem+padding)-2)]+'…'
				write(menuitem + lang.grey + padding + info + lang.reset  + lang.newline)
			else:
				write(menuitem + lang.grey + padding + info + lang.grey + ending + lang.reset + lang.newline)
	write(lang.newline)
	
def get_user_choice(menu):
	while 1:
		a = get_menu_input()
		for item in menu:
			#if the key is the same as the one typed
			if item[0]==a.lower(): #change to lower case so upper case values work
				#return the relevant function
				return item[2]
				
def get_user_option(menu,notblank):
	while 1:
		a = get_menu_input()
		for item in menu:
			#if the key is the same as the one typed
			if item[0]==a:
				#return the relevant value
				return a
			elif a == '' and not notblank:
				return ''

def menu(menu,data=False):
	clear()
	title()
	if data != False:
		message(data)
	draw_menu(menu)
	return get_user_choice(menu)

def option(menu,notblank=False):
	clear()
	title()
	draw_menu(menu)
	return get_user_option(menu,notblank)

#eqmin and eqmax are True if a value is allowed to be equal to the respective bound, and False if it must be within those bounds
def inputscreen(q,type='string',min=False,max=False,eqmin=True,eqmax=True,notblank=False,validate=False,text='',number=False):
	clear()
	title()
	error=''
	write (text+'\n')
	while 1:
		write (lang.red+error+lang.reset+lang.newline)
		error=''
		a = get_user_input(q)
		#if it's blank, just go to the previous menu
		if a == '':
			if notblank is False:
				return False
			else:
				error='Please type something!'
		else:
			if type=='float':
				try:
					a = numpy.float(a)
				except: 
					error = a + ' is not a number. Please enter a valid number, eg 2, 3.142, 6.63e-34…'
			elif type=='int':
				try:
					a = numpy.int(a)
				except: 
					error = a + ' is not an integer. Please enter a whole number!'
			elif type=='complex':
				try:
					a = numpy.complex(a)
				except: 
					error = a + ' is not a valid complex number, eg 1, 5.7 + 3.4j… (remember to use j for √-1)'
			elif type=='float_or_string':
				try:
					a = numpy.float(a)
					type='float'
				except: 
					type='string' #don't worry if it doesn't work...it's just a string
			elif type=='intlist':
				a = a.split(',')
				if number is not False:
					if len(a) != number:
						error = 'You must enter exactly '+str(number)+' values'
				for i in range(len(a)):
					try:
						a[i] = numpy.int(a[i])
						if min is not False and eqmin is True:
							if a[i] < min:
								error = 'Values must all be >= ' + str(min)
						if min is not False and eqmin is False:
							if a[i] <= min:
								error = 'Values must all be > ' + str(min)
						if max is not False and eqmax is True:
							if a[i] > max:
								error = 'Values must all be <= ' + str(max)
						if max is not False and eqmax is False:
							if a[i] >= max:
								error = 'Values must all be < ' + str(max)
					except: 
						error = 'Please enter a comma-separated list of integers, eg 1,3,4,-5,15'
			elif type=='floatlist':
				a = a.split(',')
				if number is not False:
					if len(a) != number:
						error = 'You must enter exactly '+str(number)+' values'
				for i in range(len(a)):
					try:
						a[i] = numpy.float(a[i])
						if min is not False and eqmin is True:
							if a[i] < min:
								error = 'Values must all be >= ' + str(min)
						if min is not False and eqmin is False:
							if a[i] <= min:
								error = 'Values must all be > ' + str(min)
						if max is not False and eqmax is True:
							if a[i] > max:
								error = 'Values must all be <= ' + str(max)
						if max is not False and eqmax is False:
							if a[i] >= max:
								error = 'Values must all be < ' + str(max)
					except: 
						error = 'Please enter a comma-separated list of floats, eg 1.1,5,-6.666e19'
			elif type=='yn':
				if a[0] == 'y':
					return 'yes'
				elif a[0] == 'n':
					return 'no'
				else:
					error = 'Please enter y or n, yes or no.'
			if error == '' and type=='float' or type=='int':
				if min is not False and eqmin is True:
					if a < min:
						error = 'Value must be >= ' + str(min)
				if min is not False and eqmin is False:
					if a <= min:
						error = 'Value must be > ' + str(min)
				if max is not False and eqmax is True:
					if a > max:
						error = 'Value must be <= ' + str(max)
				if max is not False and eqmax is False:
					if a >= max:
						error = 'Value must be < ' + str(max)
			if validate is not False:
				valid,output = validate(a)
				if valid:
					return output
				else:
					error = output
			#if it's a string, anything goes...so don't even test it
			if error == '':
				return a

def get_filename(directory,suffix,default_filename='',text='',file_description=''):
	errtext = ''
	write (text+'\n')
	if file_description != '':
		file_description = ' '+file_description
	while True:
		if default_filename != '':
			filename = inputscreen('Please enter the filename'+file_description+' (blank for \''+default_filename+'\'):','str',notblank=False,text=errtext)
			if filename == False:
				filename = default_filename
		else:
			filename = inputscreen('Please enter the filename'+text+':','str',notblank=True)
		if os.path.exists(directory+'/'+filename+suffix):
			return filename
		else:
			errtext = "File '"+directory+'/'+filename+suffix+"' does not exist."
			
def info(info):
	print lang.grey + wrap(info, width) + lang.reset

def table(data):
	#make sure they're strings
	#998 catch if data is a different width on the way down...
	cellwidth = int(width/len(data[0]))
	table = ''
	for row in data:
		for cell in row:
			if len(cell) >= cellwidth:
				table += cell[:cellwidth-2]+"… "
			else:
				table += cell+" "*(cellwidth-len(cell))
		table += lang.newline
	return table

#http://stackoverflow.com/questions/775049/python-time-seconds-to-hms
def s_to_hms(seconds):
	m,s = divmod(seconds,60)
	h,m = divmod(m,60)
	return '%d:%02d:%02d' % (h,m,s)