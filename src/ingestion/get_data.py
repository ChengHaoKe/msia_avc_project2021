import time
import re
import logging.config
import requests
import pandas as pd
import numpy as np
from bs4 import BeautifulSoup


try:
    from src.utils import minifuncs as minif
except ModuleNotFoundError:
    from utils import minifuncs as minif


logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def url_wait(func, wait=200, **kwargs):
    """
        Helper function used to automatically re-run the requests.get function in the event a connection error happens.

        Args:
            func = the function to loop
            wait = number of loops to re-try
            kwargs = additional inputs needed by the `func` function

        Returns:
            The function result object
    """
    t0 = 0
    for i in range(wait):
        try:
            response = func(**kwargs)
            return response
        except requests.exceptions.ConnectionError:
            time.sleep(0.1)
            t0 += 0.1
    print('Error! Retried for {0} seconds, but url is unresponsive!'.format(t0))
    logging.error('Warning! Retried for {0} seconds, but url is unresponsive!'.format(t0))


class MTGAPI:
    """Class to obtain MTG data using APIs. All APIs / mini-scrapers do not need a key to access."""
    def __init__(self):
        self.scryfall = 'https://api.scryfall.com/bulk-data/default-cards'
        self.mtgjson = 'https://mtgjson.com/api/v5/AllPrices.json'
        self.identifier = 'https://mtgjson.com/api/v5/AllIdentifiers.json'
        self.creatures = 'https://www.mtggoldfish.com/format-staples/standard/full/creatures'
        self.spells = 'https://www.mtggoldfish.com/format-staples/standard/full/spells'

    def scryfall_api(self):
        """
            Obtains data from the Scryfall bulk download API. Does a simple filtering to keep only standard legal
            non-basic land cards so that subsequent operations will be more efficient. Promotional and non-English
            cards are also filtered out.

            Returns:
                Pandas dataframe
        """

        start_time = time.time()

        re0 = url_wait(requests.get, wait=200, url=self.scryfall)
        logging.info('Status code for scryfall bulk data url: {}'.format(re0.status_code))
        bulk0 = re0.json()

        re1 = url_wait(requests.get, wait=200, url=bulk0['download_uri'])
        logging.info('Status code for scryfall data download: {}'.format(re1.status_code))
        js0 = re1.json()

        card0 = pd.DataFrame.from_dict(js0)
        card1 = card0[(card0['legalities'].apply(lambda x: x['standard']) == 'legal') &
                      (card0['set_type'].isin(['expansion', 'core'])) & (card0['lang'] == 'en')]
        card1 = card1[~card1['type_line'].str.contains('Basic Land')]
        # drop url and card description columns, keep image uri
        dropcol0 = [c for c in card1.columns if 'uri' in c and c != 'image_uris'] + \
                   ['all_parts', 'preview', 'card_faces']
        card1 = card1.drop(dropcol0, axis=1)
        # fill na with empty list to avoid TypeError
        card1['image_uris'] = card1['image_uris'].apply(lambda x: {x} if not isinstance(x, dict) else x)
        card1['image_url'] = card1['image_uris'].apply(lambda x: x['normal'] if 'normal' in x
                                                       else (x['large'] if 'large' in x
                                                             else (x['small'] if 'small' in x else np.nan)
                                                             ))

        # split color cols
        colors = list(set(re.sub(r"\{|\}|[0-9]|/|\s+", '', ''.join([i for i in card1['mana_cost'].values.tolist()
                                                                    if str(i) != 'nan']))))
        for c in colors:
            card1['colors_' + c] = card1['mana_cost'].str.count(c).fillna(0)
        # split identity color cols
        icolor = list(set(re.sub(r"\{|\}|'|\]|\[|,|/|\s+", '', ''.join([str(i) for i in
                                                                        card1['color_identity'].values.tolist()]))))
        for ic in icolor:
            card1['icolor_' + ic] = card1['color_identity'].apply(lambda x: 1 if ic in x else 0)
        # split keywords
        keyw0 = list(set([i for j in card1['keywords'].values.tolist() for i in j]))
        for k in keyw0:
            card1['kw_' + re.sub(r'-|,|/|\s+', '', k)] = card1['keywords'].apply(lambda x: 1 if k in x else 0)
        # recode a few columns (mostly from lists/dicts)
        card1['ispromo'] = np.where(card1['promo_types'].isna(), 0, 1)
        card1['difframe'] = np.where(card1['frame_effects'].isna(), 0, 1)
        card1['arenahas'] = np.where(card1['arena_id'].isna(), 0, 1)
        # recode produced mana
        pmana = list(set(re.sub(r"\{|\}|'|\]|\[|,|/|\s+", '',
                                ''.join([str(i) for i in card1['produced_mana'].values.tolist() if str(i) != 'nan']))))
        for pm in pmana:
            card1['pmana_' + pm] = card1['produced_mana'].apply(lambda x: x.count(pm) if isinstance(x, list) else 0)

        # drop additional columns
        dropcol1 = ['multiverse_ids', 'games', 'legalities', 'prices', 'artist_ids', 'colors', 'mana_cost',
                    'color_identity', 'illustration_id', 'card_back_id', 'produced_mana', 'promo_types',
                    'frame_effects', 'keywords', 'arena_id', 'image_uris']
        card1 = card1.drop(dropcol1, axis=1)

        print("Scryfall ran for: {0} seconds ({1} mins)".format(str(round(time.time() - start_time, 2)),
                                                                str(round((time.time() - start_time) / 60))))
        logging.info('Scryfall ran for {} seconds'.format(round(time.time() - start_time, 2)))
        return card1

    def mtgjson_id(self, keepraw=False):
        """
            Obtains the identifier json file from the MTGJSON API. This file allows the MTGJSON historical price data
            to be joined with the card characteristics data provided by Scryfall. Simple filtering is also done to
            increase code efficiency. Non-standard legal cards and cards not available in paper formats are excluded.
            Returns:
                Pandas dataframe, list of columns that contain keys used for joining
        """

        re0 = url_wait(requests.get, wait=200, url=self.identifier)
        logging.info('Status code for mtgjson identifier: {}'.format(re0.status_code))

        iden0 = re0.json()
        iden0 = iden0['data']
        iden1 = pd.DataFrame.from_dict(iden0).T

        # filter df to make it smaller
        mask0 = (iden1['availability'].apply(lambda x: 'paper' in x if isinstance(x, list) else False)) & \
                (iden1['legalities'].apply(lambda x: 'standard' in x if isinstance(x, dict) else False))
        iden2 = iden1[mask0]
        iden2 = iden2[~iden2['type'].str.contains('Basic Land')]

        # recode rulings from list of dicts
        iden2['newrules'] = iden2['rulings'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        # expand subtypes
        keepcol = []
        subtype = list(set([i for j in iden2['subtypes'].values.tolist() for i in j]))
        for bt in subtype:
            newcol = 'subtype_' + re.sub(r'-|,|/|\s+', '', bt)
            iden2[newcol] = iden2['subtypes'].apply(lambda x: 1 if isinstance(x, list) and bt in x else 0)
            keepcol.append(newcol)
        # expand supertypes
        supertype = list(set([i for j in iden2['supertypes'].values.tolist() for i in j]))
        for ut in supertype:
            newcol = 'supertype_' + re.sub(r'-|,|/|\s+', '', ut)
            iden2[newcol] = iden2['supertypes'].apply(lambda x: 1 if isinstance(x, list) and ut in x else 0)
            keepcol.append(newcol)
        # expand types
        types0 = list(set([i for j in iden2['types'].values.tolist() for i in j]))
        for typ in types0:
            newcol = 'types_' + re.sub(r'-|,|/|\s+', '', typ)
            iden2[newcol] = iden2['types'].apply(lambda x: 1 if isinstance(x, list) and typ in x else 0)
            keepcol.append(newcol)

        logging.info('MTGJSON ID finished all column expansions.')

        # remove columns that are not used
        iden2 = iden2[['name', 'uuid', 'identifiers'] + keepcol]

        # get id columns
        idkey0 = [i for i in iden2['identifiers'].iloc[0].keys() if any(s in i for s in ['mtgjson', 'scryfall'])]
        iddf0 = pd.DataFrame(
            iden2['identifiers'].apply(lambda x: {key: x[key] if key in x else '' for key in idkey0}).tolist())
        iden3 = pd.concat([iden2.reset_index(drop=True), iddf0], axis=1)
        iden3 = iden3.drop('identifiers', axis=1)

        idkey1 = idkey0 + keepcol
        if keepraw:
            return iden3, idkey1, iden1
        else:
            return iden3, idkey1

    def mtgjson_api(self):
        """
            Combines historical price data for the past 3 months with the identifier dataframe. The output has one
            column for each day's price data. Each card has 2 rows of price data, one for retail and the other for
            buylist. Cards without non-foil paper prices are dropped.

            Returns:
                Pandas dataframe
        """

        start_time = time.time()
        iden3, idkey0 = self.mtgjson_id()
        logging.info('MTGjson identifier ran for {} seconds'.format(round(time.time() - start_time, 2)))

        rejson = url_wait(requests.get, wait=200, url=self.mtgjson)
        logging.info('Status code for mtgjson prices: {}'.format(rejson.status_code))
        price0 = rejson.json()

        # get what is inside data key
        price0 = price0['data']
        price1 = pd.DataFrame.from_dict(price0).T
        price1['uuid'] = price1.index
        price1 = price1.reset_index(drop=True).drop('mtgo', axis=1)

        price2 = pd.merge(iden3, price1, on='uuid', how='inner')
        # price2['pricesource'] = price2['paper'].apply(lambda x: [i for i in x.keys()
        #                                               if any(s in i for s in ['cardkingdom', 'tcgplayer'])])
        # drill down to get price of non-foil paper cards
        price2['pricesource'] = price2['paper'].apply(lambda x: list(x.keys())[0])
        price2 = price2.dropna(subset=['pricesource'], how='any')
        price2['buy'] = price2['paper'].apply(
            lambda x: x[list(x.keys())[0]]['buylist'] if 'buylist' in x[list(x.keys())[0]] else np.nan)
        price2['sell'] = price2['paper'].apply(
            lambda x: x[list(x.keys())[0]]['retail'] if 'retail' in x[list(x.keys())[0]] else np.nan)
        price2 = price2.dropna(subset=['buy', 'sell'], how='any')
        price2['buynormal'] = price2['buy'].apply(lambda x: x['normal'] if 'normal' in x else np.nan)
        price2['sellnormal'] = price2['sell'].apply(lambda x: x['normal'] if 'normal' in x else np.nan)
        price2 = price2.dropna(subset=['buynormal', 'sellnormal'], how='any')
        price2 = price2.reset_index(drop=True)

        logging.info('MTGJSON price function finished extracting non-foil paper prices.')

        # expand dict of daily prices
        buy0 = pd.DataFrame(price2['buynormal'].values.tolist(), price2.index).add_prefix('p_')
        sel0 = pd.DataFrame(price2['sellnormal'].values.tolist(), price2.index).add_prefix('p_')
        buydcol = buy0.columns.tolist()
        seldcol = sel0.columns.tolist()

        # add price type and min/max dates
        buy0['pricetype'] = 'buy'
        sel0['pricetype'] = 'sell'
        buy0['minday'] = min(buydcol)
        buy0['maxday'] = max(buydcol)
        sel0['minday'] = min(seldcol)
        sel0['maxday'] = max(seldcol)
        # rename columns
        buy0.columns = ['pd' + str(i) for i in range(len(buydcol))] + ['pricetype', 'minday', 'maxday']
        sel0.columns = ['pd' + str(i) for i in range(len(seldcol))] + ['pricetype', 'minday', 'maxday']

        # missing day columns imputation
        ndays = minif.ndays()
        dcols = ['pd{}'.format(i) for i in range(ndays)]

        bscol = list(set(buy0.columns.tolist() + sel0.columns.tolist() + dcols))
        nobuy = [i for i in bscol if i not in buy0.columns.tolist()]
        nosel = [i for i in bscol if i not in sel0.columns.tolist()]

        for c in nobuy:
            buy0[c] = np.nan
        for c in nosel:
            sel0[c] = np.nan

        pricebuy = pd.concat([price2[['uuid'] + idkey0], buy0], axis=1)
        pricesel = pd.concat([price2[['uuid'] + idkey0], sel0], axis=1)
        price3 = pd.concat([pricebuy, pricesel], axis=0).reset_index(drop=True)

        print("MTGJSON ran for: {0} seconds ({1} mins)".format(str(round(time.time() - start_time, 2)),
                                                               str(round((time.time() - start_time) / 60))))
        logging.info('MTGjson data ran for {} seconds'.format(round(time.time() - start_time, 2)))
        return price3

    def mtggoldfish(self):
        """
            HTML parser function to obtain usage data for the most popular creature and spell cards within Standard.
            Only obtains the most up to date data.

            Returns:
                Pandas dataframe
        """

        top0 = []
        for u in [self.creatures, self.spells]:
            gold0 = url_wait(requests.get, wait=200, url=u)
            logging.info('Status code for mtggoldfish url {0}: {1}'.format(u, gold0.status_code))

            gold1 = gold0.content
            soup0 = BeautifulSoup(gold1, 'html.parser')
            # get all data in html table
            tab0 = soup0.find_all('table')
            tab1 = pd.read_html(str(tab0[0]))[0]
            top0.append(tab1)
        top1 = pd.concat(top0)

        # drop index column and columns with no value
        top1 = top1.drop([c for c in top1.columns if 'Unnamed' in c], axis=1)
        top1 = top1.dropna(axis=1, how='all')

        return top1


if __name__ == '__main__':
    mtg = MTGAPI()

    # gold1 = mtg.mtggoldfish()
    scry0 = mtg.scryfall_api()
    mjson0 = mtg.mtgjson_api()
    pass
