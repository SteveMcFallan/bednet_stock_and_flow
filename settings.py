""" Settings for the bednet stock and flow model"""

# PATH is important for running on the cluster; all paths should end with a '/'
PATH = './'  # use current directory
CSV_NAME = 'output.csv'

# set TESTING to True to speed up all calculations (and make them much less accurate)
TESTING = False

# Use 3000 samples for final uncertainty estimates;  50 will be enough for refining model/priors
#NUM_SAMPLES = 50
NUM_SAMPLES = 3000
THIN = 1000
BURN = 250000
#METHOD = 'NormApprox'
METHOD = 'MCMC'

# global model parameters
year_start = 1999
year_end = 2011

# matplotlib backend setup
import matplotlib
matplotlib.use("AGG") 

# windows and linux have different ideas about how to interpret this
DPI=300
#FIGURE_OPTIONS = dict(figsize=(88, 68), dpi=75) # windows looks good
FIGURE_OPTIONS = dict(figsize=(11*1.75, 8.5*1.75), dpi=DPI) # linux

try:
    from local_settings import *
except:
    pass
