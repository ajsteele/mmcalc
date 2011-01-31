# ==startup== #
err_numpy = "Error importing Numeric Python module. Please make sure the module 'numpy' is installed. See http://numpy.scipy.org/"
err_json = "Error importing JSON module. If you are using Python < 2.6, install the module 'simplejson' and try again. Python 2.6+ and 3.0+ should include the 'json' module as standard."

# ==title bar== #
muon = '[µ]'
programname = 'MµCalc'
url = 'andrewsteele.co.uk/mmcalc'
version = 'v1.0'

# ==menus== #
chooseoption = 'Please choose an option by pressing the letter'
# main menu #

# dipole menu #
# convergence testing
conv_vcrystal_radius = 'radius'
conv_error = 'error'
conv_time_estimate = 'time for 1,000,000 points'
conv_n_points = 1e6 #the number of points stipulated above which will be used to give the estimate of time taken to perform a dipole field calculation

# ==waiting== #
#generic
please_wait = 'Please wait...'
#waiting for drawing
drawing_crystal_unit_cell = 'Drawing crystallogaphic unit cell...'
drawing_constrained_positions = 'Drawing positions which satisfy constraints...'

# ==errors== #
err_no_length_unit = 'You have not specified a length unit. Please go to the crystal menu and specify one to continue.'

# ==general== #
nm = 'nm'
m = 'm'
angstrom = 'Å'
degree = '°'

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
if platform.system() == 'Windows':
	#paraphrase unicode issues
	
	# ==title bar== #
	muon = "[mu]"
	programname = "MmCalc"
	
	# ==general== #
	angstrom = 'angstroms'
	degree = ' degrees' #starts with a space because degree sign goes directly adjacent to value
	
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