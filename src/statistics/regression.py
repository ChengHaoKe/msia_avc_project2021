import re
import logging.config
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats import outliers_influence
import pandas as pd
import numpy as np
from tabulate import tabulate

try:
    from src.statistics import scaling
except ModuleNotFoundError:
    import scaling


logger = logging.getLogger(__name__)
logger.setLevel("INFO")
pd.options.mode.chained_assignment = None


# Variance inflation factor VIF
# example: reg.vif(df, ['x1', 'x2', 'x3'], thresh=10)
def vif(df, x, thresh=10):
    """
    Function to calculate the VIF of multiple columns. Will drop variables and recalculate the VIF as long as the VIF
    of a single column is above the threshold
    Args:
        df: dataframe object
        x: string name or list of string names of the columns you want to transform
        thresh: optional input to determine the VIF threshold for dropping variables
    Returns:
         dataframe
    """
    # verify if list
    if isinstance(x, list) and len(x) > 1:
        col = x.copy()
        # drop na values
        df1 = df[col].dropna()
        if len(df1) < len(df):
            print('### Warning Variance inflation factor requires that all missing data be dropped!\n',
                  'Number of NAs dropped from calculation:', str(len(df) - len(df1)))
        # iterate to remove high VIF variables
        original = len(col) - 1
        vif2 = pd.DataFrame(columns=col)
        for cc in range(0, original):
            vif1 = []
            for i in range(0, len(col)):
                vif0 = outliers_influence.variance_inflation_factor(df1[col].values, i)
                vif1.append(vif0)
            vif2 = pd.DataFrame(vif1).T
            vif2.columns = col
            print('\nRunning iteration:', cc + 1)
            print('Variance inflation factor (VIF):\n', tabulate(vif2, headers='keys', tablefmt='psql', floatfmt='.3f'))
            maxvif = max(vif1)
            if (maxvif > thresh) and (len(vif1) > 2):
                maxind = vif1.index(maxvif)
                dropv = col.pop(maxind)
                print('Dropped variable:', dropv, '   ', 'VIF:', maxvif)
            elif (maxvif > thresh) and len(vif1) <= 2:
                print('# No more variables can be removed, VIF of 1 or more variables are still higher than', thresh)
            else:
                break
        return vif2
    else:
        print('VIF calculations requires at least 2 variables! Please insert as list: [x1, x2]')


# linear regression
# example: df1 = reg.ols(df, "y ~ C(x1, Treatment(reference='0')) + x2")
def ols(data, formula, toprint=True):
    """
        Function to fit a linear regression model
    Args:
        data (dataframe): dataframe object
        formula (string): a string formula similar to that used in R "y ~ x1 + x2"
        toprint (bool): whether to print the results of the model or not

    Returns:
        Fitted model object (dataframe)
        Model results (dataframe)
    """
    if toprint:
        print('Regression result for: \n     {0}\n'.format(formula))
    model = smf.ols(formula, data=data)
    results = model.fit()
    # re0 = results.resid
    if toprint:
        print(results.summary())
        print('# This function returns: model (0), residuals (1)')
    params = results.params
    conf = results.conf_int()
    conf['coef'] = params
    conf.columns = ['2.5%', '97.5%', 'coef']
    conf['p-value'] = results.pvalues
    conf['variables'] = conf.index
    conf = conf[['variables', 'coef', '2.5%', '97.5%', 'p-value']]
    return results, conf.reset_index(drop=True)


# Generalized estimating equation
# example: gee0 = reg.gee(df, formula="y ~ x1 + x2", groupvar='id', family='binomial', toprint=False)
def gee(data, formula, groupvar, family='gaussian', toprint=True):
    """
    Function to fit a GEE model
    Args:
        data (dataframe): dataframe object
        formula (string): a string formula similar to that used in R "y ~ x1 + x2"
        groupvar (string): the grouping variable's string name
        family (string): Intragroup variance structure
        toprint (bool): whether to print the results of the model or not

    Returns:
        Fitted model object (dataframe)
        Model results (dataframe)
    """
    if toprint:
        print('GEE result for: \n     {0}\n'.format(formula))
    if family in ('poisson', 'Poisson'):
        fam = sm.families.Poisson()
    elif family in ('binomial', 'Binomial'):
        fam = sm.families.Binomial()
    elif family in ('gamma', 'Gamma'):
        fam = sm.families.Gamma()
    else:
        # linear regression: normal distribution
        fam = sm.families.Gaussian()
    mod = smf.gee(formula, groupvar, data, family=fam)
    res = mod.fit()

    if family in ('binomial', 'Binomial'):
        params = res.params
        conf = res.conf_int()
        conf['OR'] = params
        conf.columns = ['2.5%', '97.5%', 'OR']
        conf = np.exp(conf)
        conf['p-value'] = res.pvalues
        conf['variables'] = conf.index
        conf = conf[['variables', 'OR', '2.5%', '97.5%', 'p-value']]
    else:
        params = res.params
        conf = res.conf_int()
        conf['coef'] = params
        conf.columns = ['2.5%', '97.5%', 'coef']
        conf['p-value'] = res.pvalues
        conf['variables'] = conf.index
        conf = conf[['variables', 'coef', '2.5%', '97.5%', 'p-value']]
    if toprint:
        print(res.summary())
        if family in ('binomial', 'Binomial'):
            print('# Odds ratios and 95% CI')
            print(tabulate(conf, headers='keys', tablefmt='psql', floatfmt='.3f'))

    return res, conf.reset_index(drop=True)


def run_reg(df, modeltype='gee', groupvar='scryfallId', family='gaussian', scale=False):
    """
        Ensemble function that can be used to run either GEE or OLS
        Args:
            df (dataframe): dataframe object, if running GEE the dataframe produced by for_gee should be used.
                                              if running OLs the dataframe produced by for_kmeans should be used.
            modeltype (string): indicating what type of model to run
            groupvar (string): grouping variable name if using GEE
            family (string): GEE model type (use binomial for logistic GEE)
            scale (bool): whether the data should be scaled
        Returns:
            results1 (dataframe): dataframe containing significant model results
            rmodel (obj): statistical model object
    """
    # set seed
    np.random.seed(0)

    # identify dummy/dichotomous columns
    binarycol = [c for c in df.columns if len(set(df[c].values)) <= 2]
    # identify yvars
    yvar = [c for c in df.columns if re.match(r"sell|buy", c)]

    if scale:
        logger.debug('Scaling data')
        zdf = scaling.zscale(df, [c for c in df.columns if c not in binarycol + [groupvar, 'priceday', 'name'] + yvar],
                             renamecol='')
        # combine scaled and original variables
        zdf0 = pd.concat([df[binarycol + [groupvar] + yvar].reset_index(drop=True),
                          zdf.reset_index(drop=True)], axis=1)
    else:
        zdf0 = df

    # auto formula
    yvar0 = [y for y in yvar if re.match(r'sell', y)][0]
    formula = yvar0 + ' ~ ' + ' + '.join([c for c in zdf0.columns if c not in [groupvar, 'priceday', 'name'] + yvar])
    # model type
    if modeltype == 'gee':
        logger.debug('Running GEE')
        rmodel, results0 = gee(zdf0, formula, groupvar=groupvar, family=family, toprint=False)
    else:
        logger.debug('Running OLS')
        rmodel, results0 = ols(zdf0, formula, toprint=False)
    # if classification
    if family in ('binomial', 'Binomial'):
        logger.debug('Running classification')
        results1 = results0[['variables', 'OR', 'p-value']][(results0['p-value'] < 0.05) &
                                                            (results0['variables'] != 'Intercept')]
        if results1.empty:
            logger.info('No significant results')
            # if nothing is significant
            results1 = pd.DataFrame(['No variables are significant!'], columns=['Explanation'])
        else:
            results1['Explanation'] = np.where(results1['variables'].isin(binarycol),
                                               'A card that has/is ' + results1['variables'] +
                                               ' would have a {} that is '.format(yvar0)
                                               + results1['coef'].astype(str) +
                                               ' times larger/smaller than the average card.',
                                               'One unit increase in ' + results1['variables'] + ' would result in '
                                               + results1['coef'].astype(str) + ' change in {}.'.format(yvar0))
    else:
        results1 = results0[['variables', 'coef', 'p-value']][(results0['p-value'] < 0.05) &
                                                              (results0['variables'] != 'Intercept')]
        if results1.empty:
            logger.info('No significant results')
            # if nothing is significant
            results1 = pd.DataFrame(['No variables are significant!'], columns=['Explanation'])
        else:
            results1['Explanation'] = np.where(results1['variables'].isin(binarycol),
                                               'A card that has/is ' + results1['variables'] +
                                               ' would have a {} that is '.format(yvar0)
                                               + results1['coef'].astype(str) +
                                               ' larger/smaller than the average card.',
                                               'One unit increase in ' + results1['variables'] + ' would result in '
                                               + results1['coef'].astype(str) + ' change in {}.'.format(yvar0))
    return results1, rmodel


if __name__ == '__main__':
    # rdf0 = run_reg(dgee0, modeltype='gee')
    # rdf1 = run_reg(dkmean, modeltype='linear')
    pass
