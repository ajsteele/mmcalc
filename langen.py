# ==special characters== #
alpha = 'α'
angstrom = 'Å'
beta = 'β'
degree = '°'
ellipsis_short = '…'
ellipsis = '...'
gamma = 'γ'
infinity = '∞'
mu = 'µ' #mu = 'mu' in non-unicode
mu2 = 'µ' #mu2 ='m' in non-unicode
pi = 'π'
x = 'x' # cartesian directions
y = 'y'
z = 'z'
empty = '-'

# ==formatting== #
# (this isn't really internationalisation)
bold = "\033[1m"
underline = "\033[4m"

red = "\033[31m"
grey = "\033[90m"
gold = "\033[33m"

bgblack = "\033[40m"

reset = "\033[30;0m"

newline = '\n' #Unix newline

clearcommand = 'clear' #system command to clear the console

# ==Windows== #
# (a few changes are necessary because Windows command prompt doesn't support UTF-8 text or ANSI text formatting commands)
import platform
import config
if platform.system() == 'Windows' or config.unicode == False:
	# ==special characters== #
	# (paraphrase unicode issues)
	alpha = 'alpha'
	angstrom = 'angstroms'
	beta = 'beta'
	degree = ' degrees' #starts with a space because degree sign goes directly adjacent to value
	ellipsis_short = '...'
	gamma = 'gamma'
	infinity = 'infinity'
	mu = 'mu'
	mu2 = 'm'
	pi = 'pi'
	
	# ==formatting== #
	# (discard ANSI formatting commands)
	bold = ''
	underline = ''
	
	red = ''
	grey = ''
	gold = ''
	
	bgblack = ''
	
	reset = ''
	
	newline = '\r\n' #Windows CR/LF newline
	clearcommand = 'cls' #system command to clear the console

# ==startup== #
err_numpy = "Error importing Numeric Python module. Please make sure the module 'numpy' is installed. See http://numpy.scipy.org/"
err_json = "Error importing JSON module. If you are using Python < 2.6, install the module 'simplejson' and try again. Python 2.6+ and 3.0+ should include the 'json' module as standard."

# ==general== #
nm = 'nm'
m = 'm'
# input #
blankfor = 'blank for '

# ==title bar== #
muon = '['+mu+']'
programname = 'M'+mu2+'Calc'
url = 'andrewsteele.co.uk/mmcalc'
version = 'v1.1'

# ==menus== #
chooseoption = 'Please choose an option by pressing the letter'
chooseoption_with_enter = 'Please press a letter followed by enter'
# main menu #

# crystal menu #
# magnetic properties
m_vector_input_1 = '  m_' #998 remove preceding spaces in the long run, add them in the ui function
m_vector_input_2 = ' (units of '+mu+'_B, complex'
m_vector_input_2b = ', '
m_vector_input_3 = '):'#998 remove colons in the long run, add them in the ui function
add_mx = m_vector_input_1+x+m_vector_input_2+m_vector_input_3
add_my = m_vector_input_1+y+m_vector_input_2+m_vector_input_3
add_mz = m_vector_input_1+z+m_vector_input_2+m_vector_input_3
edit_mx_1 = m_vector_input_1+x+m_vector_input_2+m_vector_input_2b+blankfor
edit_my_1 = m_vector_input_1+y+m_vector_input_2+m_vector_input_2b+blankfor
edit_mz_1 = m_vector_input_1+z+m_vector_input_2+m_vector_input_2b+blankfor
edit_m_2 = m_vector_input_3

k_vector_input_1 = '    k_' #998 remove preceding spaces in the long run, add them in the ui function
k_vector_input_2 = '/2'+pi+' (complex'
k_vector_input_2b = ', '
k_vector_input_3 = '):'#998 remove colons in the long run, add them in the ui function
add_kx = k_vector_input_1+x+k_vector_input_2+k_vector_input_3
add_kx = k_vector_input_1+y+k_vector_input_2+k_vector_input_3
add_kx = k_vector_input_1+z+k_vector_input_2+k_vector_input_3
edit_kx_1 = k_vector_input_1+x+k_vector_input_2+k_vector_input_2b+blankfor
edit_ky_1 = k_vector_input_1+y+k_vector_input_2+k_vector_input_2b+blankfor
edit_kz_1 = k_vector_input_1+z+k_vector_input_2+k_vector_input_2b+blankfor
edit_k_2 = k_vector_input_3

# dipole menu #
# convergence testing
conv_vcrystal_radius = 'radius'
conv_error = 'error'
conv_time_estimate = 'time for 1,000,000 points'
conv_n_points = 1e6 #the number of points stipulated above which will be used to give the estimate of time taken to perform a dipole field calculation

# ==waiting== #
# generic
please_wait = 'Please wait'+ellipsis
# waiting for drawing
drawing_crystal_unit_cell = 'Drawing crystallogaphic unit cell'+ellipsis
drawing_constrained_positions = 'Drawing positions which satisfy constraints'+ellipsis

# ==errors== #
err = red+'ERROR: '+reset
err_no_length_unit = 'You have not specified a length unit. Please go to the crystal menu and specify one to continue.'
err_constraints_too_harsh = 'Your constraints are too harsh: no points satisfy them!'

# ==exit== #
goodbye = 'Thanks for using M'+mu2+'Calc!'