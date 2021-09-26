import logging.config
import re
from sklearn.cluster import KMeans
import matplotlib.pyplot as plt
import pandas as pd
from tabulate import tabulate
from sklearn import metrics
from sklearn.metrics.pairwise import euclidean_distances

try:
    from src.statistics import scaling
except ModuleNotFoundError:
    import scaling


logger = logging.getLogger(__name__)
logger.setLevel("INFO")
pd.options.mode.chained_assignment = None


# elbow plot for clustering
# example: elb0 = cl.elbow(df, 15)
def elbow(data, k=15, randomseed=0, noplot=True):
    """
    Function to plot an elbow plot
    Args:
        data (dataframe): dataframe object
        k (int): SSE of the maximum number cluster solution to plot
        randomseed (int): integer used for reproducibility
        noplot (bool): whether or not to NOT plot the elbow plot
    Returns:
         dataframe with two columns, one for k and the other for SSE
    """
    # data is the subset dataframe for clustering, only include variables needed!
    data1 = data.values
    sse = []
    ks = range(1, k)
    for k in ks:
        km = KMeans(n_clusters=k, random_state=randomseed)
        km = km.fit(data1)
        sse.append(km.inertia_)

    if not noplot:
        plt.plot(ks, sse, 'bx-')
        plt.xlabel('k')
        plt.ylabel('Within-cluster sum-of-squared errors')
        plt.title('Elbow Method For Optimal k')
        plt.show()

    df = pd.DataFrame()
    df['k'] = list(ks)
    df['sse'] = sse
    df['slope'] = df['sse'].diff()
    df['slope_change'] = df['slope'].pct_change()
    df['slope_diff'] = df['slope_change'].diff()
    df['slope_diff2'] = df['slope_diff'].diff()
    return df


# k-means clustering
# example: km0 = cl.kmclust(df, 4)
# to get fitted groups: xx = = km0[2].values
def kmclust(data, k, randomseed=0, fig=False):
    """
    Function to run a K-means clustering model
    Args:
        data: dataframe object
        k: number of clusters to use
        randomseed (int): integer used for reproducibility
        fig: whether to plot the K-means scatter plot
    Returns:
         km: fitted K-means object
         kcenter: a dataframe with the cluster centers
         fit0: a dataframe containing the groups of each sample
    """
    # data is the subset dataframe for clustering, only include variables needed!
    print('# This function returns: model (0), cluster center (1), groups (2)')
    data1 = data.values
    km = KMeans(n_clusters=k, init='k-means++', random_state=randomseed).fit(data1)
    print('# K-means cluster centers:')
    kcenter = pd.DataFrame(km.cluster_centers_)
    kcenter.columns = list(data.columns.values)
    print(tabulate(kcenter, headers='keys', tablefmt='psql', floatfmt='.3f'))
    fit0 = km.labels_
    dists = euclidean_distances(data, data)
    dists0 = pd.DataFrame(dists, columns=['v' + str(i) for i in range(dists.shape[1])])

    print('\nCluster size:')
    fit1 = pd.DataFrame(km.labels_, columns=['kmgroups'])
    size0 = pd.DataFrame(fit1['kmgroups'].value_counts()).sort_index()
    print(tabulate(size0, headers='keys', tablefmt='psql'))
    if fig:
        y_km = km.fit_predict(data1)
        plt.figure()
        plt.title("K-means Scatter Plot")
        for i in range(0, k):
            plt.scatter(data1[y_km == i, 0], data1[y_km == i, 1])
    return km, kcenter, fit0, dists0


# cluster performance scores
# example: ck1 = cl.clusterscore(df, df['kmgroups'])
def clusterscore(data, label, method='silhouette', tolog=False):
    """
    Function to calculate clustering statistics
    Args:
        data: dataframe object
        label: a pandas Series or dataframe column containing the cluster group labels
        method: the type of statistic to calculate
        tolog: Option to choose whether or not to log the produced score
    Returns:
         a float value of the calculated score
    """
    # for more information: https://scikit-learn.org/stable/modules/clustering.html#clustering-performance-evaluation
    data1 = data.values
    label1 = label.values  # labels are the calculated cluster groups
    if method in ['Calinski-Harabaz Index', 'Calinski-Harabaz', 'Variance Ratio Criterion', 'Calinski-Harabaz score',
                  'calinski', 'calinski-harabaz', 'Variance Ratio']:
        score = metrics.calinski_harabaz_score(data1, label1)
        print('Calinski-Harabaz Index:', str(score))
        print('\nThe score is higher when clusters are dense and well separated, which relates'
              ' to a model with better defined clusters.')
    elif method in ['Davies-Bouldin Index', 'Davies-Bouldin', 'Davies-Bouldin score', 'davies', 'davies-bouldin']:
        score = metrics.davies_bouldin_score(data1, label1)
        print('Davies-Bouldin Index:', str(score))
        print('\nA lower Davies-Bouldin index relates to a model with better separation between the clusters.\n'
              'Zero is the lowest possible score. Values closer to zero indicate a better partition.')
    else:
        score = metrics.silhouette_score(data1, label1, metric='euclidean')
        print('Silhouette Coefficient (mean):', str(score))
        print('\nThe score is bounded between -1 for incorrect clustering and +1 for highly dense clustering.\n'
              'Scores around zero indicate overlapping clusters.')
    if tolog:
        logging.info('Score of {0} metric is: {1}'.format(method, score))
    return score


def run_kmeans(df, method='silhouette', noplot=True):
    """
        Ensemble function that runs all K-means clustering related functions
        Args:
            df (dataframe): pandas dataframe produced by for_kmeans
            method (string): string indicating the type of cluster metric to calculate
            noplot (bool): whether the elbow plot should not be plotted (if False will cause Flask to crash)
        Returns:
            kcenter0 (dataframe): dataframe containing cluster centers
            distdf2 (dataframe): dataframe containing cluster groups and pairwise distances
            score0 (float): cluster score produced by scoring metrics
    """
    idcols = ['scryfallId', 'name']

    # scale data
    logger.debug('Scaling data')
    binarycol = [c for c in df.columns if len(set(df[c].values)) <= 2]
    zdf = scaling.zscale(df, [c for c in df.columns if c not in binarycol + idcols], renamecol='')
    # combine scaled and original variables
    zdf0 = pd.concat([df[binarycol].reset_index(drop=True), zdf.reset_index(drop=True)], axis=1)

    # elbow plot
    logger.debug('Running elbow plot')
    elbow0 = elbow(zdf0, noplot=noplot)
    bestk = elbow0['k'][elbow0['slope_change'] == elbow0['slope_change'].min()].values[0]
    print('Best k:', bestk)
    logging.info('Best k for Kmeans is {}'.format(bestk))

    # get clusters and distances
    logger.debug('Running K-means')
    kmodel, kcenter0, label0, dist0 = kmclust(zdf0, bestk)
    distdf = df[idcols]
    distdf['kmgroups'] = label0
    dist0.columns = distdf['name'].values.tolist()
    distdf1 = pd.concat([distdf.reset_index(drop=True), dist0.reset_index(drop=True)], axis=1)
    distdf2 = pd.melt(distdf1, id_vars=idcols + ['kmgroups'],
                      value_vars=[c for c in distdf1.columns if c not in idcols + ['kmgroups']], var_name='card',
                      value_name='distance')
    distdf = distdf.rename(columns={'kmgroups': 'matchgroup', 'name': 'card'})
    distdf2 = pd.merge(distdf2, distdf[['card', 'matchgroup']], on='card', how='inner')
    # get price data
    yvar = [c for c in df.columns if re.match(r"sell|buy", c)]
    yvar0 = [y for y in yvar if re.match(r'sell', y)][0]
    pricedf = df[['name', yvar0]]
    pricedf = pricedf.rename(columns={'name': 'card', yvar0: 'price'})

    distdf2 = pd.merge(distdf2, pricedf, on='card', how='left')

    # score
    logger.debug('Running clusterscore')
    score0 = clusterscore(zdf0, distdf['matchgroup'], method=method, tolog=True)
    return kcenter0, distdf2, score0


if __name__ == '__main__':
    # kcenter1, distdf, score1 = run_kmeans(dkmean)
    pass
