from numpy import *
from numpy.linalg import *
from math import pi
import random

# === CONSTANTS === #
# physical
gamma_mu = 135.538817*1e6 # Hz/T   muon gyromagnetic ratio   http://www.ebyte.it/library/educards/constants/ConstantsOfPhysicsAndMath.html
mu_B = 9.2740091e-24 # J/T    Bohr magneton   http://physics.nist.gov/cgi-bin/cuu/Value?mub
# units
nano = 1.0e-9 # nm in m
angstrom = 1.0e-10 #angstrom in m
# computational
epsilon = finfo(float).eps #epsilon is the tiny error on floating-point calculations

# === FUNCTIONS === #

# zero_if_close
# --------------------------
# Named in analogy to NumPy's real_if_close, this returns zero if the input is within epsilon of it.
# ---
# INPUT
# x = a number or array
# ---
# OUTPUT
# x = 0 is close, x otherwise
def zero_if_close(x,tolerance=100):
	global epsilon
	try:
		for i in range(len(x)):
			x[i] = zero_if_close(x[i])
		return x
	except:
		if abs(x) < epsilon*tolerance:
			return 0
		return x

def modulus(a):
	return sqrt(dot(a,a))

# triclinic
# --------------------------
# Turns an a, b, c, alpha, beta and gamma into a vector of three vectors; a, b and c in cartesians.
# See http://www.mse.mtu.edu/~drjohn/my3200/stereo/sg4.html
# ---
# INPUT
# a = array of three scalars: the magnitude of the primitive translation vectors / m
# alpha = array of three scalars: crystallographic angles / degrees
# ---
# OUTPUT
# a_cartesian = array of three three-component vectors: the primitive translation vectors in cartesian coordinates / m
def triclinic(a,alpha):
	#convert angles to radians
	alpha_rad = alpha * pi/180.
	# a = |a| (sin(beta), 0, cos(beta))
	a_cartesian = a[0]*array((sin(alpha_rad[1]),0,cos(alpha_rad[1])))
	# b = |b| (sin(alpha)cos(delta), sin(alpha)sin(delta), cos(alpha))
	# where delta is the angle of |b| projected onto the xy-plane
	cos_delta = (cos(alpha_rad[2])-cos(alpha_rad[0])*cos(alpha_rad[1]))/(sin(alpha_rad[0])*sin(alpha_rad[1]))
	# if an invalid set of alpha, beta and gamma is entered, delta is impossible to compute
	if abs(cos_delta) > 1.:
		print 'ERROR: alpha, beta and gamma are not geometrically consistent'
		return False
	sin_delta = sin(arccos(cos_delta))
	b_cartesian = a[1]*array((sin(alpha_rad[0])*cos_delta,sin(alpha_rad[0])*sin_delta,cos(alpha_rad[0])))
	# c = (0, 0, |c|)
	c_cartesian = array((0,0,a[2]))
	return array((a_cartesian,b_cartesian,c_cartesian))

# reciplatt
# --------------------------
# Turns a 3x3 array of cartesian vectors into their reciprocal lattice vectors.
# ---
# INPUT
# a = array of three three-component vectors: the primitive translation vectors in cartesian coordinates / m
# ---
# OUTPUT
# a_star = array of three three-component vectors: the primitive translation vectors of the reciprocal lattice in cartesian coordinates / m^-1
def reciplatt(a):
	v = dot(a[0],cross(a[1],a[2])) #v = a . b x c
	a_star = cross(a[1],a[2])/v #a* = b x c / v
	b_star = cross(a[2],a[0])/v #b* = c x a / v
	c_star = cross(a[0],a[1])/v #c* = a x b / v
	return array((a_star,b_star,c_star))
	
#to append a 3-vector to an array
def vector_append(a,v):
	return reshape(append(a,v),(-1,3))

#to create a blank array suitable for adding vectors to...actually not very exciting but safer in case I do think of a clever way of doing it
def blank_vector_array():
	return array([])

def unit_cell_shared_atoms(r,attr):
	atoms_r = blank_vector_array()
	atoms_attr = []
	for i in range(len(r)):
		atoms_r = vector_append(atoms_r,r[i])
		atoms_attr.append(attr[i])
		iszero = (array(r[i]) == 0)
		numberofzeroes = iszero.tolist().count(True) #NumPy appears not to have a count function, so must convert to a Python list first
		#do nothing if there are no zeros
		if numberofzeroes == 1: #if there's only one zero...
			extra_r = copy(r[i]) #this must be copied or NumPy simply adds another reference to the array
			for j in range(3):
				if iszero[j]:
					extra_r[j] = 1
					break #there's only one, so no point in keepin' loopin'
			atoms_r = vector_append(atoms_r,extra_r)
			atoms_attr.append(attr[i])
		if numberofzeroes == 2: #if there are two zeros...
			permutations = [[0,1],[1,0],[1,1]]
			for k in range(3): #3 for 3 permutations
				l = 0
				extra_r = copy(r[i])
				for j in range(3):
					if iszero[j]:
						extra_r[j] = permutations[k][l]
						l += 1 #probably an if...break statement would take longer than just doing the loop once more..?
				atoms_r = vector_append(atoms_r,extra_r)
				atoms_attr.append(attr[i])
		if numberofzeroes ==3: #if it's three, just lob in all the permutations
			permutations = [[1,0,0],[0,1,0],[0,0,1],[1,1,0],[1,0,1],[0,1,1],[1,1,1]]
			for k in range(7): #7 for 7 permutations
				extra_r = permutations[k]
				atoms_r = vector_append(atoms_r,extra_r)
				atoms_attr.append(attr[i])
	return atoms_r,atoms_attr

# max_radius
# --------------------------
# Evaluates the maximum radius from the quantity entered by the user, usually by multiplying a number of unit
# cells by a side length.
# ---
# INPUT
# r_user = user-specified radius, usually / unit cells, possibly / m
# a = array of three scalars: the magnitude of the primitive translation vectors / m
# mode = specifies whether r_user is in a, b or c lengths or simply in m: currently does nothing
# ---
# OUTPUT
# r = the sphere's radius / m
def max_radius(n_user,a,mode):
	r = n_user * sqrt(dot(a[0],a[0]))
	# It's a bit daft to work out the length of the user with sqrt(mod^2) when it's entered as a parameter, but I'm going to leave it like that to save passing the real
	# crystal parameters and messing up the code. Also, it's unimportant because the program will round up when calculating this, so the worst one will get is an
	# extra point. Boo hoo.
	return r

# crystal_size
# --------------------------
# This works out the size of a parallelpipedal crystal which will contain a cube of side 2*r_max, and thus will certainly (?)
# contain a sphere of radius r_max.
# It does it by solving the simultaneous equations that make sure that the cube is escaped on each of the cartesian axes,
# and thus hopefully will be escaped in all directions. Is that a good idea?
# ---
# INPUT
# a = array of three scalars: the magnitude of the primitive translation vectors / m
# alpha = array of three scalars: crystallographic angles / degrees
# r = radius of sphere / m
# ---
# OUTPUT
# n = vector of side lengths along a, b and c in number of unit cells
def minimum_para_for_sphere(a,alpha,r):
	#a vector of three ones, for normalised a = b = c = 1
	a_norm = ones((3),float)
	a_cart_norm = triclinic(a_norm,alpha)
	#compute plane normals
	N = zeros((3,3),float)
	for i in range(3):
		#N = axb, bxc, cxa
		N[i] = cross(a_cart_norm[i%3],a_cart_norm[(i+1)%3])
		#normalise normals
		N[i] /= sqrt(dot(N[i],N[i]))
	#position of parallelepiped vertex in the positive octant
	ABC = r*(cross(N[0],N[1])+cross(N[1],N[2])+cross(N[2],N[0]))/dot(N[0],cross(N[1],N[2]))
	#get vertex coordinates in abc, rather than xyz, coordinates
	A = dot(transpose(inv(a_cart_norm)),ABC)
	#get number of unit cells in each direction
	n = A/a
	n = array(ceil(n)+1,int) #add one for paranoia
	return n

# make_para_crystal
# --------------------------
# Returns two arrays, one containing atom positions and the other containing attributes (which can have any
# dimensionality - charge, spin, mass etc) in a parallelepipedal crystal of size n1xn2xn3.
# The attribute in the case of the dipole field calculations is magnetic moment.
# ---
# INPUT
# a = array of three three-component vectors: the primitive translation vectors in cartesian coordinates / m
# atoms = a 4D array of all the atoms in the unit cell - three components of cartesian coordinates of atom positions
#    plus an array in the fourth dimension representing the property you're distributing throughout the cell
# n = three-component array containing the number of atoms in each crystallographic direction
# ---
# OUTPUT
# r_i = array of N three-component vectors corresponding to the spatial coordinates of the atoms within the crystal
# attr_i = array of N vectors corresponding to the attributes of the atoms - magnetic moment in the case of the dipole
#    field calculations
def make_para_crystal(a, r_atoms, m, k, q_atoms, name_atoms, L1, L2):
	#make copies of L1 and L2 so as not to mess about in the outside world
	#see http://stackoverflow.com/questions/575196/python-variable-scope-and-function-calls and http://effbot.org/zone/python-list.htm
	L1 = array(list(L1))
	L2 = array(list(L2))
	#make sure that L2 > L1
	for i in range(3):
		if (L1[i] > L2[i]):
			L1[i],L2[i] = L2[i],L1[i]
		elif(L1[i]==L2[i]):
			print "ERROR: crystal is of zero size in one dimension!!!"
	#add one to the larger value, so the crystal is drawn as expected to, rather than to just before, the upper limit
	#L1 += array([1,1,1])
	L2 += array([1,1,1])
	N = (L2[0]-L1[0])*(L2[1]-L1[1])*(L2[2]-L1[2])*len(r_atoms)
	r = zeros((N,3),float) #positions
	q = zeros((N),float) #charges
	mu = zeros((N,3),float) #magnetic moments
	names = []
	T = zeros((3),int) #lattice translation vector
	i = 0 #incrementing variable
	for T[0] in range(L1[0],L2[0]):
		for T[1] in range(L1[1],L2[1]):
			for T[2] in range(L1[2],L2[2]):
				for l in range(len(r_atoms)):
					#atomic positions
					for j in range(3):
						#position = unit cell position + atomic displacement
						r[i][j] = (a[0][j]*T[0]+a[1][j]*T[1]+a[2][j]*T[2])+(r_atoms[l][0]*a[0][j]+r_atoms[l][1]*a[1][j]+r_atoms[l][2]*a[2][j])
					#atomic magnetic moments, possibly modulated by k
					if m[l] is not False:
						for j in range(len(m[l])):
							mu[i] += m[l][j]*exp(-2*pi*1j*dot(k[l][j], T)) #M_j = sum of (m_j,k * e^(-2piik.T))
							#(k is in integers, as is T, because it's computationally pointless to turn them into real length vectors only to undo this by multiplying them by one-another in the exponent here)
							#999 if the imaginary part is tiny, lose it
					else:
						mu[i] = 0
					q[i] = q_atoms[l]
					names.append(name_atoms[l])
					i += 1
	return r,q,mu,names

#structure factor of a scalar field
# G = reciprocal lattice vector
# f = array of field values
# r = corresponding array of positions
def Ss(G,f,r):
	S =  0.0 + 0.0j
	for i in range(len(r)):
		S += f[i] * exp(2*pi*1j*dot(G,r[i]))
	return S
	
#structure factor of a vector field
# G = reciprocal lattice vector
# v = array of field vectors
# r = corresponding array of positions
def Sv(G,v,r):
	S =  0.0 + 0.0j
	for i in range(len(r)):
		S += 1j*dot(v[i],G) * exp(2*pi*1j*dot(G,r[i]))
	return S
		
#add support for magnetic k vectors - should be doable 999
def make_para_recip(astar, r_unit, q_unit, m_unit, L1,L2):
	#make copies of L1 and L2 so as not to mess about in the outside world
	#see http://stackoverflow.com/questions/575196/python-variable-scope-and-function-calls and http://effbot.org/zone/python-list.htm
	L1 = array(list(L1))
	L2 = array(list(L2))
	#make sure that L2 > L1
	for i in range(3):
		if (L1[i] > L2[i]):
			L1[i],L2[i] = L2[i],L1[i]
		elif(L1[i]==L2[i]):
			print "ERROR: crystal is of zero size in one dimension!!!"
	#add one to the larger value, so the crystal is drawn as expected to, rather than to just before, the upper limit
	L2 += array([1,1,1])
	N = (L2[0]-L1[0])*(L2[1]-L1[1])*(L2[2]-L1[2])
	G = zeros((N,3),float) #one array element per atom containing three reciprocal-spatial coordinates
	Sq = zeros((N),complex) #structure factor in units of charge
	Smu = zeros((N),complex) #structure factor in units of magnetic moment
	Gn = zeros((3),int) #reciprocal lattice vector in reciprocal lattice vectors
	u = zeros((3),int)
	i = 0
	for Gn[0] in range(L1[0],L2[0]):
		for Gn[1] in range(L1[1],L2[1]):
			for Gn[2] in range(L1[2],L2[2]):
				#if we're not at the origin...
				if(not(Gn.all == 0)):
					G[i] = dot(Gn[0],astar[0])+dot(Gn[1],astar[1])+dot(Gn[2],astar[2])#+Gn[1]*astar[1]+Gn[2]*astar[2]
					Sq[i] = Ss(G[i],q_unit,r_unit)
					Smu[i] = Sv(G[i],m_unit,r_unit)
					i += 1
	return G,Sq,Smu

def make_recip_sph(para_Q, para_Sq, para_Smu, r_max):
	keep = zeros((len(para_Q)), "int")
	r_max_2 = r_max**2
	for i in range(len(para_Q)):
		r_2 = para_Q[i][0]**2+para_Q[i][1]**2+para_Q[i][2]**2
		if r_2 <= r_max_2:
			keep[i] = 1
	#then, discard the ones for which keep[i] is still zero
	sph_Q = compress(keep, para_Q, axis=0)
	sph_Sq =  compress(keep, para_Sq, axis=0)
	sph_Smu =  compress(keep, para_Smu, axis=0)
	return sph_Q, sph_Sq, sph_Smu

#Find the denominator of a fraction, ie the smallest number you can multiply a rational number by to obtain an integer
# x = a rational number
# max = the largest denominator to try
def find_denominator(x,max):
	for d in xrange(1,max):
		testint = x * d
		if testint == int(real(testint)): #999 this line means that the function only looks at the real part...think about how to fix that!!
			return d
			break
	return 0

#http://www.uselesspython.com/download.php?script_id=218
def GCF(x):
	y = x[0]
	for i in range(len(x)-1):
		x1 = y
		x2 = x[i+1]
		if x1 < x2:
			x1,x2=x2,x1
		while x1 - x2 :
			x3 = x1 - x2
			x1 = max(x2,x3)
			x2 = min(x2,x3)
		y = x1
	return y

def LCM(x):
	y = x[0]
	for i in range(len(x)-1):
		x1 = y
		x2 = x[i+1]
		z = GCF([x1,x2])
		y = z * x1/z * x2/z
	return y

def mag_unit_cell_size(k):
	#999 calling this L is all very well, except I call it n elsewhere - standardise (I actually think on L...)
	Lmax = 100 #this is the maximum size of the unit cell in any dimension
	Lall = ones((len(k),3),int) #these will be the repeat distances of each k-vector
	L = ones((3),int) #this will be the total repeat distance in all dimensions
	#go through each atom...
	for j in range(len(k)):
		if k[j] is not False:
			#and each k-vector...
			for l in range(len(k[j])):
				#and each spatial dimension...
				for i in range(3):
					#...and find out how long it takes to repeat
					Lall[j][i] = find_denominator(k[j][l][i],Lmax)
	#transpose L such that all x ordinates are in the first row etc
	Lall = transpose(Lall)
	#go through each dimension...
	for i in range(3):
		L[i] = LCM(Lall[i])
	return L

# randomise_sites
# --------------------------
# Takes a crystal with all sites occupied by magnetic ions and randomly removes some to simulate random occupation.
# I'm not sure if this is the best way to do this in general, but it's the best for the Ni2Al system this was programmed for.
# It only works in this fairly simple case! It takes no account of different types of magnetic site, or any positional info.
# It may be necessary in a more complex case to put the randomiser inside the crystal-building function. However,
# this version has the advantage of speed of re-randomisation, not needing to re-make the whole crystal.
# It requires saving a copy of the unrandomised sites (ie all occupied) if you want to re-run the function.
# ---
# INPUT
# attr = array of N vectors corresponding to the attributes of the atoms - magnetic moment in the case of the dipole
#    field calculations
# p = probability of occupancy by a magnetic ion
# ---
# OUTPUT
# attr = the newly-culled-at-random occupied sites
def randomise_sites(attr,p):
	for i in range(len(attr)):
		#then, randomly choose whether it's occupied or not
		if random.random() < p:
			attr[i] *= 1
		else:
			attr[i] *= 0
	return attr

# make_crystal_sph
# --------------------------
# Takes a parallelepiped crystal (well, any shape actually) and shaves its outsides off beyond a certain radius.
# ---
# INPUT
# para_pos = array of N three-component vectors corresponding to the spatial coordinates of the atoms within the crystal
# para_attr = array of N vectors corresponding to the attributes of the atoms - magnetic moment in the case of the dipole
#    field calculations
# r_max = radius of sphere / m
# ---
# OUTPUT
# sph_pos, sph_attr = the equivalents in the shaved crystal
def make_crystal_sph(para_pos, para_attr, para_q, para_names, r_max):
	keep = zeros((len(para_pos)), "int")
	r_max_2 = r_max**2
	for i in range(len(para_pos)):
		r_2 = para_pos[i][0]**2+para_pos[i][1]**2+para_pos[i][2]**2
		if r_2 <= r_max_2:
			keep[i] = 1
	#then, discard the ones for which keep[i] is still zero
	sph_pos = compress(keep, para_pos, axis=0)
	sph_attr =  compress(keep, para_attr, axis=0)
	sph_q =  compress(keep, para_q, axis=0)
	sph_names =  compress(keep, para_names, axis=0)
	return sph_pos, sph_attr, sph_q, sph_names

# make_crystal_trim_para
# --------------------------
# Takes a parallelepiped crystal and shaves off excess extra atoms around the outside.
# ---
# INPUT
# para_pos = array of N three-component vectors corresponding to the spatial coordinates of the atoms within the crystal
# para_attr = array of N vectors corresponding to the attributes of the atoms - magnetic moment in the case of the dipole
#    field calculations
# r_max = radius of sphere / m
# ---
# OUTPUT
# sph_pos, sph_attr = the equivalents in the shaved crystal
def make_crystal_trim_para(r_in, q_in, mu_in, names_in, a, L):
	r_out = []
	q_out = []
	mu_out = []
	names_out = []
	#allow a small error, say 0.1%
	L = array(L,float)*1.001
	for i in range(len(r_in)):
		#multiply x through with the inverse of a to solve the equations
		n = array(dot(inv(transpose(a)),r_in[i])) #for some reason, NumPy uses dot() to signify matrix multiplication of arrays
		if n[0] < L[0] and n[1] < L[1] and n[2] < L[2]: #if it's inside the parallelepiped
			r_out.append(r_in[i])
			q_out.append(q_in[i])
			mu_out.append(mu_in[i])
			names_out.append(names_in[i])
	return r_out, q_out, mu_out, names_out

# make_crystal
# --------------------------
# This is just a neat accumulation of several functions which eventually result in a spherical vcrystal of
# with the specified parameters and the appropriate dimensions.
# ---
# INPUT
# n_user = radius of sphere specified by user - currently in units of a, but will be specifiable
# a = array of three three-component vectors: the primitive translation vectors in cartesian coordinates
# atoms = array of three-component vectors specifying the cartesian coordinates of all atoms in a unit cell
# ---
# OUTPUT
# n = 
def make_crystal(r_sphere,a,alpha,r_atoms,m_atoms,k_atoms, q_atoms, name_atoms,type='all'):
	#radius over which to do dipole calculation
	r_max = max_radius(r_sphere,a,999) #999 means 'add in mode switch'
	#work out how many unit cells in each direction
	L = minimum_para_for_sphere(a,alpha,r_max)
	a_cart = triclinic(a,alpha)
	#strip atoms if type switch is set
	if type == 'magnetic':
		for i in range(len(r_atoms)-1,-1,-1): #go through backwards so popping does not cock things up
			if m_atoms[i] is False:
				r_atoms.pop(i)
				m_atoms.pop(i)
				k_atoms.pop(i)
				q_atoms.pop(i)
				name_atoms.pop(i)
	#make a crystal from -L to L
	r_i,mu_i, q,names = make_para_crystal(a_cart, r_atoms, m_atoms, k_atoms, q_atoms, name_atoms, -L, L)
	#shave off excess points in the currently-parallelepiped crystal
	r_i, mu_i,q,names = make_crystal_sph(r_i, mu_i, q,names, r_max)
	return L,r_i,mu_i,q,names,r_max

#given a vector of vectors, this returns a vector of unit vectors
def unit_vectors(vectors):
	#999 is there a unit(blah) function?
	i = 0
	unit_vectors = zeros((len(vectors),3), float)
	for vector in vectors:
		#if it's 0,0,0, the unit vector is 0,0,0
		if (vector[0]==0 and vector[1]==0 and vector[2]==0):
			unit_vectors[i] = array((0,0,0))
		else:
			unit_vectors[i] = vector/sqrt(dot(vector,vector))
		i += 1
	return unit_vectors
	
def vector_min_max(vectors):
	min = 9.999e99
	max = 0
	for vector in vectors:
		#keep them all squared for the moment
		mod2 = dot(vector,vector)
		if mod2 < min:
			min = mod2
		elif mod2 > max:
			max = mod2
	min = sqrt(min)
	max = sqrt(max)
	return min, max

# check_muon_pos
# --------------------------
# check_muon_pos makes sure that the muon isn't too near a magnetic moment - this is bad firstly because
# such proximity creates explodingly large values for the precession frequency, but also because it is almost
# certainly an unphysical positon for the muon to occupy
# ---
# INPUT
# a = array of three three-component vectors: the primitive translation vectors in cartesian coordinates
# atoms = array of three-component vectors specifying the cartesian coordinates of all atoms in a unit cell
# mu_frac = a three-component vector of the muon's fractional position within the unit cell
# ---
# OUTPUT
# This returns the distance to the nearest atom for the program to panic over if it fancies a panic.
def check_muon_pos(a,atoms,mu_frac):
	nearest_dist_2=float(20) #set it to a monstrously high value which the first one will inevitably be less than (999 better way?)
	for atom in atoms:
		dist_2=float(0)
		for i in range(3):
			dist_2 += (a[i]*(atom[i] - mu_frac[i]))**2
		if dist_2 < nearest_dist_2:
			nearest_dist_2 = dist_2
	return sqrt(nearest_dist_2)

def simplify_crystal(r_in,q_in,mu_in,names_in):
	keep = ones(len(r_in),int)
	for i in range(len(r_in)):
		#if it's really small, then throw it away (999allow user's definition of 'really small' - though this is mostly to discard zeros, there may be insignificant moments in the crystal, too)
		if(dot(mu_in[i],mu_in[i])<((0.001*9.24e-24)**2)):
			keep[i] = 0
	return compress(keep,r_in,axis=0), compress(keep,q_in,axis=0), compress(keep,mu_in,axis=0), compress(keep,names_in,axis=0)

def simplify_crystal_e(r_in,q_in):
	keep = ones(len(r_in),int)
	for i in range(len(r_in)):
		#if it's zero, throw it away (since charge is quantised, no need to have a small cut-off)
		if q_in[i] == 0:
			keep[i] = 0
	return compress(keep,r_in,axis=0), compress(keep,q_in,axis=0)

def gyro(B):
	return gamma_mu*sqrt(dot(B,B))

def calculate_V(r_test, r_crystal, q):
	r = r_crystal - r_test
	#e / 4pi epsilon0 (at the front of the dipole eqn)
	A = 1 #1.6e-19 / (4*3.14159263538979323*8.854188e-12) #http://physics.nist.gov/cgi-bin/cuu/Value?ep0
	V = 0
	for i in range(len(r)):
		if not(r[i][0] == 0 and r[i][1] == 0 and r[i][2] == 0):
			#work out the electric potential and add it to the estimate so far
			V += A*q[i]/sqrt(dot(r[i],r[i]))
			# 1/4pi e0 * q/r (q_mu = +1)
	return V