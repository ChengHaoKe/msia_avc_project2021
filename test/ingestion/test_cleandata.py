import re
from datetime import datetime
import pandas as pd
import numpy as np
import pytest

try:
    from test.ingestion import df_for_test as testdf
    from src.ingestion import cleandata
except ModuleNotFoundError:
    import df_for_test as testdf
    from ingestion import cleandata


def test_merge_all_happy():
    scry = testdf.scrydf()
    mtgjson = testdf.jsondf()

    scrypr0 = pd.merge(scry, mtgjson, left_on='id', right_on='scryfallId', how='inner')

    # drop cards with rarity type special (just keep the 4 basic types)
    scrypr0 = scrypr0[scrypr0['rarity'].isin(['common', 'rare', 'uncommon', 'mythic'])]
    # drop cards with no released_at
    scrypr0 = scrypr0.dropna(subset=['released_at'])

    scrypr1 = cleandata.Clean(scry, mtgjson).merge_all()
    pd.testing.assert_frame_equal(scrypr1, scrypr0)


def test_merge_all_un():
    df = testdf.just_string()
    with pytest.raises(TypeError):
        cleandata.Clean(df, df).merge_all()


def test_merge_clean_happy():
    scry = testdf.scrydf()
    mtgjson = testdf.jsondf()

    scrypr0 = pd.merge(scry, mtgjson, left_on='id', right_on='scryfallId', how='inner')

    # drop cards with rarity type special (just keep the 4 basic types)
    scrypr0 = scrypr0[scrypr0['rarity'].isin(['common', 'rare', 'uncommon', 'mythic'])]
    # drop cards with no released_at
    scrypr0 = scrypr0.dropna(subset=['released_at'])

    # drop columns that are not needed
    noneed = ['object', 'id', 'oracle_id', 'mtgo_id', 'mtgo_foil_id', 'tcgplayer_id', 'cardmarket_id', 'lang',
              'highres_image', 'image_status', 'image_url', 'type_line', 'oracle_text', 'reserved', 'foil',
              'nonfoil', 'oversized', 'promo', 'variation', 'digital', 'flavor_text', 'artist', 'border_color',
              'frame', 'full_art', 'textless', 'booster', 'watermark', 'printed_name', 'printed_type_line',
              'printed_text', 'content_warning', 'variation_of', 'flavor_name', 'uuid', 'mtgjsonV4Id',
              'scryfallIllustrationId', 'scryfallOracleId', 'minday', 'maxday', 'layout', 'set', 'set_name',
              'set_type', 'collector_number']
    scrypr00 = scrypr0.drop(noneed, axis=1)
    # drop columns with all na
    scrypr00 = scrypr00.dropna(axis=1, how='all')

    # filter columns with very little variation
    numcols = scrypr00.select_dtypes(include=np.number).columns.tolist()
    numcols1 = [c for c in numcols if not re.match(r"pd[0-9]+", c)]

    pkeep = len(scrypr00) * 0.03
    for n in numcols1:
        scrypr00 = scrypr00.fillna({n: 0})
        if scrypr00[n].sum() < pkeep:
            scrypr00 = scrypr00.drop([n], axis=1)

    # manual recode to numeric
    scrypr00['power'] = pd.to_numeric(scrypr00['power'], errors='coerce')
    scrypr00['toughness'] = pd.to_numeric(scrypr00['toughness'], errors='coerce')
    scrypr00['loyalty'] = pd.to_numeric(scrypr00['loyalty'], errors='coerce')
    scrypr00 = scrypr00.fillna({'power': 0, 'toughness': 0, 'loyalty': 0})
    # boolean to numeric / int
    boocols = scrypr00.select_dtypes(include=bool).columns.tolist()
    for b in boocols:
        scrypr00[b] = scrypr00[b] * 1

    # dummy var
    scrypr00 = pd.get_dummies(scrypr00, prefix=['rarity'], columns=['rarity'], drop_first=True)
    # released_at to day from today
    scrypr00['days_since_release'] = scrypr00['released_at'].apply(
        lambda x: (datetime.now() - datetime.strptime(x, "%Y-%m-%d")).days)

    # drop cards with the same name, keep most recent version
    scrypr00 = scrypr00.sort_values(by=['scryfallId', 'name', 'days_since_release', 'pricetype'])
    scrypr00 = scrypr00.drop_duplicates(subset=['name', 'pricetype'], keep='first')
    scrypr00 = scrypr00.drop(['released_at'], axis=1)

    # reorder
    scrypr00 = scrypr00[['scryfallId'] + [c for c in scrypr00.columns if c != 'scryfallId']]

    scrypr11 = cleandata.Clean(scry, mtgjson).merge_clean()
    pd.testing.assert_frame_equal(scrypr11, scrypr00)


def test_merge_clean_un():
    df = testdf.just_string()
    with pytest.raises(TypeError):
        cleandata.Clean(df, df).merge_clean()


def test_for_gee_happy():
    scry = testdf.scrydf()
    mtgjson = testdf.jsondf()

    scrypr0 = pd.merge(scry, mtgjson, left_on='id', right_on='scryfallId', how='inner')

    # drop cards with rarity type special (just keep the 4 basic types)
    scrypr0 = scrypr0[scrypr0['rarity'].isin(['common', 'rare', 'uncommon', 'mythic'])]
    # drop cards with no released_at
    scrypr0 = scrypr0.dropna(subset=['released_at'])

    # drop columns that are not needed
    noneed = ['object', 'id', 'oracle_id', 'mtgo_id', 'mtgo_foil_id', 'tcgplayer_id', 'cardmarket_id', 'lang',
              'highres_image', 'image_status', 'image_url', 'type_line', 'oracle_text', 'reserved', 'foil',
              'nonfoil', 'oversized', 'promo', 'variation', 'digital', 'flavor_text', 'artist', 'border_color',
              'frame', 'full_art', 'textless', 'booster', 'watermark', 'printed_name', 'printed_type_line',
              'printed_text', 'content_warning', 'variation_of', 'flavor_name', 'uuid', 'mtgjsonV4Id',
              'scryfallIllustrationId', 'scryfallOracleId', 'minday', 'maxday', 'layout', 'set', 'set_name',
              'set_type', 'collector_number']
    scrypr00 = scrypr0.drop(noneed, axis=1)
    # drop columns with all na
    scrypr00 = scrypr00.dropna(axis=1, how='all')

    # filter columns with very little variation
    numcols = scrypr00.select_dtypes(include=np.number).columns.tolist()
    numcols1 = [c for c in numcols if not re.match(r"pd[0-9]+", c)]

    pkeep = len(scrypr00) * 0.03
    for n in numcols1:
        scrypr00 = scrypr00.fillna({n: 0})
        if scrypr00[n].sum() < pkeep:
            scrypr00 = scrypr00.drop([n], axis=1)

    # manual recode to numeric
    scrypr00['power'] = pd.to_numeric(scrypr00['power'], errors='coerce')
    scrypr00['toughness'] = pd.to_numeric(scrypr00['toughness'], errors='coerce')
    scrypr00['loyalty'] = pd.to_numeric(scrypr00['loyalty'], errors='coerce')
    scrypr00 = scrypr00.fillna({'power': 0, 'toughness': 0, 'loyalty': 0})
    # boolean to numeric / int
    boocols = scrypr00.select_dtypes(include=bool).columns.tolist()
    for b in boocols:
        scrypr00[b] = scrypr00[b] * 1

    # dummy var
    scrypr00 = pd.get_dummies(scrypr00, prefix=['rarity'], columns=['rarity'], drop_first=True)
    # released_at to day from today
    scrypr00['days_since_release'] = scrypr00['released_at'].apply(
        lambda x: (datetime.now() - datetime.strptime(x, "%Y-%m-%d")).days)

    # drop cards with the same name, keep most recent version
    scrypr00 = scrypr00.sort_values(by=['scryfallId', 'name', 'days_since_release', 'pricetype'])
    scrypr00 = scrypr00.drop_duplicates(subset=['name', 'pricetype'], keep='first')
    scrypr00 = scrypr00.drop(['released_at'], axis=1)

    # reorder
    scrypr00 = scrypr00[['scryfallId'] + [c for c in scrypr00.columns if c != 'scryfallId']]
    # wide to long
    scrypr1 = pd.melt(scrypr00, id_vars=[c for c in scrypr00.columns if not re.match(r"pd[0-9]+", c)],
                      value_vars=[c for c in scrypr00.columns if re.match(r"pd[0-9]+", c)], var_name='priceday',
                      value_name='price')
    scrypr2 = scrypr1.pivot_table(index=[c for c in scrypr1.columns if c not in ['pricetype', 'price']],
                                  columns='pricetype', values='price', aggfunc='first', fill_value=0).reset_index()
    # price day to int
    scrypr2['priceday'] = scrypr2['priceday'].apply(lambda x: re.sub(r'[^0-9]', '', x)).astype(int)
    # sort by id and day order
    scrypr2 = scrypr2.sort_values(by=['scryfallId', 'priceday'])

    scrypr22 = cleandata.Clean(scry, mtgjson).for_gee()
    pd.testing.assert_frame_equal(scrypr22, scrypr2)


def test_for_gee_un():
    df = testdf.just_string()
    with pytest.raises(TypeError):
        cleandata.Clean(df, df).for_gee()


def test_for_kmeans_happy():
    scry = testdf.scrydf()
    mtgjson = testdf.jsondf()

    scrypr0 = pd.merge(scry, mtgjson, left_on='id', right_on='scryfallId', how='inner')

    # drop cards with rarity type special (just keep the 4 basic types)
    scrypr0 = scrypr0[scrypr0['rarity'].isin(['common', 'rare', 'uncommon', 'mythic'])]
    # drop cards with no released_at
    scrypr0 = scrypr0.dropna(subset=['released_at'])

    # drop columns that are not needed
    noneed = ['object', 'id', 'oracle_id', 'mtgo_id', 'mtgo_foil_id', 'tcgplayer_id', 'cardmarket_id', 'lang',
              'highres_image', 'image_status', 'image_url', 'type_line', 'oracle_text', 'reserved', 'foil',
              'nonfoil', 'oversized', 'promo', 'variation', 'digital', 'flavor_text', 'artist', 'border_color',
              'frame', 'full_art', 'textless', 'booster', 'watermark', 'printed_name', 'printed_type_line',
              'printed_text', 'content_warning', 'variation_of', 'flavor_name', 'uuid', 'mtgjsonV4Id',
              'scryfallIllustrationId', 'scryfallOracleId', 'minday', 'maxday', 'layout', 'set', 'set_name',
              'set_type', 'collector_number']
    scrypr00 = scrypr0.drop(noneed, axis=1)
    # drop columns with all na
    scrypr00 = scrypr00.dropna(axis=1, how='all')

    # filter columns with very little variation
    numcols = scrypr00.select_dtypes(include=np.number).columns.tolist()
    numcols1 = [c for c in numcols if not re.match(r"pd[0-9]+", c)]

    pkeep = len(scrypr00) * 0.03
    for n in numcols1:
        scrypr00 = scrypr00.fillna({n: 0})
        if scrypr00[n].sum() < pkeep:
            scrypr00 = scrypr00.drop([n], axis=1)

    # manual recode to numeric
    scrypr00['power'] = pd.to_numeric(scrypr00['power'], errors='coerce')
    scrypr00['toughness'] = pd.to_numeric(scrypr00['toughness'], errors='coerce')
    scrypr00['loyalty'] = pd.to_numeric(scrypr00['loyalty'], errors='coerce')
    scrypr00 = scrypr00.fillna({'power': 0, 'toughness': 0, 'loyalty': 0})
    # boolean to numeric / int
    boocols = scrypr00.select_dtypes(include=bool).columns.tolist()
    for b in boocols:
        scrypr00[b] = scrypr00[b] * 1

    # dummy var
    scrypr00 = pd.get_dummies(scrypr00, prefix=['rarity'], columns=['rarity'], drop_first=True)
    # released_at to day from today
    scrypr00['days_since_release'] = scrypr00['released_at'].apply(
        lambda x: (datetime.now() - datetime.strptime(x, "%Y-%m-%d")).days)

    # drop cards with the same name, keep most recent version
    scrypr00 = scrypr00.sort_values(by=['scryfallId', 'name', 'days_since_release', 'pricetype'])
    scrypr00 = scrypr00.drop_duplicates(subset=['name', 'pricetype'], keep='first')
    scrypr00 = scrypr00.drop(['released_at'], axis=1)

    # reorder
    scrypr00 = scrypr00[['scryfallId'] + [c for c in scrypr00.columns if c != 'scryfallId']]
    # wide to long
    m0 = pd.melt(scrypr00, id_vars=[c for c in scrypr00 if not re.match(r"pd[0-9]+", c)],
                 value_vars=[c for c in scrypr00 if re.match(r"pd[0-9]+", c)], var_name='priceday',
                 value_name='price')
    # get max, min, avg price of each card during time range
    form = []
    for p in set(m0['pricetype'].values.tolist()):
        m1 = m0[m0['pricetype'] == p].groupby(['scryfallId'], as_index=False).agg(
            {'price': ['max', 'min', 'mean']})
        m1.columns = ['scryfallId', p + '_max', p + '_min', p + '_mean']
        form.append(m1)
    # remove duplicates
    m2 = m0[[c for c in m0.columns if c not in ['priceday', 'price', 'pricetype']]]
    m2 = m2.drop_duplicates(keep='first')
    for m in form:
        m2 = pd.merge(m2, m, how='left', on='scryfallId')

    m3 = cleandata.Clean(scry, mtgjson).for_kmeans()
    pd.testing.assert_frame_equal(m3, m2)


def test_for_kmeans_un():
    df = testdf.just_string()
    with pytest.raises(TypeError):
        cleandata.Clean(df, df).for_kmeans()
