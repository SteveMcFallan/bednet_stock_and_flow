"""  Script to fit stock-and-flow compartmental model of bednet distribution
"""

from pylab import *
from pymc import *

import copy

def load_csv(fname):
    """ Quick function to load each row of a csv file as a dict
    Parameters
    ----------
    fname : str
      name of the .csv file to load
    
    Results
    -------
    returns a list of dicts, one list item for each row of the csv
    (keyed by the first row)

    Notes
    -----
    every value in the dict will be a string.  remember to convert
    numbers to floats before doing any math with them.
    """
    import csv
    f = open(fname)
    csv_f = csv.DictReader(f)
    data = [d for d in csv_f]
    f.close()

    return data


### load all data from csv files
manufacturing_data = load_csv('manuitns_forabie07072009.csv')
administrative_distribution_data = load_csv('programitns_forabie07072009.csv')
household_stock_data = load_csv('stock_surveyitns_forabie07072009.csv')
household_distribution_data = load_csv('surveyitns_forabie7072009.csv')
retention_data = load_csv('retention07072009.csv')


### pick the country of interest
c = 'Malawi'


### find some descriptive statistics to use as priors
nd_all = [float(d['Program_Itns']) for d in administrative_distribution_data if d['Country'] == c]
nd_min = min(nd_all)
nd_avg = mean(nd_all)
nd_ste = std(nd_all)

nm_all = [float(d['Manu_Itns']) for d in manufacturing_data if d['Country'] == c]
nm_min = min(nm_all)
nm_avg = mean(nm_all)


### setup the model variables
vars = []
   #######################
  ### compartmental model
 ###
#######################

logit_p_l = Normal('logit(Pr[net is lost])', mu=logit(.05), tau=1./.5**2)
p_l = InvLogit('Pr[net is lost]', logit_p_l, verbose=1)

## by commenting out the next line, the MCMC will not try to fit the stoch
vars += [p_l]

# TODO: consider choosing better priors
s_r = Gamma('error in retention rate', 10., 10./.05, value=.05)
s_m = Gamma('error in manufacturing data', 10., 10./.05, value=.05)
s_d = Gamma('error in administrative distribution data', 10., 10./.05, value=.05)

## by commenting out the next line, the MCMC will not try to fit the stoch
vars += [s_r, s_m, s_d]

# TODO: consider choosing better priors
nd = Lognormal('nets distributed', mu=log(nd_avg) * ones(10), tau=1.)
nm = Lognormal('nets manufactured', mu=log(nm_avg) * ones(10), tau=1.)

# TODO: consider choosing better priors
W_0 = Lognormal('initial warehouse net stock', mu=log(1.e5), tau=100., value=1.e5)
H_0 = Lognormal('initial household net stock', mu=log(1.e5), tau=100., value=1.e5)

@deterministic(name='warehouse net stock')
def W(W_0=W_0, nm=nm, nd=nd):
    W = zeros(10)
    W[0] = W_0
    for t in range(9):
        W[t+1] = W[t] + nm[t] - nd[t]
    return W

@deterministic(name='household net stock')
def H(H_0=H_0, nd=nd, p_l=p_l):
    H = zeros(10)
    H[0] = H_0
    for t in range(9):
        H[t+1] = H[t] * (1 - p_l) + nd[t]
    return H

vars += [nd, nm, W_0, H_0, W, H]

# set initial condition on W_0 to have no stockouts
if min(W.value) < 0:
    W_0.value = W_0.value - 2*min(W.value)

   #####################
  ### additional priors
 ###
#####################

@potential
def smooth_W(W=W):
    return normal_like(diff(log(maximum(W,10000))), 0., 1. / (1.)**2)

@potential
def smooth_H(H=H):
    return normal_like(diff(log(maximum(H,10000))), 0., 1. / (.1)**2)

@potential
def positive_stocks(H=H, W=W):
    return -1000 * (dot(H**2, H < 0) + dot(W**2, W < 0))

vars += [smooth_H, smooth_W, positive_stocks]


   #####################
  ### statistical model
 ###
#####################


### observed nets manufactured

manufacturing_obs = []
for d in manufacturing_data:
    if d['Country'] != c:
        continue
    
    @observed
    @stochastic(name='manufactured_%s_%s' % (d['Country'], d['Year']))
    def obs(value=float(d['Manu_Itns']), year=int(d['Year']), nm=nm, s_m=s_m):
        return normal_like(value / nm[year-2000], 1., 1. / s_m**2)
    manufacturing_obs.append(obs)

    # also take this opportinuty to set better initial values for the MCMC
    cur_val = copy.copy(nm.value)
    cur_val[int(d['Year']) - 2000] = float(d['Manu_Itns'])
    nm.value = cur_val

vars += [manufacturing_obs]



### observed nets distributed

admin_distribution_obs = []
for d in administrative_distribution_data:
    if d['Country'] != c:
        continue

    @observed
    @stochastic(name='administrative_distribution_%s_%s' % (d['Country'], d['Year']))
    def obs(value=float(d['Program_Itns']), year=int(d['Year']), nd=nd, s_d=s_d):
        return normal_like(value / nd[year-2000], 1., 1. / s_d**2)
    admin_distribution_obs.append(obs)

    # also take this opportinuty to set better initial values for the MCMC
    cur_val = copy.copy(nd.value)
    cur_val[int(d['Year']) - 2000] = float(d['Program_Itns'])
    nd.value = cur_val

vars += [admin_distribution_obs]


household_distribution_obs = []
for d in household_distribution_data:
    if d['Name'] != c:
        continue

    d2_i = float(d['Survey_Itns'])
    estimate_year = int(d['Year'])
    survey_year = int(d['Survey_Year'])
    s_d2_i = float(d['Ste_Survey_Itns'])
    @observed
    @stochastic(name='household_distribution_%s_%s' % (d['Name'], d['Year']))
    def obs(value=d2_i,
            estimate_year=estimate_year,
            survey_year=survey_year,
            survey_err=s_d2_i,
            retention_err=s_r,
            nd=nd, p_l=p_l):
        return normal_like(
            value,
            nd[estimate_year - 2000] * (1 - p_l) ** (survey_year - estimate_year),
            1./ (survey_err**2 + ((survey_year - estimate_year) * retention_err)**2))
    household_distribution_obs.append(obs)

    # also take this opportinuty to set better initial values for the MCMC
    cur_val = copy.copy(nd.value)
    cur_val[estimate_year - 2000] = d2_i / (1 - p_l.value)**(survey_year - estimate_year)
    nd.value = cur_val

vars += [household_distribution_obs]



### observed household net stocks
household_stock_obs = []
for d in household_stock_data:
    if d['Name'] != c:
        continue

    @observed
    @stochastic(name='household_stock_%s_%s' % (d['Name'], d['Year']))
    def obs(value=float(d['Survey_Itns']),
            year=int(d['Year']),
            std_err=float(d['Ste_Survey_Itns']),
            H=H):
        return normal_like(value, H[year-2000], 1. / std_err ** 2)
    household_stock_obs.append(obs)

vars += [household_stock_obs]


### observed net retention 

retention_obs = []
for d in retention_data:
    @observed
    @stochastic(name='retention_%s_%s' % (d['Name'], d['Year']))
    def obs(value=float(d['Retention_Rate']),
            T_i=float(d['Follow_up_Time']),
            p_l=p_l, s_r=s_r):
        return normal_like(value, (1. - p_l) ** T_i, 1. / s_r**2)
    retention_obs.append(obs)

vars += [retention_obs]



   #################
  ### fit the model
 ###
#################
print 'running fit for net model in %s...' % c

method = 'MCMC'
#method = 'NormApprox'

if method == 'MCMC':
    map = MAP(vars)
    map.fit(method='fmin_powell', verbose=1)
    for stoch in [s_m, s_d, s_r, p_l]:
        print '%s: %f' % (stoch, stoch.value)

    mc = MCMC(vars, verbose=1)
    #mc.use_step_method(AdaptiveMetropolis, [nd, nm, W_0, H_0], verbose=0)
    #mc.use_step_method(AdaptiveMetropolis, nd, verbose=0)
    #mc.use_step_method(AdaptiveMetropolis, nm, verbose=0)

    try:
        mc.sample(10000, 5000, 100)
    except:
        pass

elif method == 'NormApprox':
    na = NormApprox(vars)
    na.fit(method='fmin_powell', tol=.00001, verbose=1)
    for stoch in [s_m, s_d, s_r, p_l]:
        print '%s: %f' % (stoch, stoch.value)
    na.sample(1000)


   ######################
  ### plot the model fit
 ###
######################
def plot_fit(f, scale=1.e6):
    plot(range(2000,2010), f.stats()['mean']/scale, 'k-', alpha=1., label='Est Mean')
    #plot(range(2000,2010), f.stats()['quantiles'][2.5]/scale, 'k:', alpha=.95, label='Est 95% UI')
    #plot(range(2000,2010), f.stats()['quantiles'][97.5]/scale, 'k:', alpha=.95)
    x = np.concatenate((arange(2000,2010), arange(2000,2010)[::-1]))
    y = np.concatenate((f.stats()['quantiles'][2.5]/scale,
                        f.stats()['quantiles'][97.5][::-1]/scale))
    fill(x, y, alpha=.95, label='Est 95% UI', facecolor=.8)

def scatter_data(data_list, country, country_key, data_key,
                 error_key=None, error_val=None, fmt='go', scale=1.e6, p_l=None, label=''):

    if p_l == None:
        data_val = array([float(d[data_key]) for d in data_list if d[country_key] == c])
    else:
        # account for the nets lost prior to survey
        data_val = array([
                float(d[data_key]) / (1-p_l)**(int(d['Survey_Year']) - int(d['Year']))
                for d in data_list if d[country_key] == c])

    if error_key:
        error_val = array([1.96*float(d[error_key]) \
                               for d in data_list if d[country_key] == c])
    elif error_val:
        error_val = 1.96 * error_val * data_val
    errorbar([float(d['Year']) for d in data_list if d[country_key] == c],
             data_val/scale,
             error_val/scale, fmt=fmt, alpha=.95, label=label)
        

def decorate_figure():
    l,r,b,t = axis()
    vlines(range(2000,2010), 0, t, color=(0,0,0), alpha=.3)
    axis([2000,2009,0,t])
    xticks([2000, 2004, 2008], ['2000', '2004', '2008'])

def my_hist(stoch):
    hist(stoch.trace(), normed=True, log=False)
    l,r,b,t = axis()
    vlines(stoch.stats()['quantiles'].values(), b, t,
           linewidth=2, alpha=.75, linestyle='dashed',
           color=['k', 'k', 'r', 'k', 'k'])
    yticks([])

def my_acorr(stoch):
    vals = copy.copy(stoch.trace())

    if shape(vals)[-1] == 1:
        vals = ravel(vals)
    
    if len(shape(vals)) > 1:
        vals = vals[5]

    vals -= mean(vals)
    acorr(vals, normed=True, maxlags=min(8, len(vals)))
    hlines([0],-8,8, linewidth=2, alpha=.7, linestyle='dotted')
    xticks([])
    yticks([0,1], fontsize=6)
    
clf()

cols = 4

for ii, stoch in enumerate([p_l, s_r, s_m, s_d, nm, nd, W, H]):
    subplot(8, cols*2, 2*cols - 1 + ii*2*cols)
    try:
        plot(stoch.trace(), linewidth=2, alpha=.5)
    except Exception, e:
        print 'Error: ', e

    xticks([])
    yticks([])
    title(str(stoch), fontsize=6)
        
    subplot(8, cols*2, 2*cols + ii*2*cols)
    try:
        my_acorr(stoch)
    except Exception, e:
        print 'Error: ', e


subplot(4, cols/2, 1)
title('nets manufactured', fontsize=8)
plot_fit(nm)
try:
    scatter_data(manufacturing_data, c, 'Country', 'Manu_Itns',
                 error_val=1.96 * s_m.stats()['quantiles'][97.5])
except Exception, e:
    print 'Error: ', e
    scatter_data(manufacturing_data, c, 'Country', 'Manu_Itns',
                 error_val=1.96 * s_m.value)
decorate_figure()


subplot(4, cols/2, 2*(cols/2)+1)
title('nets distributed', fontsize=8)
plot_fit(nd)

label = 'Administrative Data'
try:
    scatter_data(administrative_distribution_data, c, 'Country', 'Program_Itns',
                 error_val=1.96 * s_d.stats()['quantiles'][97.5], label=label)
except Exception, e:
    print 'Error: ', e
    scatter_data(administrative_distribution_data, c, 'Country', 'Program_Itns',
                 error_val=1.96 * s_m.value, label=label)

label = 'Survey Data'
try:
    scatter_data(household_distribution_data, c, 'Name', 'Survey_Itns',
                 error_key='Ste_Survey_Itns', fmt='bs', p_l=p_l.stats()['mean'][0], label=label)
except Exception, e:
    print 'Error: ', e
    scatter_data(household_distribution_data, c, 'Name', 'Survey_Itns',
                 error_key='Ste_Survey_Itns', fmt='bs', p_l=p_l.value, label=label)
decorate_figure()
legend(loc='upper left')


subplot(4, cols/2, (cols/2)+1)
title('nets in warehouse', fontsize=8)
plot_fit(W)
decorate_figure()


subplot(4, cols/2, 3*(cols/2)+1)
title('nets in households', fontsize=8)
plot_fit(H)
scatter_data(household_stock_data, c, 'Name', 'Survey_Itns',
             error_key='Ste_Survey_Itns', fmt='bs')
decorate_figure()


try:
    subplot(2,cols,3)
    title(str(p_l), fontsize=8)
    my_hist(p_l)
except Exception, e:
    print 'Error: ', e

for ii, stoch in enumerate([s_r, s_m, s_d]):
    try:
        subplot(7, cols, (4 + ii)*cols + 3)
        my_hist(stoch)
        title(str(stoch), fontsize=8)
    except Exception, e:
        print 'Error: ', e
