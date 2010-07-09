""" Module to generate empirical priors for the stock-and-flow model
for bednet distribution
"""
import settings

from numpy import *
from pymc import *

import simplejson as json
import os
import time

from data import Data
data = Data()

import graphics


def llin_discard_rate(recompute=False):
    """ Return the empirical priors for the llin discard rate Beta stoch,
    calculating them if necessary.

    Parameters
    ----------
    recompute : bool, optional
      pass recompute=True to force recomputation of empirical priors, even if json file exists

    Results
    -------
    returns a dict suitable for using to instantiate a Beta stoch
    """
    # load and return, if applicable
    fname = 'discard_prior.json'
    if fname in os.listdir(settings.PATH) and not recompute:
        f = open(settings.PATH + fname)
        return json.load(f)
        
    ### setup (hyper)-prior stochs
    pi = Beta('Pr[net is lost]', 1, 2)
    sigma = InverseGamma('standard error', 11, 1)

    vars = [pi, sigma]

    ### data likelihood from net retention studies
    retention_obs = []
    for d in data.retention:
        @observed
        @stochastic(name='retention_%s_%s' % (d['name'], d['year']))
        def obs(value=d['retention_rate'],
                T_i=d['follow_up_time'],
                pi=pi, sigma=sigma):
            return normal_like(value, (1. - pi) ** T_i, 1. / sigma**2)
        retention_obs.append(obs)

        vars += [retention_obs]

    # find model with MCMC
    mc = MCMC(vars, verbose=1, db='pickle', dbname=settings.PATH + 'discard_prior_%s.pickle' % time.strftime('%Y_%m_%d_%H_%M'))
    iter = 10000
    thin = 20
    burn = 20000
    mc.sample(iter*thin+burn, burn, thin)
    mc.db.commit()

    # save fit values for empirical prior
    x = pi.stats()['mean']
    v = pi.stats()['standard deviation']**2

    emp_prior_dict = dict(mu=x, var=v, tau=1/v,
                          alpha=x*(x*(1-x)/v-1), beta=(1-x)*(x*(1-x)/v-1))
    f = open(settings.PATH + fname, 'w')
    json.dump(emp_prior_dict, f)

    graphics.plot_discard_prior(pi, emp_prior_dict)
    
    return emp_prior_dict


def improve_admin_err_and_bias_from_posterior():
    """ Use the results of the posterior estimates to generate
    improved estimates of the empirical priors for admin error and
    bias.  This is analogous to a step in the EM algorithm.
    """

    # make a list of flow data dicts from output.csv
    import csv
    flow_data = []
    for d in csv.DictReader(open(settings.PATH + 'output.csv')):
        if d['Country'] in ['Liberia', 'SaoTome & Principe', 'Cameroon', 'Malawi', 'Madagascar']:
            if int(d['Year']) >= 2007:
                flow_data.append(dict(country=d['Country'],
                                      year=int(d['Year']),
                                      total_llins=float(d['LLINs Distributed (Thousands)'])*1000.,
                                      total_st=(float(d['LLINs Shipped Lower CI'])-float(d['LLINs Shipped Upper CI'])) * 1000. / (2.*1.96)
                                      ))

    # recompute empirical priors
    admin_err_and_bias(recompute=True, flow_data=flow_data)
    
                

def admin_err_and_bias(recompute=False, flow_data=None):
    """ Return the empirical priors for the admin error and bias stochs,
    calculating them if necessary.

    Parameters
    ----------
    recompute : bool, optional
      pass recompute=True to force recomputation of empirical priors,
      even if json file exists

    flow_data : list of dicts, optional
      this defaults to the household survey llin flow data, but for
      more accurate borrowing of strength between regions, it can be
      replaced.  each dict on the list needs 4 keys:
        * country, lower case string
        * year, int betweer settings.year_start and settings.year_end
        * total_llins, float, number of llins distributed in this country-year
        * total_st. float, standard error for estimated total_llins

    Results
    -------
    returns a dict suitable for using to instantiate a Beta stoch
    """
    # load and return, if applicable
    fname = 'admin_err_and_bias_prior.json'
    if fname in os.listdir(settings.PATH) and not recompute:
        f = open(settings.PATH + fname)
        return json.load(f)

    mu_pi = llin_discard_rate()['mu']

    # setup hyper-prior stochs
    sigma = Gamma('error in admin dist data', 1., 1.)
    eps = Normal('bias in admin dist data', 0., 1.)
    beta = Uniform('relative weight', 0., 2., value=.1)
    vars = [sigma, eps, beta]

    ### setup data likelihood stochs
    data_dict = {}
    for country in data.countries:
        for year in data.years:
            data_dict[(country, year)] = {}

    # store admin data for each country-year
    for d in data.admin_llin:
        key = (d['country'], d['year'])
        data_dict[key]['obs_t'] = d['program_llins']

    # store household data for each country-year
    if flow_data == None:
        flow_data = data.hh_llin_flow
    for d in flow_data:
        key = (d['country'], d['year'])
        data_dict[key]['true_t'] = d['total_llins']
        data_dict[key]['se_t'] = d['total_st']

        key = (d['country'], d['year']-1)
        data_dict[key]['true_{t+1}'] = d['total_llins']
        data_dict[key]['se_{t+1}'] = d['total_st']
        
    # keep only country-years with both admin and survey data
    for key in data_dict.keys():
        if len(data_dict[key]) != 5:
            data_dict.pop(key)

    print 'fitting %d data points' % len(data_dict)

    # create the observed stochs
    data_vars = []
    for k, d in data_dict.items():
        @deterministic(name='pred_%s'%str(k))
        def pred(mu=d['true_t'], mu_next=d['true_{t+1}'], eps=eps, beta=beta):
            return log(max(1., mu + beta*mu_next)) + eps

        @observed
        @stochastic(name='obs_%s'%str(k))
        def obs(value=log(d['obs_t']),
                pred=pred,
                log_v=1.1*d['se_t']**2/d['true_t']**2 + 1.1*d['se_{t+1}']**2/d['true_{t+1}']**2,
                sigma=sigma):
            return normal_like(value, pred,
                               1. / (log_v + sigma**2))
        data_vars.append([obs, pred])
    vars.append(data_vars)

    # sample from empirical prior distribution via MCMC
    mc = MCMC(vars, verbose=1, db='pickle', dbname=settings.PATH + 'admin_err_prior_%s.pickle' % time.strftime('%Y_%m_%d_%H_%M'))
    iter = 10000
    thin = 20
    burn = 20000
    mc.sample(iter*thin+burn, burn, thin)
    mc.db.commit()

    # output information on empirical prior distribution
    emp_prior_dict = dict(
        sigma=dict(mu=sigma.stats()['mean'],
                   std=sigma.stats()['standard deviation'],
                   tau=sigma.stats()['standard deviation']**-2),
        eps=dict(mu=eps.stats()['mean'],
                 std=eps.stats()['standard deviation'],
                 tau=eps.stats()['standard deviation']**-2),
        beta=dict(mu=beta.stats()['mean'],
                  std=beta.stats()['standard deviation'],
                  tau=beta.stats()['standard deviation']**-2))

    f = open(settings.PATH + fname, 'w')
    json.dump(emp_prior_dict, f)

    graphics.plot_admin_priors(eps, sigma, emp_prior_dict, data_dict, data_vars, mc)

    return emp_prior_dict


def neg_binom(recompute=False):
    """ Return the empirical priors for the coverage factor and
    dispersion factor, calculating them if necessary.

    Parameters
    ----------
    recompute : bool, optional
      pass recompute=True to force recomputation of empirical priors,
      even if json file exists

    Results
    -------
    returns a dict suitable for using to instantiate normal and beta stochs
    """
    # load and return, if applicable
    fname = 'neg_binom_prior.json'
    if fname in os.listdir(settings.PATH) and not recompute:
        f = open(settings.PATH + fname)
        return json.load(f)

    # setup hyper-prior stochs
    e = Normal('coverage parameter', 5., 3.)
    a = Exponential('dispersion parameter', 1.)
    vars = [e, a]

    ### setup data likelihood stochs
    data_dict = {}

    # store population data for each country-year
    for d in data.population:
        key = (d['country'], d['year'])
        data_dict[key] = {}
        data_dict[key]['pop'] =  d['pop']*1000

    # store stock data for each country-year
    for d in data.hh_llin_stock:
        key = (d['country'], d['survey_year1'])
        data_dict[key]['stock'] = d['svyindex_llins'] / data_dict[key]['pop']
        data_dict[key]['stock_se'] = d['svyindexllins_se'] / data_dict[key]['pop']

    # store coverage data for each country-year
    for d in data.llin_coverage:
        key = (d['country'], d['survey_year1'])
        data_dict[key]['uncovered'] =  d['per_0llins']
        data_dict[key]['se'] = d['llins0_se']
        
    # keep only country-years with both stock and coverage
    for key in data_dict.keys():
        if len(data_dict[key]) != 5:
            data_dict.pop(key)

    # create stochs from stock and coverage data
    for k, d in data_dict.items():
        stock = Normal('stock_%s_%s' % k, mu=d['stock'], tau=d['stock_se']**-2)
        
        @observed
        @stochastic
        def obs(value=d['uncovered'], stock=stock, tau=d['se']**-2,
                e=e, a=a):
            return normal_like(value,
                               exp(negative_binomial_like(0, e * stock, a)),
                               tau)
        vars += [stock, obs]

    # sample from empirical prior distribution via MCMC
    mc = MCMC(vars, verbose=1, db='pickle', dbname=settings.PATH + 'neg_binom_prior_%s.pickle' % time.strftime('%Y_%m_%d_%H_%M'))
    iter = 1000
    thin = 20
    burn = 2000
    mc.sample(iter*thin+burn, burn, thin)
    mc.db.commit()


    # output information on empirical prior distribution
    emp_prior_dict = dict(
        eta=dict(mu=e.stats()['mean'],
                 std=e.stats()['standard deviation'],
                 tau=e.stats()['standard deviation']**-2),
        alpha=dict(mu=a.stats()['mean'],
                   std=a.stats()['standard deviation'],
                   alpha=a.stats()['mean']**2/a.stats()['standard deviation']**2,
                   beta=a.stats()['mean']/a.stats()['standard deviation']**2)
        )

    f = open(settings.PATH + fname, 'w')
    json.dump(emp_prior_dict, f)

    graphics.plot_neg_binom_priors(e, a, emp_prior_dict, data_dict)

    return emp_prior_dict


def survey_design(recompute=False):
    """ Return the empirical prior for the survey design factor

    Results
    -------
    returns a dict suitable for using to instantiate normal and beta stochs
    """
    # load and return, if applicable
    fname = 'survey_design_effect_prior.json'
    if fname in os.listdir(settings.PATH) and not recompute:
        f = open(settings.PATH + fname)
        return json.load(f)

    obs = [d['itncomplex_to_simpleratio'] for d in data.design] + \
        [d['llincomplex_to_simpleratio'] for d in data.design if d['llincomplex_to_simpleratio']]
    emp_prior_dict = dict(mu=mean(obs), std=std(obs), tau=1/var(obs))

    f = open(settings.PATH + fname, 'w')
    json.dump(emp_prior_dict, f)

    graphics.plot_survey_design_prior(emp_prior_dict, obs)

    return emp_prior_dict


if __name__ == '__main__':
    import optparse
    
    usage = 'usage: %prog [options]'
    parser = optparse.OptionParser(usage)
    (options, args) = parser.parse_args()

    if len(args) != 0:
        parser.error('incorrect number of arguments')

    admin_err_and_bias()
    llin_discard_rate()
    neg_binom()
    survey_design()
    
    graphics.plot_neg_binom_fits()
