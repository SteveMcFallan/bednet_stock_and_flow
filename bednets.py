"""  Script to fit stock-and-flow compartmental model of bednet distribution
"""

import settings

from pylab import *
from pymc import *

import copy
import time
import optparse
import random

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
    f = open(settings.PATH + fname)
    csv_f = csv.DictReader(f)
    data = [d for d in csv_f]
    f.close()

    # make sure all floats are floats
    for d in data:
        for k in d.keys():
            try:
                d[k] = float(d[k].replace(',',''))
            except ValueError:
                pass

    return data


def main(country_list=None):
    ### setup the canvas for our plots
    figure(**settings.FIGURE_OPTIONS)

    ### load all data from csv files
    manufacturing_llin_data = load_csv('manuitns.csv')
    administrative_llin_distribution_data = load_csv('adminllins_itns.csv')

    household_llin_stock_data = load_csv('stock_llins.csv')
    household_llin_distribution_data = load_csv('flow_llins.csv')

    retention_llin_data = load_csv('reten.csv')

    coverage_llin_data = load_csv('llincc.csv')
    coverage_itn_data = load_csv('itncc.csv')

    population_data = load_csv('pop.csv')
    household_size_data = load_csv('itncc.csv')


#     ### find parameters for simple model to predict administrative
#     ### distribution data from household distribution data
#     data_dict = {}
#     # store admin data for each country-year
#     for d in administrative_llin_distribution_data:
#         key = (d['Country'], d['Year'])
#         if not data_dict.has_key(key):
#             data_dict[key] = {}
#         data_dict[key]['admin'] = float(d['Program_LLINs'])
#     # store household data for each country-year
#     for d in household_llin_distribution_data:
#         key = (d['Country'], d['Year'])
#         if not data_dict.has_key(key):
#             data_dict[key] = {}
#         data_dict[key]['survey'] = float(d['Total_LLINs'])
#         data_dict[key]['time'] =  float(d['Survey_Year2'])-float(d['Year'])
#         data_dict[key]['survey_ste'] = float(d['Total_st'])
#     # keep only country-years with both admin and survey data
#     for key in data_dict.keys():
#         if len(data_dict[key]) != 4:
#             data_dict.pop(key)

#     x = array([data_dict[k]['admin'] for k in sorted(data_dict.keys())])
#     y = array([data_dict[k]['survey'] for k in sorted(data_dict.keys())])
#     y_e = array([data_dict[k]['survey_ste'] for k in sorted(data_dict.keys())])


#     prior_s_d = Gamma('prior on sampling error in admin dist data', 1., 1./.05, value=.05)
#     prior_e_d = Normal('prior on sys error in admin dist data', 0., 1./.5**2, value=0.)
#     prior_vars = [prior_s_d, prior_e_d]

#     for k in data_dict:
#         @observed
#         @stochastic
#         def net_distribution_data(value=data_dict[k]['admin'], survey_value=data_dict[k]['survey'],
#                               s_d=prior_s_d, e_d=prior_e_d):
#             return normal_like(log(value), log(survey_value) + e_d, 1. / s_d**2)
#         prior_vars.append(net_distribution_data)


#     # sample from empirical prior distribution via MCMC
#     mc = MCMC(prior_vars, verbose=1)
#     mc.use_step_method(AdaptiveMetropolis, [prior_s_d, prior_e_d])

#     if settings.TESTING:
#         iter = 100
#         thin = 1
#         burn = 0
#     else:
#         iter = settings.NUM_SAMPLES
#         thin = 200
#         burn = 20000

#     mc.sample(iter*thin+burn, burn, thin)


#     # output information on empirical prior distribution
#     print str(prior_s_d), prior_s_d.stats()
#     print str(prior_e_d), prior_e_d.stats()

#     mean_e_d = prior_e_d.stats()['mean']

#     y_predicted = exp(arange(log(1000), 16, .1))
#     x_predicted = (1 + mean_e_d) * y_predicted
#     x_predicted = maximum(10, x_predicted)

#     ### setup the canvas for our plots
#     figure(**settings.FIGURE_OPTIONS)

#     clf()
#     subplot(1,2,1)
#     #errorbar(x, y, 1.96*y_e, fmt=',', alpha=.9, linewidth=1.5)
#     plot(x_predicted, y_predicted, 'r:', alpha=.75, linewidth=2, label='predicted value')
#     loglog([1000,exp(16)],[1000,exp(16)], 'k--', alpha=.5, linewidth=2, label='y=x')

#     y = np.concatenate((y_predicted, y_predicted[::-1]))
#     x = np.concatenate(((1 + mean_e_d - 1.96*prior_e_d.stats()['standard deviation']) * y_predicted,
#                        ((1 + mean_e_d + 1.96*prior_e_d.stats()['standard deviation']) * y_predicted)[::-1]))
#     x = maximum(10, x)
#     fill(x, y, alpha=.95, label='Sys Err 95% UI', facecolor=(.8,.4,.4), alpha=.5)

#     x = np.concatenate(((1 + mean_e_d - 1.96*prior_e_d.stats()['standard deviation']) * y_predicted * (1 - 1.96*prior_s_d.stats()['mean']),
#                        ((1 + mean_e_d + 1.96*prior_e_d.stats()['standard deviation']) * y_predicted * (1 + 1.96*prior_s_d.stats()['mean']))[::-1]))
#     x = maximum(10, x)
#     fill(x, y, alpha=.95, label='Total Err 95% UI', facecolor='.8', alpha=.5)

#     axis([1000,exp(16),1000,exp(16)])
#     legend()
#     ylabel('LLINs distributed according to household survey')
#     xlabel('LLINs distributed according to administrative data')
#     for k in data_dict:
#         d = data_dict[k]
#         text(d['admin'], d['survey'], ' %s, %s' % k, fontsize=12, alpha=.5, verticalalignment='center')

#     subplot(2,4,3)
#     hist(prior_e_d.trace(), normed=True, log=False)
#     l,r,b,t = axis()
#     vlines(ravel(prior_e_d.stats()['quantiles'].values()), b, t,
#            linewidth=2, alpha=.75, linestyle='dashed',
#            color=['k', 'k', 'r', 'k', 'k'])
#     yticks([])
#     title(str(prior_e_d), fontsize=12)

#     subplot(2,4,4)
#     hist(prior_s_d.trace(), normed=True, log=False)
#     l,r,b,t = axis()
#     vlines(ravel(prior_s_d.stats()['quantiles'].values()), b, t,
#            linewidth=2, alpha=.75, linestyle='dashed',
#            color=['k', 'k', 'r', 'k', 'k'])
#     yticks([])
#     title(str(prior_s_d), fontsize=12)

#     subplot(2,4,7)
#     plot(prior_e_d.trace())
#     plot(prior_s_d.trace())
#     legend()
#     title('MCMC trace')

#     subplot(2,4,8)
#     acorr(prior_e_d.trace() - mean(prior_e_d.trace()), maxlags=10, normed=True)
#     acorr(prior_s_d.trace() - mean(prior_s_d.trace()), maxlags=10, normed=True)
#     legend()
#     title('MCMC autocorrelation')
#     axis([-10,10,-.2,1.2])
#     yticks([0,1])

#     #savefig(settings.PATH + 'bednets__Priors_%s.png' % time.strftime('%Y_%m_%d_%H_%M'))

    ### pick the country of interest
    country_set = set([d['Country'] for d in population_data])
    print 'fitting models for %d countries...' % len(country_set)

    ### set years for estimation
    year_start = 1999
    year_end = 2011

    for c_id, c in enumerate(sorted(country_set)):
        # hacky way to run only a subset of countries, for parallelizing on the cluster
        if not c_id in country_list:
            continue

        print c

        # get population data for this country, to calculate LLINs per capita
        # TODO: refactor into a data module
        # pop = data.population(c, year_start, year_end)
        population = zeros(year_end - year_start)
        for d in population_data:
            if d['Country'] == c:
                population[int(d['Year']) - year_start] = d['Pop']*1000
        # since we might be predicting into the future, fill in population with last existing value
        for ii in range(1, year_end-year_start):
            if population[ii] == 0.:
                population[ii] = population[ii-1]

        ### setup the model variables
        vars = []
           #######################
          ### compartmental model
         ###
        #######################

        # Empirical Bayesian priors
        logit_pi = Normal('t', .051, .026**-2)
        pi = InvLogit('Pr[net is lost]', logit_pi)
        vars += [logit_pi, pi]
        
        eta = Normal('coverage factor', 4.49, 3.035, value=5.)
        zeta = Normal('zero inflation factor', .235, 122.3, value=.1)
        vars += [eta, zeta]
        
        mu_s_d = 1.05
        s_s_d = .16
        s_d = Normal('error in admin dist data', mu_s_d, s_s_d**-2, value=mu_s_d)

        mu_e_d = .26
        s_e_d = .26
        e_d = Normal('bias in admin dist data', mu_e_d, s_e_d**-2, value=mu_e_d)
        vars += [s_d, e_d]

        # Fully Bayesian priors
        s_m = Lognormal('error in llin ship', log(.1), .5**-2, value=.1)
        vars += [s_m]

        s_r_c = Lognormal('error in report coverage data', log(.01), .1**-2, value=.01)
        vars += [s_r_c]
        
        s_rb = Lognormal('recall bias factor', log(.1), .5**-2, value=.01)
        vars += [s_rb]

        mu_nd = .001 * population
        nd = Lognormal('llins distributed', mu=log(mu_nd), tau=3.**-2, value=mu_nd)
        
        mu_nm = where(arange(year_start, year_end) <= 2003, .00005, .001) * population
        nm = Lognormal('llins shipped', mu=log(mu_nm), tau=3.**-2, value=mu_nm)
        
        mu_h_prime = .001 * population
        Hprime = Lognormal('non-llin household net stock',
                            mu=log(mu_h_prime), tau=3.**-2, value=mu_h_prime)
        
        vars += [nd, nm, Hprime]
        
        W_0 = Lognormal('initial llin warehouse net stock', mu=log(.00005 * population[0]),
                        tau=.3**-2, value=.00005*population[0])
        H_0 = Lognormal('initial llin household net stock', mu=log(.00005 * population[0]),
                        tau=.3**-2, value=.00005*population[0])

        @deterministic(name='llin warehouse net stock')
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

        @deterministic(name='1-year-old household llin stock')
        def H1(H_0=H_0, nd=nd):
            H1 = zeros(year_end-year_start)
            H1[0] = H_0
            for t in range(year_end - year_start - 1):
                H1[t+1] = nd[t]
            return H1

        @deterministic(name='2-year-old household llin stock')
        def H2(H_0=H_0, H1=H1, pi=pi):
            H2 = zeros(year_end-year_start)
            for t in range(year_end - year_start - 1):
                H2[t+1] = H1[t] * (1 - pi)**.5
            return H2

        @deterministic(name='3-year-old household llin stock')
        def H3(H_0=H_0, H2=H2, pi=pi):
            H3 = zeros(year_end-year_start)
            for t in range(year_end - year_start - 1):
                H3[t+1] = H2[t] * (1 - pi)
            return H3

        @deterministic(name='4-year-old household llin stock')
        def H4(H_0=H_0, H3=H3, pi=pi):
            H4 = zeros(year_end-year_start)
            for t in range(year_end - year_start - 1):
                H4[t+1] = H3[t] * (1 - pi)
            return H4

        @deterministic(name='household llin stock')
        def H(H1=H1, H2=H2, H3=H3, H4=H4):
            return H1 + H2 + H3 + H4

        @deterministic(name='llin coverage')
        def llin_coverage(H=H, population=population,
                          eta=eta, zeta=zeta):
            return 1. - zeta - (1-zeta)*exp(-eta * H / population)

        @deterministic(name='itn coverage')
        def itn_coverage(H_llin=H, H_non_llin=Hprime, population=population,
                         eta=eta, zeta=zeta):
            return 1. - zeta - (1-zeta)*exp(-eta * (H_llin + H_non_llin) / population)

        vars += [W_0, H_0, W, T, H, H1, H2, H3, H4, llin_coverage, itn_coverage]


        # set initial condition on W_0 to have no stockouts
        if min(W.value) < 0:
            W_0.value = W_0.value - 2*min(W.value)

           #####################
          ### additional priors
         ###
        #####################

#         @potential
#         def smooth_W(W=W):
#             return normal_like(diff(log(maximum(W,1))), 0., 10.**-2)

#         @potential
#         def smooth_H(H=H):
#             return normal_like(diff(log(maximum(H,1))), 0., 10.**-2)

        @potential
        def smooth_Hprime(H=Hprime):
            return normal_like(diff(log(maximum(H,1))), 0., 1.**-2)

#         @potential
#         def smooth_nd(nd=nd):
#             return normal_like(diff(log(maximum(nd,1))), 0., 10.**-2)

        @potential
        def positive_stocks(H=H, W=W, Hprime=Hprime):
            return -1000 * (dot(H**2, H < 0) + dot(W**2, W < 0) + dot(Hprime**2, Hprime < 0))

        #vars += [smooth_H, smooth_Hprime, smooth_W, smooth_nd, positive_stocks]
        vars += [smooth_Hprime, positive_stocks]

#         @potential
#         def proven_supply(nm=nm):
#             max_log_nm = log(maximum(1.,[max(nm[:(i+1)]) for i in range(len(nm))]))
#             amt_below_cap = minimum(log(maximum(nm,1.)) - max_log_nm, 0.)
#             return normal_like(amt_below_cap, 0., 10.**-2)

        @potential
        def proven_capacity(nd=nd):
            max_log_nd = log(maximum(1.,[max(nd[:(i+1)]) for i in range(len(nd))]))
            amt_below_cap = minimum(log(maximum(nd,1.)) - max_log_nd, 0.)
            return normal_like(amt_below_cap, 0., .25**-2)
        #vars += [proven_capacity, proven_supply]
        vars += [proven_capacity]

           #####################
          ### statistical model
         ###
        #####################


        ### observed nets manufactured

        manufacturing_obs = []
        for d in manufacturing_llin_data:
            if d['Country'] != c:
                continue

            @observed
            @stochastic(name='manufactured_%s_%s' % (d['Country'], d['Year']))
            def obs(value=float(d['Manu_Itns']), year=int(d['Year']), nm=nm, s_m=s_m):
                return normal_like(log(value),  log(max(1., nm[year - year_start])), 1. / s_m**2)
            manufacturing_obs.append(obs)

            # also take this opportinuty to set better initial values for the MCMC
            cur_val = copy.copy(nm.value)
            cur_val[int(d['Year']) - year_start] = float(d['Manu_Itns'])
            #log_nm.value = log(cur_val)
            nm.value = cur_val

        vars += [manufacturing_obs]



        ### observed nets distributed

        admin_distribution_obs = []
        for d in administrative_llin_distribution_data:
            if d['Country'] != c:
                continue

            @observed
            @stochastic(name='administrative_distribution_%s_%s' % (d['Country'], d['Year']))
            def obs(value=d['Program_LLINs'], year=int(d['Year']),
                    nd=nd, s_d=s_d, e_d=e_d):
                return normal_like(log(value), e_d + log(max(1., nd[year - year_start])), 1. / s_d**2)
            admin_distribution_obs.append(obs)

            # also take this opportinuty to set better initial values for the MCMC
            cur_val = copy.copy(nd.value)
            cur_val[int(d['Year']) - year_start] = d['Program_LLINs']
            #log_nd.value = log(cur_val)
            nd.value = cur_val

        vars += [admin_distribution_obs]


        household_distribution_obs = []
        for d in household_llin_distribution_data:
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
                    nd=nd, pi=pi, s_rb=s_rb):
                return normal_like(
                    value,
                    nd[estimate_year - year_start] * (1 - pi) ** (survey_year - estimate_year - .5),
                    1./ (survey_err*(1+s_rb))**2)
            household_distribution_obs.append(obs)

            # also take this opportinuty to set better initial values for the MCMC
            cur_val = copy.copy(nd.value)
            cur_val[estimate_year - year_start] = d2_i / (1 - pi.value)**(survey_year - estimate_year - .5)
            #log_nd.value = log(cur_val)
            nd.value = cur_val

        vars += [household_distribution_obs]


        ### observed household stocks (from survey)
        household_stock_obs = []
        for d in household_llin_stock_data:
            if d['Country'] != c:
                continue
            mean_survey_date = time.strptime(d['Mean_SvyDate'], '%d-%b-%y')
            d['Year'] = mean_survey_date[0] + mean_survey_date[1]/12.

            @observed
            @stochastic(name='LLIN_HH_Stock_%s_%s' % (d['Country'], d['Survey_Year2']))
            def obs(value=d['SvyIndex_LLINstotal'],
                    year=d['Year'],
                    std_err=d['SvyIndex_st'],
                    H=H):
                year_part = year-floor(year)
                H_i = (1-year_part) * H[floor(year)-year_start] + year_part * H[ceil(year)-year_start]
                return normal_like(value, H_i, 1. / std_err**2)
            household_stock_obs.append(obs)

        vars += [household_stock_obs]
        ### observed coverage 
        coverage_obs = []
        for d in coverage_llin_data:
            if d['Country'] != c:
                continue

            d['coverage'] = 1. - float(d['Per_0LLINs'])
            d['coverage_se'] = float(d['LLINs0_SE'])
            mean_survey_date = time.strptime(d['Mean_SvyDate'], '%d-%b-%y')
            d['Year'] = mean_survey_date[0] + mean_survey_date[1]/12.
            
            @observed
            @stochastic(name='LLIN_Coverage_%s_%s' % (d['Country'], d['Survey_Year2']))
            def obs(value=d['coverage'],
                    year=d['Survey_Year2'],
                    std_err=d['coverage_se'],
                    coverage=llin_coverage):
                year_part = year-floor(year)
                coverage_i = (1-year_part) * coverage[floor(year)-year_start] + year_part * coverage[ceil(year)-year_start]
                return normal_like(value, coverage_i, 1. / std_err**2)
            coverage_obs.append(obs)

        for d in coverage_itn_data:
            if d['Country'] != c:
                continue

            d['coverage'] = 1. - float(d['Per_0ITNs'])

            if d['noLLINs'] != 2: # data from survey
                d['coverage_se'] = float(d['ITNs0_SE'])
                mean_survey_date = time.strptime(d['Mean_SvyDate'], '%d-%b-%y')
                d['Year'] = mean_survey_date[0] + mean_survey_date[1]/12.
                @observed
                @stochastic(name='ITN_Coverage_%s_%s' % (d['Country'], d['Year']))
                def obs(value=d['coverage'],
                        year=d['Year'],
                        std_err=d['coverage_se'],
                        coverage=itn_coverage):
                    year_part = year-floor(year)
                    coverage_i = (1-year_part) * coverage[floor(year)-year_start] + year_part * coverage[ceil(year)-year_start]
                    return normal_like(value, coverage_i, 1. / std_err**2)

            else: # data from report
                d['Year'] = d['Survey_Year1'] + .5
                d['coverage_se'] = 0.
                @observed
                @stochastic(name='ITN_Coverage_Report_%s_%s' % (d['Country'], d['Year']))
                def obs(value=d['coverage'],
                        year=d['Year'],
                        std_err=s_r_c,
                        coverage=itn_coverage):
                    year_part = year-floor(year)
                    coverage_i = (1-year_part) * coverage[floor(year)-year_start] + year_part * coverage[ceil(year)-year_start]
                    return normal_like(value, coverage_i, 1. / std_err**2)
            
            coverage_obs.append(obs)


            # also take this opportinuty to set better initial values for the MCMC
            t = floor(d['Year'])-year_start
            cur_val = copy.copy(Hprime.value)
            cur_val[t] = max(.0001*population[t], log(1-d['coverage']) * population[t] / eta.value - H.value[t])
            #log_Hprime.value = log(cur_val)
            Hprime.value = cur_val

        vars += [coverage_obs]

#         ### observed net retention 

#         retention_obs = []
#         for d in retention_llin_data:
#             @observed
#             @stochastic(name='retention_%s_%s' % (d['Name'], d['Year']))
#             def obs(value=float(d['Retention_Rate']),
#                     T_i=float(d['Follow_up_Time']),
#                     pi=pi, s_r=s_r):
#                 return normal_like(value, (1. - pi) ** T_i, 1. / s_r**2)
#             retention_obs.append(obs)

#         vars += [retention_obs]



           #################
          ### fit the model
         ###
        #################
        print 'running fit for net model in %s...' % c

        if settings.METHOD == 'MCMC':
            map = MAP(vars)
            if settings.TESTING:
                map.fit(method='fmin', iterlim=100, verbose=1)
            else:
                map.fit(method='fmin_powell', iterlim=10, verbose=1)

            for stoch in [s_m, s_d, e_d, pi, T]:
                print '%s: %s' % (str(stoch), str(stoch.value))

            mc = MCMC(vars, verbose=1)

            try:
                if settings.TESTING:
                    iter = 100
                    thin = 1
                    burn = 0
                else:
                    iter = settings.NUM_SAMPLES
                    thin = settings.THIN
                    burn = settings.BURN
                mc.sample(iter*thin+burn, burn, thin)
            except:
                pass

        elif settings.METHOD == 'NormApprox':
            na = NormApprox(vars)
            na.fit(method='fmin_powell', tol=.00001, verbose=1)
            for stoch in [s_m, s_d, e_d, pi]:
                print '%s: %s' % (str(stoch), str(stoch.value))
            na.sample(1000)

        else:
            assert 0, 'Unknown estimation method'
            
        # save results in output file
        col_headings = ['Country', 'Year',
                        'LLINs Shipped (Thousands)', 'LLINs Shipped Lower CI', 'LLINs Shipped Upper CI',
                        'LLINs Distributed (Thousands)', 'LLINs Distributed Lower CI', 'LLINs Distributed Upper CI',
                        'LLINs in Warehouse (Thousands)', 'LLINs in Warehouse Lower CI', 'LLINs in Warehouse Upper CI',
                        'LLINs Owned (Thousands)', 'LLINs Owned Lower CI', 'LLINs Owned Upper CI',
                        'non-LLIN ITNs Owned (Thousands)', 'non-LLIN ITNs Owned Lower CI', 'non-LLIN ITNs Owned Upper CI',
                        'LLIN Coverage (Percent)', 'LLIN Coverage Lower CI', 'LLIN Coverage Upper CI',
                        'ITN Coverage (Percent)', 'ITN Coverage Lower CI', 'ITN Coverage Upper CI']
        
        try:  # sleep for a random time interval to avoid collisions when writing results
            print 'sleeping...'
            time.sleep(random.random()*30)
            print '...woke up'
        except:  # but let user cancel with cntl-C if there is a rush
            print '...work up early'

        if not settings.CSV_NAME in os.listdir(settings.PATH):
            f = open(settings.PATH + settings.CSV_NAME, 'a')
            f.write('%s\n' % ','.join(col_headings))
        else:
            f = open(settings.PATH + settings.CSV_NAME, 'a')

        for t in range(year_end - year_start):
            f.write('%s,%d,' % (c,year_start + t))
            if t == year_end - year_start - 1:
                val = [-1, -1, -1]
                val += [-1, -1, -1]
            else:
                val = [nm.stats()['mean'][t]/1000] + list(nm.stats()['95% HPD interval'][t]/1000)
                val += [nd.stats()['mean'][t]/1000] + list(nd.stats()['95% HPD interval'][t]/1000)
            val += [W.stats()['mean'][t]/1000] + list(W.stats()['95% HPD interval'][t]/1000)
            val += [H.stats()['mean'][t]/1000] + list(H.stats()['95% HPD interval'][t]/1000)
            val += [Hprime.stats()['mean'][t]/1000] + list(Hprime.stats()['95% HPD interval'][t]/1000)
            val += [100*llin_coverage.stats()['mean'][t]] + list(100*llin_coverage.stats()['95% HPD interval'][t])
            val += [100*itn_coverage.stats()['mean'][t]] + list(100*itn_coverage.stats()['95% HPD interval'][t])
            f.write(','.join(['%.2f']*(len(col_headings)-2)) % tuple(val))
            f.write('\n')
        f.close()

           ######################
          ### plot the model fit
         ###
        ######################
        fontsize = 14
        small_fontsize = 12
        tiny_fontsize = 10

        def plot_fit(f, scale=1.e6, style='lines'):
            """ Plot the posterior mean and 95% UI
            """
            if style=='lines' or style=='alt lines':
                x = year_start + arange(len(f.value))
                y = f.stats()['mean']/scale
                lb = f.stats()['quantiles'][2.5]/scale
                ub = f.stats()['quantiles'][97.5]/scale
            elif style=='steps':
                x = []
                for ii in range(len(f.value)):
                    x.append(ii)
                    x.append(ii)

                y = (f.stats()['mean']/scale)[x]
                lb = (f.stats()['quantiles'][2.5]/scale)[x]
                ub = (f.stats()['quantiles'][97.5]/scale)[x]
                x = array(x[1:] + [ii+1]) + year_start
            else:
                raise ValueError, 'unrecognized style option: %s' % str(style)

            if style=='alt lines':
                plot(x, y, 'b:', alpha=.75)
                plot(x, lb, 'b:', alpha=.75)
                plot(x, ub, 'b:', alpha=.75)
            else:
                plot(x, y, 'k-', linewidth=2, label='Est Mean')

                x = np.concatenate((x, x[::-1]))
                y = np.concatenate((lb, ub[::-1]))
                fill(x, y, alpha=.95, label='Est 95% UI', facecolor='.8', alpha=.5)

        def scatter_data(data_list, country, country_key, data_key,
                         error_key=None, error_val=0.,  pi=None, s_r=None,
                         fmt='go', scale=1.e6, label='', offset=0.):
            """ This convenience function is a little bit of a mess, but it
            avoids duplicating code for scatter-plotting various types of
            data, with various types of error bars
            """

            data_val = array([float(d[data_key]) for d in data_list if d[country_key] == c])
            if len(data_val) == 0:
                return

            if error_key:
                error_val = array([1.96*float(d[error_key]) \
                                       for d in data_list if d[country_key] == c])

            elif error_val:
                error_val = 1.96 * error_val * data_val
            x = array([float(d['Year']) for d in data_list if d[country_key] == c])
            errorbar(x + offset,
                     data_val/scale,
                     error_val/scale, fmt=fmt, alpha=.95, label=label)

        def stoch_max(stoch):
            return max(stoch.stats()['95% HPD interval'][:,1])

        def decorate_figure(ystr='# of Nets (Millions)', ymax=False):
            """ Set the axis, etc."""
            l,r,b,t = axis()
            if ymax:
                t = ymax*1.2
            vlines(range(year_start,year_end), 0, t, color=(0,0,0), alpha=.3)
            axis([year_start, 2009, 0, t])
            ylabel(ystr, fontsize=fontsize)
            xticks([1999.5, 2001.5, 2003.5, 2005.5, 2007.5], ['1999', '2001', '2003', '2005', '2007'], fontsize=fontsize)

        def my_hist(stoch):
            """ Plot a histogram of the posterior distribution of a stoch"""
            hist(stoch.trace(), normed=True, log=False, label=str(stoch), alpha=.5)
            #l,r,b,t = axis()
            #vlines(ravel(stoch.stats()['quantiles'].values()), b, t,
            #       linewidth=2, alpha=.75, linestyle='dashed',
            #       color=['black', 'black', 'red', 'black', 'black'])
            yticks([])

            if str(stoch).find('distribution waiting time') == -1:
                a,l = xticks()
                l = [int(floor(x*100.)) for x in a]
                l[0] = str(l[0]) + '%'
                xticks([])
                xticks(floor(array(a)*100.)/100., l, fontsize=small_fontsize)
            #title(str(stoch), fontsize=small_fontsize)
            ylabel('probability density')

            leg = legend(loc='upper left')
            # the matplotlib.patches.Rectangle instance surrounding the legend
            frame = leg.get_frame()  
            frame.set_alpha(0.)    # set the frame face color to light gray
            frame.set_edgecolor('white')    # set the frame face color to light gray
            
            # matplotlib.text.Text instances
            for t in leg.get_texts():
                t.set_fontsize('small')    # the legend text fontsize


        def my_acorr(stoch):
            """ Plot the autocorrelation of the a stoch trace"""
            vals = copy.copy(stoch.trace())
            if shape(vals)[-1] == 1:
                vals = ravel(vals)

            if len(shape(vals)) > 1:
                vals = array(vals)[:,5]

            vals -= mean(vals, 0)
            acorr(vals, normed=True, maxlags=min(8, len(vals)))
            hlines([0],-8,8, linewidth=2, alpha=.7, linestyle='dotted')
            xticks([])
            #ylabel(str(stoch).replace('error in ', '').replace('data','err'),
            #       fontsize=tiny_fontsize)
            yticks([0,1], fontsize=tiny_fontsize)
            #title('mcmc autocorrelation', fontsize=small_fontsize)


        ### actual plotting code start here
        clf()

        figtext(.055, .5, 'a' + ' '*20 + c + ' '*20 + 'a', rotation=270, fontsize=100,
                 bbox={'facecolor': 'black', 'alpha': 1},
                  color='white', verticalalignment='center', horizontalalignment='right')

        stochs_to_plot = [s_m, s_d, e_d, pi, pi, nm, nd, W, H, s_r_c, eta, zeta, s_rb]

        cols = 4
        rows = len(stochs_to_plot)

        figtext(6.05/8., .925, 'mcmc trace', horizontalalignment='center', verticalalignment='top', fontsize=small_fontsize)
        figtext(6.85/8., .925, 'mcmc autocorrelation', horizontalalignment='center', verticalalignment='top', fontsize=small_fontsize)
        
        for ii, stoch in enumerate(stochs_to_plot):
            figtext(6.45/8., .097 + .814*(1-(ii+.0)/rows), str(stoch), horizontalalignment='center', verticalalignment='top', fontsize=small_fontsize)
            subplot(rows, cols*2, 2*cols - 1 + ii*2*cols)
            try:
                plot(stoch.trace(), linewidth=2, alpha=.5)
            except Exception, e:
                print 'Error: ', e

            xticks([])
            yticks([])

            subplot(rows, cols*2, 2*cols + ii*2*cols)
            try:
                my_acorr(stoch)
            except Exception, e:
                print 'Error: ', e

        subplot(5, cols, 0*cols + 3)
        my_hist(s_m)
        my_hist(s_r_c)
        xticks([0., .02, .04, .06, .08, .1], ['0%', '2', '4', '6', '8', '10'], fontsize=small_fontsize)


        subplot(5, cols, 1*cols + 3)
        my_hist(s_d)
        my_hist(e_d)
        xticks([0., .5, 1., 1.5, 2.], ['0%', '50', '100', '150', '200'], fontsize=small_fontsize)

        subplot(5, cols, 2*cols + 3)
        my_hist(pi)
        #my_hist(s_r)
        xticks([0., .1, .2, .3, .4], ['0%', '10', '20', '30', '40'], fontsize=small_fontsize)

        subplot(5, cols, 3*cols + 3)
        my_hist(eta)
        xticks([])
        xticks([3, 6, 9], [3, 6, 9], fontsize=small_fontsize)

        subplot(5, cols, 4*cols + 3)
        my_hist(s_rb)
        my_hist(zeta)
        xticks([0., .02, .04, .06], ['0%', '2', '4', '6'], fontsize=small_fontsize)
        

        rows = 5
        subplot(rows, cols/2, 0*(cols/2)+1)
        title('LLINs shipped (per capita)', fontsize=fontsize)
        plot_fit(nm, scale=population, style='steps')
        if len(manufacturing_obs) > 0:
            scatter_data(manufacturing_llin_data, c, 'Country', 'Manu_Itns', scale=mean(population),
                         error_val=1.96 * s_m.stats()['mean'], offset=.5)
        decorate_figure(ymax=.2)

        subplot(rows, cols/2, 1*(cols/2)+1)
        title('LLINs in country, not in households (per capita)', fontsize=fontsize)
        plot_fit(W, scale=population)
        decorate_figure(ymax=.2)

        subplot(rows, cols/2, 2*(cols/2)+1)
        title('LLINs distributed (per capita)', fontsize=fontsize)
        plot_fit(nd, style='steps', scale=population)
        if len(admin_distribution_obs) > 0:
            label = 'Administrative Data'
            scatter_data(administrative_llin_distribution_data, c, 'Country', 'Program_LLINs', scale=mean(population),
                         error_val=1.96 * s_d.stats()['mean'], label=label, offset=.5)
        if len(household_distribution_obs) > 0:
            label = 'Survey Data'
            scatter_data(household_llin_distribution_data, c, 'Country', 'Total_LLINs', scale=mean(population),
                         error_key='Total_st', fmt='bs',
                         pi=pi.stats()['mean'][0], #s_r=s_r.stats()['mean'],
                         label=label, offset=.5)
        legend(loc='upper left')
        decorate_figure(ymax=.2)

        subplot(rows, cols/2, 4*(cols/2)+1)
        title('ITN and LLIN coverage', fontsize=fontsize)
        plot_fit(itn_coverage, scale=.01)
        plot_fit(llin_coverage, scale=.01, style='alt lines')
        if max(itn_coverage.stats()['mean']) > .1:
            hlines([80], 1999, 2009, linestyle='dotted', color='blue', alpha=.5)

        # calculate coverage from fraction of households with zero llins
        for d in coverage_llin_data:
            d['coverage'] = 1. - float(d['Per_0LLINs'])
            mean_survey_date = time.strptime(d['Mean_SvyDate'], '%d-%b-%y')
            d['Year'] = mean_survey_date[0] + mean_survey_date[1]/12.
        scatter_data(coverage_llin_data, c, 'Country', 'coverage', 'LLINs0_SE',
                     fmt='bs', scale=.01)
        scatter_data(coverage_itn_data, c, 'Country', 'coverage', 'coverage_se',
                     fmt='r^', scale=.01)
        decorate_figure(ystr='At least one net (%)', ymax=80)

        subplot(rows, cols/2, 3*(cols/2)+1)
        title('LLINs in households (per capita)', fontsize=fontsize)
        plot_fit(H, scale=population)
        for d in household_llin_stock_data:
            mean_survey_date = time.strptime(d['Mean_SvyDate'], '%d-%b-%y')
            d['Year'] = mean_survey_date[0] + mean_survey_date[1]/12.
        scatter_data(household_llin_stock_data, c, 'Country', 'SvyIndex_LLINstotal', scale=mean(population),
                     error_key='SvyIndex_st', fmt='bs')
        decorate_figure(ymax=.2)

        savefig('bednets_%s_%d_%s.png' % (c, c_id, time.strftime('%Y_%m_%d_%H_%M')))

    # close the output file
    f.close()

if __name__ == '__main__':
    usage = 'usage: %prog [options] country_id'
    parser = optparse.OptionParser(usage)
    (options, args) = parser.parse_args()

    if len(args) != 1:
        parser.error('incorrect number of arguments')
    else:
        try:
            id = int(args[0])
        except ValueError:
            parser.error('country_id must be an integer')

        main(country_list = [id])
