""" Settings for the bednet stock and flow model"""

# PATH is important for running on the cluster; all paths should end with a '/'
# PATH = './'  # use current directory
PATH = '/net/gs/vol1/home/abie/bednet_stock_and_flow/'
CSV_NAME = 'bednets.csv'

# set TESTING to True to speed up all calculations (and make them much less accurate)
TESTING = False

# matplotlib backend setup
import matplotlib
matplotlib.use("AGG") 

# windows and linux have different ideas about how to interpret this
# FIGURE_OPTIONS = dict(figsize=(88, 68), dpi=75) # windows looks good
FIGURE_OPTIONS = dict(figsize=(11*1.75, 8.5*1.75), dpi=300) # linux
