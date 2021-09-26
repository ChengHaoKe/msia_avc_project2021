from sklearn import preprocessing
import pandas as pd
import logging.config


logger = logging.getLogger(__name__)
logger.setLevel("INFO")


# z-score scaling -> can be used for entire dataframe
def zscale(data, x, renamecol='_z'):
    """
    Function to transform values in a single or multiple columns into z-scores
    Args:
        data: dataframe object
        x: string name or list of string names of the columns you want to transform
        renamecol: optional suffix added to the newly created z-score columns
    Returns:
         dataframe
    """
    if isinstance(x, list) and (len(x) == 1):
        exo1 = data[x[0]].values
    else:
        exo1 = data[x].values
    if len(exo1.shape) > 1:
        data1 = exo1
    else:
        data1 = exo1.reshape(-1, 1)
    data2 = preprocessing.scale(data1)
    if isinstance(x, list):
        col = []
        for i in x:
            col0 = str(i) + renamecol
            col.append(col0)
    else:
        col = [x + renamecol]
    df = pd.DataFrame(data2, columns=col)
    return df

