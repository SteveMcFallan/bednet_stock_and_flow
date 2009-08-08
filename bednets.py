"""  Script to fit stock-and-flow compartmental model of bednet distribution
"""

from pylab import *
from pymc import *

import copy
import time

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
administrative_distribution_data = load_csv('total_admllins_forabie06082009.csv')
household_stock_data = load_csv('stock_surveyitns_07082009.csv')
household_distribution_data = load_csv('updated_total_svyllins_forabie06082009.csv')
retention_data = load_csv('retention07072009.csv')


### find parameters for simple model to predict administrative
### distribution data from household distribution data
data_dict = {}
for d in administrative_distribution_data:
    key = (d['Country'], d['Year'])
    if not data_dict.has_key(key):
        data_dict[key] = {}
    data_dict[key]['admin'] = float(d['Program_Llns'])
for d in household_distribution_data:
    key = (d['Country'], d['Year'])
    if not data_dict.has_key(key):
        data_dict[key] = {}
    data_dict[key]['survey'] = float(d['Total_LLINs'])
    data_dict[key]['time'] =  float(d['Survey_Year2'])-float(d['Year'])
    data_dict[key]['survey_ste'] = float(d['Total_st'])
for key in data_dict.keys():
    if len(data_dict[key]) != 4:
        data_dict.pop(key)

x = array([data_dict[k]['admin'] for k in sorted(data_dict.keys())])
y = array([data_dict[k]['survey'] for k in sorted(data_dict.keys())])
y_e = array([data_dict[k]['survey_ste'] for k in sorted(data_dict.keys())])


prior_s_d = Gamma('prior on sampling error in admin dist data', 1., 1./.05, value=.05)
prior_e_d = Normal('prior on sys error in admin dist data', 0., 1./.5**2, value=0.)
prior_vars = [prior_s_d, prior_e_d]

for k in data_dict:
    @observed
    @stochastic
    def net_distribution_data(value=data_dict[k]['admin'], survey_value=data_dict[k]['survey'],
                          s_d=prior_s_d, e_d=prior_e_d):
        return normal_like(log(value), e_d + log(survey_value), 1. / s_d**2)
    prior_vars.append(net_distribution_data)

mc = MCMC(prior_vars, verbose=1)
mc.use_step_method(AdaptiveMetropolis, [prior_s_d, prior_e_d])
iter = 1000
thin = 25
burn = 20000

# say "if True:" to skip the empirical prior computation, for testing
if False:
    iter = 100
    thin = 1
    burn = 0

mc.sample(iter*thin+burn, burn, thin)

print str(prior_s_d), prior_s_d.stats()
print str(prior_e_d), prior_e_d.stats()

mean_e_d = prior_e_d.stats()['mean']

y_predicted = exp(arange(log(1000), 16, .1))
x_predicted = (1 + mean_e_d) * y_predicted
x_predicted = maximum(10, x_predicted)

### setup the canvas for our plots
figure(figsize=(88, 68), dpi=75)

clf()
subplot(1,2,1)
errorbar(x, y, 1.96*y_e, fmt=',', alpha=.9, linewidth=1.5)
plot(x_predicted, y_predicted, 'r:', alpha=.75, linewidth=2, label='predicted value')
#loglog([1000,exp(16)],[1000,exp(16)], 'k--', alpha=.5, linewidth=2, label='y=x')

y = np.concatenate((y_predicted, y_predicted[::-1]))
x = np.concatenate(((1 + mean_e_d - 1.96*prior_e_d.stats()['standard deviation']) * y_predicted,
                   ((1 + mean_e_d + 1.96*prior_e_d.stats()['standard deviation']) * y_predicted)[::-1]))
x = maximum(10, x)
fill(x, y, alpha=.95, label='Sys Err 95% UI', facecolor=(.8,.4,.4), alpha=.5)

x = np.concatenate(((1 + mean_e_d - 1.96*prior_e_d.stats()['standard deviation']) * y_predicted * (1 - 1.96*prior_s_d.stats()['mean']),
                   ((1 + mean_e_d + 1.96*prior_e_d.stats()['standard deviation']) * y_predicted * (1 + 1.96*prior_s_d.stats()['mean']))[::-1]))
x = maximum(10, x)
fill(x, y, alpha=.95, label='Total Err 95% UI', facecolor='.8', alpha=.5)

axis([1000,exp(16),1000,exp(16)])
legend()
ylabel('Nets distributed according to household survey')
xlabel('Nets distributed according to administrative data')
for k in data_dict:
    d = data_dict[k]
    text(d['admin'], d['survey'], ' %s, %s' % k, fontsize=8, alpha=.7, verticalalignment='center')

subplot(2,4,3)
hist(prior_e_d.trace(), normed=True, log=False)
l,r,b,t = axis()
vlines(ravel(prior_e_d.stats()['quantiles'].values()), b, t,
       linewidth=2, alpha=.75, linestyle='dashed',
       color=['k', 'k', 'r', 'k', 'k'])
yticks([])
title(str(prior_e_d), fontsize=8)

subplot(2,4,4)
hist(prior_s_d.trace(), normed=True, log=False)
l,r,b,t = axis()
vlines(ravel(prior_s_d.stats()['quantiles'].values()), b, t,
       linewidth=2, alpha=.75, linestyle='dashed',
       color=['k', 'k', 'r', 'k', 'k'])
yticks([])
title(str(prior_s_d), fontsize=8)

subplot(2,4,7)
plot(prior_e_d.trace())
plot(prior_s_d.trace())
legend()
title('MCMC trace')

subplot(2,4,8)
acorr(prior_e_d.trace() - mean(prior_e_d.trace()), maxlags=10, normed=True)
acorr(prior_s_d.trace() - mean(prior_s_d.trace()), maxlags=10, normed=True)
legend()
title('MCMC autocorrelation')
axis([-10,10,-.2,1.2])
yticks([0,1])

savefig('bednets_Priors_%s.png' % time.strftime('%Y_%m_%d_%H_%M'))

### pick the country of interest
country_set = set([d['Country'] for d in manufacturing_data])
print 'fitting models for %d countries...' % len(country_set)

### set years for estimation
year_start = 1999
year_end = 2010

for c in sorted(country_set):
    ### find some descriptive statistics to use as priors
    nd_all = [float(d['Program_Llns']) for d in administrative_distribution_data \
                  if d['Country'] == c] \
                  + [float(d['Survey_Itns']) for d in household_distribution_data \
                         if d['Country'] == c and d['Year'] == d['Survey_Year2']]
    # if there is no distribution data, make some up
    if len(nd_all) == 0:
        nd_all = [ 1000. ]

    nd_min = min(nd_all)
    nd_avg = mean(nd_all)
    nd_ste = std(nd_all)

    nm_all = [float(d['Manu_Itns']) for d in manufacturing_data if d['Country'] == c]
    # if there is no manufacturing data, make some up
    if len(nm_all) == 0:
        nm_all = [ 1000. ]
    nm_min = min(nm_all)
    nm_avg = mean(nm_all)


    ### setup the model variables
    vars = []
       #######################
      ### compartmental model
     ###
    #######################

    logit_p_l = Normal('logit(Pr[net is lost])', mu=logit(.05), tau=1.)
    p_l = InvLogit('Pr[net is lost]', logit_p_l)

    vars += [logit_p_l, p_l]

    
    s_r = Gamma('error in retention data', 20., 20./.15, value=.15)
    s_m = Gamma('error in manufacturing data', 20., 20./.05, value=.05)
    s_d = Normal('sampling error in admin dist data', prior_s_d.stats()['mean'], prior_s_d.stats()['standard deviation']**-2, value=.05)
    e_d = Normal('sys error in admin dist data', prior_e_d.stats()['mean'], prior_e_d.stats()['standard deviation']**-2, value=.05)

    vars += [s_r, s_m, s_d, e_d]

    
    nd = Lognormal('nets distributed', mu=log(nd_min) * ones(year_end-year_start-1), tau=1.)
    nm = Lognormal('nets manufactured', mu=log(nm_min) * ones(year_end-year_start-1), tau=1.)

    W_0 = Lognormal('initial warehouse net stock', mu=log(1000), tau=10., value=1000)
    H_0 = Lognormal('initial household net stock', mu=log(1000), tau=10., value=1000)

    @deterministic(name='warehouse net stock')
    def W(W_0=W_0, nm=nm, nd=nd):
        W = zeros(year_end-year_start)
        W[0] = W_0
        for t in range(year_end - year_start - 1):
            W[t+1] = W[t] + nm[t] - nd[t]
        return W

    @deterministic(name='distribution waiting time')
    def T(W=W, nd=nd, nm=nm):
        T = zeros(year_end - year_start - 3)
        for t in range(year_end - year_start - 3):
            T[t] = sum(maximum(0, nm[t] - maximum(0, cumsum(nd[t:]) - W[t]))[1:]) / nm[t]
        return T

    @deterministic(name='1-year-old household net stock')
    def H1(H_0=H_0, nd=nd):
        H1 = zeros(year_end-year_start)
        H1[0] = H_0/3.
        for t in range(year_end - year_start - 1):
            H1[t+1] = nd[t]
        return H1

    @deterministic(name='2-year-old household net stock')
    def H2(H_0=H_0, H1=H1, p_l=p_l):
        H2 = zeros(year_end-year_start)
        H2[0] = H_0/3.
        for t in range(year_end - year_start - 1):
            H2[t+1] = H1[t] * (1 - p_l)
        return H2

    @deterministic(name='3-year-old household net stock')
    def H3(H_0=H_0, H2=H2, p_l=p_l):
        H3 = zeros(year_end-year_start)
        H3[0] = H_0/3.
        for t in range(year_end - year_start - 1):
            H3[t+1] = H2[t] * (1 - p_l)
        return H3

    @deterministic(name='household net stock')
    def H(H1=H1, H2=H2, H3=H3):
        return H1 + H2 + H3

    vars += [nd, nm, W_0, H_0, W, T, H, H1, H2, H3]

    
    # set initial condition on W_0 to have no stockouts
    if min(W.value) < 0:
        W_0.value = W_0.value - 2*min(W.value)

       #####################
      ### additional priors
     ###
    #####################

    @potential
    def smooth_W(W=W):
        return normal_like(diff(log(maximum(W,1))), 0., 1. / (1.)**2)

    @potential
    def smooth_H(H=H):
        return normal_like(diff(log(maximum(H,1))), 0., 1. / (1.)**2)

    @potential
    def T_near_1(T=T):
        return normal_like(T, ones(shape(T)), 1. / (1.)**2)

    @potential
    def positive_stocks(H=H, W=W):
        return -1000 * (dot(H**2, H < 0) + dot(W**2, W < 0))

    vars += [smooth_H, smooth_W, positive_stocks, T_near_1]


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
            return normal_like(log(value),  log(nm[year - year_start]), 1. / s_m**2)
        manufacturing_obs.append(obs)

        # also take this opportinuty to set better initial values for the MCMC
        cur_val = copy.copy(nm.value)
        cur_val[int(d['Year']) - year_start] = float(d['Manu_Itns'])
        nm.value = cur_val

    vars += [manufacturing_obs]



    ### observed nets distributed

    admin_distribution_obs = []
    for d in administrative_distribution_data:
        if d['Country'] != c:
            continue

        @observed
        @stochastic(name='administrative_distribution_%s_%s' % (d['Country'], d['Year']))
        def obs(value=float(d['Program_Llns']), year=int(d['Year']),
                nd=nd, s_d=s_d, e_d=e_d):
            return normal_like(log(value), e_d + log(nd[year - year_start]), 1. / s_d**2)
        admin_distribution_obs.append(obs)

        # also take this opportinuty to set better initial values for the MCMC
        cur_val = copy.copy(nd.value)
        cur_val[int(d['Year']) - year_start] = float(d['Program_Llns'])
        nd.value = cur_val

    vars += [admin_distribution_obs]


    household_distribution_obs = []
    for d in household_distribution_data:
        if d['Country'] != c:
            continue

        d2_i = float(d['Total_LLINs'])
        estimate_year = int(d['Year'])
        survey_year = int(d['Survey_Year2'])
        s_d2_i = float(d['Total_st'])
        @observed
        @stochastic(name='household_distribution_%s_%s' % (d['Country'], d['Year']))
        def obs(value=d2_i,
                estimate_year=estimate_year,
                survey_year=survey_year,
                survey_err=s_d2_i,
                retention_err=s_r,
                nd=nd, p_l=p_l):
            return normal_like(
                value,
                nd[estimate_year - year_start] * (1 - p_l) ** (survey_year - estimate_year - .5),
                1./ survey_err**2)
        household_distribution_obs.append(obs)

        # also take this opportinuty to set better initial values for the MCMC
        cur_val = copy.copy(nd.value)
        cur_val[estimate_year - year_start] = d2_i / (1 - p_l.value)**(survey_year - estimate_year - .5)
        nd.value = cur_val

    vars += [household_distribution_obs]



    ### observed household net stocks
    household_stock_obs = []
    for d in household_stock_data:
        if d['Country'] != c:
            continue

        @observed
        @stochastic(name='household_stock_%s_%s' % (d['Country'], d['Survey_Year2']))
        def obs(value=float(d['SvyIndex_LLINstotal']),
                year=int(d['Survey_Year2']),
                std_err=float(d['SvyIndex_st']),
                H=H):
            return normal_like(value, H[year-year_start], 1. / std_err ** 2)
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
        for stoch in [s_r, s_m, s_d, e_d, p_l, T]:
            print '%s: %s' % (str(stoch), str(stoch.value))

        mc = MCMC(vars, verbose=1)
        mc.use_step_method(AdaptiveMetropolis, [nd, nm, p_l, s_r], verbose=0)
        #mc.use_step_method(AdaptiveMetropolis, nd, verbose=0)
        #mc.use_step_method(AdaptiveMetropolis, nm, verbose=0)

        try:
            iter = 1000
            thin = 200
            burn = 20000
            mc.sample(iter*thin+burn, burn, thin)
        except:
            pass

    elif method == 'NormApprox':
        na = NormApprox(vars)
        na.fit(method='fmin_powell', tol=.00001, verbose=1)
        for stoch in [s_r, s_m, s_d, e_d, p_l]:
            print '%s: %s' % (str(stoch), str(stoch.value))
        na.sample(1000)


       ######################
      ### plot the model fit
     ###
    ######################
    fontsize = 12
    small_fontsize = 10
    tiny_fontsize = 7

    def plot_fit(f, scale=1.e6):
        """ Plot the posterior mean and 95% UI
        """
        plot(year_start + arange(len(f.value)),
             f.stats()['mean']/scale, 'k-', linewidth=2, label='Est Mean')

        x = np.concatenate((year_start + arange(len(f.value)),
                            year_start + arange(len(f.value))[::-1]))
        y = np.concatenate((f.stats()['quantiles'][2.5]/scale,
                            f.stats()['quantiles'][97.5][::-1]/scale))
        fill(x, y, alpha=.95, label='Est 95% UI', facecolor='.8', alpha=.5)

    def scatter_data(data_list, country, country_key, data_key,
                     error_key=None, error_val=None,  p_l=None, s_r=None,
                     fmt='go', scale=1.e6, label=''):
        """ This convenience function is a little bit of a mess, but it
        avoids duplicating code for scatter-plotting various types of
        data, with various types of error bars
        """

        data_val = array([float(d[data_key]) for d in data_list if d[country_key] == c])
        #if p_l == None:
        #    data_val = array([float(d[data_key]) for d in data_list if d[country_key] == c])
        #else:
        #    # account for the nets lost prior to survey
        #    data_val = array([
        #            float(d[data_key]) / (1-p_l)**(int(d['Survey_Year']) - int(d['Year']) - .5)
        #            for d in data_list if d[country_key] == c])

        if error_key:
            error_val = array([1.96*float(d[error_key]) \
                                   for d in data_list if d[country_key] == c])
            #if s_r == None:
            #    error_val = array([1.96*float(d[error_key]) \
            #                           for d in data_list if d[country_key] == c])
            #else:
            #    error_val = array([1.96*float(d[error_key])
            #                       * (1 + (int(d['Survey_Year']) - int(d['Year'])) * s_r) \
            #                           for d in data_list if d[country_key] == c])

        elif error_val:
            error_val = 1.96 * error_val * data_val
        errorbar([float(d['Year']) for d in data_list if d[country_key] == c],
                 data_val/scale,
                 error_val/scale, fmt=fmt, alpha=.95, label=label)


    def decorate_figure(ystr='# of Nets (Millions)'):
        """ Set the axis, etc."""
        l,r,b,t = axis()
        vlines(range(year_start,year_end), 0, t, color=(0,0,0), alpha=.3)
        axis([year_start, year_end-1, 0, t])
        ylabel(ystr, fontsize=fontsize)
        xticks([2001, 2003, 2005, 2007], ['2001', '2003', '2005', '2007'], fontsize=fontsize)

    def my_hist(stoch):
        """ Plot a histogram of the posterior distribution of a stoch"""
        hist(stoch.trace(), normed=True, log=False)
        l,r,b,t = axis()
        vlines(ravel(stoch.stats()['quantiles'].values()), b, t,
               linewidth=2, alpha=.75, linestyle='dashed',
               color=['k', 'k', 'r', 'k', 'k'])
        yticks([])

        if str(stoch).find('distribution waiting time') == -1:
            a,l = xticks()
            l = [int(floor(x*100.)) for x in a]
            l[0] = str(l[0]) + '%'
            xticks(floor(array(a)*100.)/100., l, fontsize=small_fontsize)
        title(str(stoch), fontsize=small_fontsize)
        ylabel('probability density')
        

    def my_acorr(stoch):
        """ Plot the autocorrelation of the a stoch trace"""
        vals = copy.copy(stoch.trace())

        if shape(vals)[-1] == 1:
            vals = ravel(vals)

        if len(shape(vals)) > 1:
            vals = vals[5]

        vals -= mean(vals, 0)
        acorr(vals, normed=True, maxlags=min(8, len(vals)))
        hlines([0],-8,8, linewidth=2, alpha=.7, linestyle='dotted')
        xticks([])
        ylabel(str(stoch).replace('error in ', '').replace('data','err'),
               fontsize=tiny_fontsize)
        yticks([0,1], fontsize=tiny_fontsize)
        title('mcmc autocorrelation', fontsize=small_fontsize)


    ### actual plotting code start here
    clf()

    figtext(.055, .5, 'a' + ' '*10 + c + ' '*10 + 'a', rotation=270, fontsize=100,
             bbox={'facecolor': 'black', 'alpha': 1},
              color='white', verticalalignment='center', horizontalalignment='right')

    stochs_to_plot = [s_m, s_d, e_d, p_l, s_r, nm, nd, W, H, T]
    stochs_to_hist = [s_m, s_d, e_d, p_l, s_r]

    cols = 4
    rows = len(stochs_to_plot)

    for ii, stoch in enumerate(stochs_to_plot):
        subplot(rows, cols*2, 2*cols - 1 + ii*2*cols)
        try:
            plot(stoch.trace(), linewidth=2, alpha=.5)
        except Exception, e:
            print 'Error: ', e

        xticks([])
        yticks([])
        title('mcmc trace', fontsize=small_fontsize)
        ylabel(str(stoch).replace('error in ', '').replace('data','err'),
               fontsize=tiny_fontsize)

        subplot(rows, cols*2, 2*cols + ii*2*cols)
        try:
            my_acorr(stoch)
        except Exception, e:
            print 'Error: ', e

        try:
            if stoch in stochs_to_hist:
                subplot(len(stochs_to_hist), cols, ii*cols + 3)
                my_hist(stoch)
        except Exception, e:
            print 'Error: ', e

    rows = 5
    subplot(rows, cols/2, 0*(cols/2)+1)
    title('nets manufactured', fontsize=fontsize)
    plot_fit(nm)
    if len(manufacturing_obs) > 0:
        try:
            scatter_data(manufacturing_data, c, 'Country', 'Manu_Itns',
                         error_val=1.96 * s_m.stats()['mean'])
        except Exception, e:
            print 'Error: ', e
            scatter_data(manufacturing_data, c, 'Country', 'Manu_Itns',
                         error_val=1.96 * s_m.value)
    decorate_figure()

    subplot(rows, cols/2, 1*(cols/2)+1)
    title('nets in warehouse', fontsize=fontsize)
    plot_fit(W)
    decorate_figure()

    subplot(rows, cols/2, 2*(cols/2)+1)
    title('nets distributed', fontsize=fontsize)
    plot_fit(nd)
    if len(admin_distribution_obs) > 0:
        label = 'Administrative Data'
        try:
            scatter_data(administrative_distribution_data, c, 'Country', 'Program_totalnets',
                         error_val=1.96 * s_d.stats()['mean'], label=label)
        except Exception, e:
            print 'Error: ', e
            scatter_data(administrative_distribution_data, c, 'Country', 'Program_totalnets',
                         error_val=1.96 * s_m.value, label=label)
    if len(household_distribution_obs) > 0:
        label = 'Survey Data'
        try:
            scatter_data(household_distribution_data, c, 'Name', 'Survey_Itns',
                         error_key='Ste_Survey_Itns', fmt='bs',
                         p_l=p_l.stats()['mean'][0], s_r=s_r.stats()['mean'],
                         label=label)
        except Exception, e:
            print 'Error: ', e
            scatter_data(household_distribution_data, c, 'Name', 'Survey_Itns',
                         error_key='Ste_Survey_Itns', fmt='bs',
                         p_l=p_l.value, s_r=s_r.value,
                         label=label)
    legend(loc='upper left')
    decorate_figure()

    subplot(rows, cols/2, 4*(cols/2)+1)
    title(str(T), fontsize=fontsize)
    plot_fit(T, scale=1.)
    decorate_figure(ystr='Years')
    #l,r,b,t = axis()
    #axis([l, r, 0, 5])

    subplot(rows, cols/2, 3*(cols/2)+1)
    title('nets in households', fontsize=fontsize)
    plot_fit(H)
    if len(household_stock_obs) > 0:
        scatter_data(household_stock_data, c, 'Name', 'Survey_Itns',
                     error_key='Ste_Survey_Itns', fmt='bs')
    decorate_figure()

    savefig('bednets_%s_%s.png' % (c, time.strftime('%Y_%m_%d_%H_%M')))
