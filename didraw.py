# coding=utf-8

#Python modules
try:
	import visual as v
except:
	print 'Error importing Visual Python. Please ensure it is installed.'
	exit()

import numpy as np
import difn
import math
import time

#initialise the scene
def initialise(stereo):
	return v.display(title='MµCalc', width=800, height=800,x=500,y=500, center=(0,0,0), background=(0.1,0.1,0.1),exit=False,stereo=stereo)

def hide(a):
	if a.__class__.__name__ == 'dict': #if it's a Python dictionary, do this function on all sub-elements thereof
		for key in iter(a):
			hide(a[key])
	elif  a.__class__.__name__ == 'list':
		for i in range(len(a)):
			hide(a[i])
	else: #if it's not a list or a dictionary, it must be a VPython object so hide it
		a.visible = False
	return a
	
#given 3 cartesian 3-vectors, this creates a simple scale value which will make spheres around the right size
def scale(a):
	#the average of the nontiny components of the crystal vectors
	return np.average(np.compress(np.ravel(a > 0.05*np.average(a)), a)) #(ravel flattens an array into 1D)

# turns a number from 0 to 1 into a rainbow colour bar colour, starting at blue and ending at red
# If x > 1 or x < 0, returns a cautionary black or white.
def col_rainbow(x):
	if(0 <= x <= 1):
		a = math.floor(x/0.25)%4
		s = (x - a*0.25)*4.0
		if(s==4.0): a,s=3,1.0 #this stops the error if x = 1.0...is there a better way?
		# blue - cyan
		if(a==0):
			return np.array([0,s,1])
		# cyan - green
		elif(a==1):
			return np.array([0,1,1-s])
		# green - yellow
		elif(a==2):
			return np.array([s,1,0])
		# yellow - red
		elif(a==3):
			return np.array([1,1-s,0])
	#if x < 0 was passed, return black
	elif(x < 0):
		return  np.array([0,0,0])
	#if x > 1 was passed, return white
	elif(x > 1):
		return  np.array([1,1,1])
	#if x is not numerical, return magenta
	elif(x > 1):
		return  np.array([1,0,1])

def col_rainbow_complex(r, theta,degrees=False):
	if(0 <= r <= 1):
		if(not(degrees)):
			#turn the angles into degrees
			deg = (theta * 180 / math.pi) % 360 #mod 360 to catch rounding errors
		a = math.floor(deg/60.0)%6
		s = (deg - a*60.0)/60.0
		if(s==6.0): a,s=5,1.0 #this stops the error if deg = 360.0...is there a better way?
		s = r*s #scale s with r
		# red - yellow
		if(a==0):
			return np.array([r,s,0])
		# yellow - green
		elif(a==1):
			return np.array([r-s,r,0])
		# green - cyan
		elif(a==2):
			return np.array([0,r,s])
		# cyan - blue
		elif(a==3):
			return np.array([0,r-s,r])
		# blue - magenta
		elif(a==4):
			return np.array([s,0,r])
		# magenta - red
		elif(a==5):
			return np.array([r,0,r-s])
	#if x < 0 was passed, return grey
	elif(r < 0):
		return  np.array([0.5,0.5,0.5])
	#if x > 1 was passed, return white
	elif(r > 1):
		return  np.array([1,1,1])
	#if x is not numerical, return light magenta
	else:
		return  np.array([1,0.9,1])
		
def col_rainbow_theta(theta,degrees=False):
	if(not(degrees)):
		#turn the angles into degrees
		deg = (theta * 180 / math.pi) % 360 #mod 360 to catch rounding errors/angles outside 0-360
	a = math.floor(deg/60.0)%6
	s = (deg - a*60.0)/60.0
	if(s==6.0): a,s=5,1.0 #this stops the error if deg = 360.0...is there a better way?
	# red - yellow
	if(a==0):
		return np.array([1,s,0])
	# yellow - green
	elif(a==1):
		return np.array([1-s,1,0])
	# green - cyan
	elif(a==2):
		return np.array([0,1,s])
	# cyan - blue
	elif(a==3):
		return np.array([0,1-s,1])
	# blue - magenta
	elif(a==4):
		return np.array([s,0,1])
	# magenta - red
	elif(a==5):
		return np.array([1,0,1-s])

def draw_crystal(r, attr, types):
	# draw atoms
	for i in range(len(r)):
		xyz,s = np.array(r[i]),np.array(attr[i])
		#choose colour depending on spin direction (make the col vector the unit vector)
		if (s[0]==0 and s[1]==0 and s[2]==0):
			col = np.array((0,0,0))
		else:
			col = s/np.sqrt(np.dot(s,s))
			#and if any are less than zero, add the complementary
			if col[0] < 0:
				col[1]-= col[0]
				col[2] -=col[0]
				col[0] = 0
			if col[1] < 0:
				col[0]-= col[1]
				col[2] -=col[1]
				col[1] = 0
			if col[2] < 0:
				col[0]-= col[2]
				col[1] -=col[2]
				col[2] = 0
		spingro = 0.2 #because mu_B is 10^-24, so we need to make it about ~10^-10 to display
		print xyz,s
		pointer = v.arrow(pos=xyz-s*spingro/2, axis=s*spingro, color=col)
		#draw spheres on the atom sites
		colour,size = atom_colours(types[i])
		pointer = v.sphere(pos=xyz, color=colour, radius=0.1*size)

	#draw a dot at the origin
	#pointer = v.sphere(pos=(0,0,0), color=(1,1,1), radius=0.35e-10)

	#draw a dot at the muon position
	#pointer = v.sphere(pos=a_cart[0]*mu_frac[0]+a_cart[1]*mu_frac[1]+a_cart[2]*mu_frac[2], color=(1,0.8,0), radius=0.15e-10)

def unitcell_init(a,scale):
	radius = 0.01*scale
	#initialise variable to return
	components = []
	#draw the cylinders (one for each vector at the origin, two of each other vector from the tip of each vector, one of each vector from the sum of each pair of vectors)
	for i in range(3):
		components.append(v.cylinder(pos=(0,0,0), axis=(a[i][0],a[i][1],a[i][2]), radius=radius))
		components.append(v.cylinder(pos=(a[(i+1)%3][0],a[(i+1)%3][1],a[(i+1)%3][2]), axis=(a[i][0],a[i][1],a[i][2]), radius=radius))
		components.append(v.cylinder(pos=(a[(i+2)%3][0],a[(i+2)%3][1],a[(i+2)%3][2]), axis=(a[i][0],a[i][1],a[i][2]), radius=radius))
		components.append(v.cylinder(pos=(a[(i+1)%3][0]+a[(i+2)%3][0],a[(i+1)%3][1]+a[(i+2)%3][1],a[(i+1)%3][2]+a[(i+2)%3][2]), axis=(a[i][0],a[i][1],a[i][2]), radius=radius))
	return components

def bonds(bonds,scale):
	default_bond_radius = 0.01
	#initialise variable to return
	components = []
	#draw the cylinders (one for each vector at the origin, two of each other vector from the tip of each vector, one of each vector from the sum of each pair of vectors)
	for bond in bonds:
		if bond[2] is not False:
			colour = list(np.array(bond[2],np.float)/255)
		else:
			colour = [1,1,1]
		#if
		if bond[3] == 'd':
			radius = scale*default_bond_radius
		elif bond[3] == 'r':
			radius = bond[4]*scale*default_bond_radius
		elif bond[3] == 'n':
			radius = bond[4]*difn.nano
		elif bond[3] == 'm':
			radius = bond[4]
		elif bond[3] == 'a':
			radius = bond[4]*difn.angstrom
		components.append(v.cylinder(pos=bond[0], axis=bond[1]-bond[0], radius=radius, color=colour))
	return components

def draw_atoms(r,name,q,mu,colourtype,scale,custom):
	default_atom_size = 0.05
	atoms = []
	for i in range(len(r)):
		if not custom.has_key(name[i]) or custom[name[i]]['visible']:
			size = False
			colour = False
			opacity = 1.0
			if custom.has_key(name[i]):
				if custom[name[i]]['colour'] is not False:
					colour = (float(custom[name[i]]['colour'][0])/255.,float(custom[name[i]]['colour'][1])/255.,float(custom[name[i]]['colour'][2])/255.)
				if custom[name[i]]['size_unit'] == 'r':
					size = custom[name[i]]['size']*scale*default_atom_size
				elif custom[name[i]]['size_unit'] == 'n':
					size = custom[name[i]]['size']*difn.nano
				elif custom[name[i]]['size_unit'] == 'm':
					size = custom[name[i]]['size']
				elif custom[name[i]]['size_unit'] == 'a':
					size = custom[name[i]]['size']*difn.angstrom
				if custom[name[i]]['opacity'] is not False:
					opacity = custom[name[i]]['opacity']
			if colour is False:
				if colourtype == 'e':
					if element_colours.has_key(name[i]):
						colour = element_colours[name[i]]
					else:
						colour = (0,0,0) #if it's not a recognised element, make it black 998 or a better colour?
				if colourtype == 'c':
					if q[i] == 0:
						colour = (0,0,0)
					else:
						colourval = float(q[i])/4. # +/-4 is the largest charge we might reasonably expect
						if abs(colourval) > 1: #slightly odd coding because charge can be +/-
							colourval = colourval/abs(colourval)
						if colourval > 0:
							colour = (colourval,0,0) #red
						else:
							colour = (0,0,-colourval) #blue
			if size is False:
				size = scale*default_atom_size
			atoms.append(v.sphere(pos=r[i], color=colour, radius=size, opacity=opacity))
	return atoms

#~ def draw_unit_cell_atoms(r,names,scale,offset=[0,0,0],fenceposts=True):
	#~ #if fenceposts is true, then get adjacent atoms
	#~ if fenceposts:
		#~ atoms_r,atoms_names = difn.unit_cell_shared_atoms(r,names)
	#~ #otherwise, just use atoms already generated
	#~ else:
		#~ atoms_r = []
		#~ atoms_names = []
		#~ for i in range(len(r)):
			#~ atoms_r.append(r[i])
			#~ atoms_names.append(names[i])
	#~ return draw_atoms(atoms_r,atoms_names,scale)

def scalar_field(r,phi,phimin=0,phimax=0,colourtype='rainbow',scale=1):
	field = []
	#work out limits of phi if not provided
	if(phimin==phimax==0):
		phimin = np.min(np.abs(phi))
		phimax = np.max(np.abs(phi))
		#if they're the same because all passed field values are identical
		if(phimin==phimax):
			phimin = 0
	
	for i in range(len(r)):
		#colour from black to white at fmax
		val = (np.abs(phi[i]-phimin))/(phimax-phimin)
		if(colourtype=='rainbow'):
			colour = col_rainbow(val)
			opacity = 1.0
		elif(colourtype=='bw'):
			colour = (val,val,val)
			opacity = 1.0
		elif(colourtype=='rainbow_complex'):
			colour = col_rainbow_complex(val,np.angle(phi[i]))
			opacity = 1.0
		elif(colourtype=='rainbow_complex_transparency'):
			colour = col_rainbow_theta(np.angle(phi[i]))
			opacity = val*0.95 + 0.05 #make it such that the minimum opacity is not zero
		field.append(v.sphere(pos=r[i], color=colour, radius=0.1*scale, opacity=opacity))
	return field

def vector_field(r,vec,vmin,vmax,colourtype,lengthtype,scale):
	field = []
	#work out limits of phi if not provided
	if(vmin==vmax==0):
		vmin,vmax = difn.vector_min_max(vec)
		#if they're the same because all passed field values are identical
		if(vmin==vmax):
			vmin = 0
	v_unit = difn.unit_vectors(vec)	
	for i in range(len(r)):
		modv = np.sqrt(np.dot(vec[i],vec[i]))
		val = (modv-vmin)/(vmax-vmin)
		if colourtype == 'fadetoblack':
			colour = (val,val,val)
		elif colourtype == 'rainbow':
			colour = col_rainbow(val)
			opacity = 1.0
		else:
			colour = (1,1,1) #default to white if nothing is specified
		if lengthtype.__class__.__name__ == 'float' or lengthtype.__class__.__name__ == 'int':
			length = np.float(lengthtype)
		elif lengthtype == 'proportional':
			length = val
		else:
			length = 1
		if length != 0:
			scalefactor = 0.3
			field.append(v.arrow(pos=r[i]-0.5*length*scale*scalefactor*v_unit[i], axis=length*scale*scalefactor*v_unit[i], color=colour)) #length needs to be determined automatically
	return field
	
def points(r,scale):
	field = []
	for i in range(len(r)):
		size = scale*0.07
		field.append(v.box(pos=r[i], length=size, height=size, width=size, color=(0,1,1)))
	return field

def freq_limits(r,f,fsmall,fbig,colour):
	#colour from black to white at fmax
	if f > fsmall and f < fbig:
		pointer = v.box(pos=r, color=colour, length=0.1e-10,height=0.1e-10,width=0.1e-10)

def get_event(scene):
	#delete all pre-existing events in the Visual Python cache
	scene.mouse.events = 0
	while scene.kb.keys:
		s = scene.kb.getkey() #there appears to be no way to do this all in one go
	#start the continual loop awaiting an event
	while True:
		if scene.mouse.events:
			return {'type':"click",'event':scene.mouse.getclick()}
		if scene.kb.keys: #is there a keyboard event waiting to be processed?
			return {'type':"keypress",'event':scene.kb.getkey()}

element_colours = {
'H':(255.0/255,255.0/255,255.0/255),
'He':(217.0/255,255.0/255,255.0/255),
'Li':(204.0/255,128.0/255,255.0/255),
'Be':(194.0/255,255.0/255,0.0/255),
'B':(255.0/255,181.0/255,181.0/255),
'C':(144.0/255,144.0/255,144.0/255),
'N':(48.0/255,80.0/255,248.0/255),
'O':(255.0/255,13.0/255,13.0/255),
'F':(144.0/255,224.0/255,80.0/255),
'Ne':(179.0/255,227.0/255,245.0/255),
'Na':(171.0/255,92.0/255,242.0/255),
'Mg':(138.0/255,255.0/255,0.0/255),
'Al':(191.0/255,166.0/255,166.0/255),
'Si':(240.0/255,200.0/255,160.0/255),
'P':(255.0/255,128.0/255,0.0/255),
'S':(255.0/255,255.0/255,48.0/255),
'Cl':(31.0/255,240.0/255,31.0/255),
'Ar':(128.0/255,209.0/255,227.0/255),
'K':(143.0/255,64.0/255,212.0/255),
'Ca':(61.0/255,255.0/255,0.0/255),
'Sc':(230.0/255,230.0/255,230.0/255),
'Ti':(191.0/255,194.0/255,199.0/255),
'V':(166.0/255,166.0/255,171.0/255),
'Cr':(138.0/255,153.0/255,199.0/255),
'Mn':(156.0/255,122.0/255,199.0/255),
'Fe':(224.0/255,102.0/255,51.0/255),
'Co':(240.0/255,144.0/255,160.0/255),
'Ni':(80.0/255,208.0/255,80.0/255),
'Cu':(200.0/255,128.0/255,51.0/255),
'Zn':(125.0/255,128.0/255,176.0/255),
'Ga':(194.0/255,143.0/255,143.0/255),
'Ge':(102.0/255,143.0/255,143.0/255),
'As':(189.0/255,128.0/255,227.0/255),
'Se':(255.0/255,161.0/255,0.0/255),
'Br':(166.0/255,41.0/255,41.0/255),
'Kr':(92.0/255,184.0/255,209.0/255),
'Rb':(112.0/255,46.0/255,176.0/255),
'Sr':(0.0/255,255.0/255,0.0/255),
'Y':(148.0/255,255.0/255,255.0/255),
'Zr':(148.0/255,224.0/255,224.0/255),
'Nb':(115.0/255,194.0/255,201.0/255),
'Mo':(84.0/255,181.0/255,181.0/255),
'Tc':(59.0/255,158.0/255,158.0/255),
'Ru':(36.0/255,143.0/255,143.0/255),
'Rh':(10.0/255,125.0/255,140.0/255),
'Pd':(0.0/255,105.0/255,133.0/255),
'Ag':(192.0/255,192.0/255,192.0/255),
'Cd':(255.0/255,217.0/255,143.0/255),
'In':(166.0/255,117.0/255,115.0/255),
'Sn':(102.0/255,128.0/255,128.0/255),
'Sb':(158.0/255,99.0/255,181.0/255),
'Te':(212.0/255,122.0/255,0.0/255),
'I':(148.0/255,0.0/255,148.0/255),
'Xe':(66.0/255,158.0/255,176.0/255),
'Cs':(87.0/255,23.0/255,143.0/255),
'Ba':(0.0/255,201.0/255,0.0/255),
'La':(112.0/255,212.0/255,255.0/255),
'Ce':(255.0/255,255.0/255,199.0/255),
'Pr':(217.0/255,255.0/255,199.0/255),
'Nd':(199.0/255,255.0/255,199.0/255),
'Pm':(163.0/255,255.0/255,199.0/255),
'Sm':(143.0/255,255.0/255,199.0/255),
'Eu':(97.0/255,255.0/255,199.0/255),
'Gd':(69.0/255,255.0/255,199.0/255),
'Tb':(48.0/255,255.0/255,199.0/255),
'Dy':(31.0/255,255.0/255,199.0/255),
'Ho':(0.0/255,255.0/255,156.0/255),
'Er':(0.0/255,230.0/255,117.0/255),
'Tm':(0.0/255,212.0/255,82.0/255),
'Yb':(0.0/255,191.0/255,56.0/255),
'Lu':(0.0/255,171.0/255,36.0/255),
'Hf':(77.0/255,194.0/255,255.0/255),
'Ta':(77.0/255,166.0/255,255.0/255),
'W':(33.0/255,148.0/255,214.0/255),
'Re':(38.0/255,125.0/255,171.0/255),
'Os':(38.0/255,102.0/255,150.0/255),
'Ir':(23.0/255,84.0/255,135.0/255),
'Pt':(208.0/255,208.0/255,224.0/255),
'Au':(255.0/255,209.0/255,35.0/255),
'Hg':(184.0/255,184.0/255,208.0/255),
'Tl':(166.0/255,84.0/255,77.0/255),
'Pb':(87.0/255,89.0/255,97.0/255),
'Bi':(158.0/255,79.0/255,181.0/255),
'Po':(171.0/255,92.0/255,0.0/255),
'At':(117.0/255,79.0/255,69.0/255),
'Rn':(66.0/255,130.0/255,150.0/255),
'Fr':(66.0/255,0.0/255,102.0/255),
'Ra':(0.0/255,125.0/255,0.0/255),
'Ac':(112.0/255,171.0/255,250.0/255),
'Th':(0.0/255,186.0/255,255.0/255),
'Pa':(0.0/255,161.0/255,255.0/255),
'U':(0.0/255,143.0/255,255.0/255),
'Np':(0.0/255,128.0/255,255.0/255),
'Pu':(0.0/255,107.0/255,255.0/255),
'Am':(84.0/255,92.0/255,242.0/255),
'Cm':(120.0/255,92.0/255,227.0/255),
'Bk':(138.0/255,79.0/255,227.0/255),
'Cf':(161.0/255,54.0/255,212.0/255),
'Es':(179.0/255,31.0/255,212.0/255),
'Fm':(179.0/255,31.0/255,186.0/255),
'Md':(179.0/255,13.0/255,166.0/255),
'No':(189.0/255,13.0/255,135.0/255),
'Lr':(199.0/255,0.0/255,102.0/255),
'Rf':(204.0/255,0.0/255,89.0/255),
'Db':(209.0/255,0.0/255,79.0/255),
'Sg':(217.0/255,0.0/255,69.0/255),
'Bh':(224.0/255,0.0/255,56.0/255),
'Hs':(230.0/255,0.0/255,46.0/255),
'Mt':(235.0/255,0.0/255,38.0/255)
}