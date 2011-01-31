#title bar stuff
muon = "[µ]"
programname = "MµCalc"
url = "andrewsteele.co.uk/mmcalc"
version = "v1.0"

angstrom = 'Å'
degree = '°'

chooseoption = 'Please choose an option by pressing the letter'

bold = "\033[1m"
underline = "\033[4m"

red = "\033[31m"
grey = "\033[90m"
gold = "\033[33m"

bgblack = "\033[40m"

reset = "\033[30;0m"

newline = "\n"


#the system command for clearing the screen
clearcommand = 'clear'

# a few changes are necessary because Windows command prompt doesn't support UTF-8 text or ANSI text formatting commands
import platform
if platform.system() == 'Windows':
	#paraphrase unicode issues
	muon = "[mu]"
	programname = "MmCalc"
	
	angstrom = 'angstroms'
	degree = ' degrees' #must start with a space because degree sign goes directly adjacent to value
	
	#discard ANSI formating commands
	bold = ''
	underline = ''

	red = ''
	grey = ''
	gold = ''

	bgblack = ''

	reset = ''
	
	newline = "\r\n"
	#the system command for clearing the screen
	clearcommand = 'cls'