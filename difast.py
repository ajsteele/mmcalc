# Many thanks to the StackOverflow community, who pointed out how to optimise this in NumPy and make it run about 100x faster!
# http://stackoverflow.com/questions/2586749/what-is-the-most-platform-and-python-version-independent-way-to-make-a-fast-loop
import numpy as np

def reshape_array(a):
	b = np.empty((3,len(a)))
	for i in range(len(a)):
		for j in range(3):
			b[j][i] = a[i][j]
	return b

def reshape_vector(v):
	b = np.empty((3,1))
	for i in range(3):
		b[i][0] = v[i]
	return b

def unit_vectors(r):
	 return r / np.sqrt((r*r).sum(0))

def calculate_dipole(mu, r_i, mom_i):
	relative = mu - r_i
	r_unit = unit_vectors(relative)
	A = 1e-7

	num = A*(3*np.sum(mom_i*r_unit, 0)*r_unit - mom_i)
	den = np.sqrt(np.sum(relative*relative, 0))**3
	B = np.sum(num/den, 1)
	return B