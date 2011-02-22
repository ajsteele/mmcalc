# The width of the console in text columns
console_width = 80

# If you are having problems which throw up errors like
#   UnicodeEncodeError: 'ascii' codec can't encode character u'\xc5' in position 44: ordinal not in range(128)
# set this to False
unicode = True

# Verbose or terse output. In a few places, setting this to true will provide additional mildly interesting information...though not many places at present.
verbose = True

# This is the number of points randomly generated in one go as a compromise between generating as many as possible in a highly-optimised NumPy loop, and crashing the computer by using too much RAM by generating too many points simultaneously.
# 10,000,000 seemed to result in near-crashing pagefile usage, and, if a second calculation was attempted with the same instance of MmCalc, the program would crash with a MemoryError. (On a quad-core Pentium with 2 GiB RAM.)
n_pos_at_a_time = 1000000

# Directories
current_dir = 'current' #for session files
output_dir = 'output' #for output files