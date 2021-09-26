import os
import yaml
import time
from datetime import datetime
import traceback
import logging.config
import pandas as pd
from flask import Flask
from flask import render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

try:
    from src.storage import tomysql, s3tofrom
    from src.ingestion import get_data, cleandata
    from config.flaskconfig import SQLALCHEMY_DATABASE_URI, DB_USER, DB_PW, DATABASE, DB_HOST
    from src.statistics import clustering, regression
except ModuleNotFoundError:
    from ingestion import get_data, cleandata
    from storage import tos3, tomysql
    from ingestion import get_data, cleandata
    from flaskconfig import SQLALCHEMY_DATABASE_URI
    from statistics import clustering, regression


# Initialize the Flask application
app = Flask(__name__, template_folder="app/templates", static_folder="app/static")
# don't cache css so we can see updates
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

# Configure flask app from flask_config.py
app.config.from_pyfile('config/flaskconfig.py')

# mysql = MySQL(app)
db = SQLAlchemy(app)
session = db.session

# Define LOGGING_CONFIG in flask_config.py - path to config file for setting
# up the logger (e.g. config/logging/local.conf)
logging.config.fileConfig(app.config["LOGGING_CONFIG"])
logger = logging.getLogger(app.config["APP_NAME"])
logger.debug('web_app_log')


@app.route("/", methods=["GET"])
def home():
    """Function that renders the default home.html page"""
    if request.method == "GET":
        try:
            conn = db.engine.connect().connection
            chsql = tomysql.MysqlAll(u=DB_USER, p=DB_PW, db=DATABASE, schema='msia423_db')
            sqlc = "SELECT * FROM msia423_db.cards"
            cards = chsql.read_table(query=sqlc, cursor=conn)
            return render_template("home.html", cards=cards['cardname'].values.tolist())
        except Exception as e:
            traceback.print_exc()
            logger.error('Error with autocomplete query! {}'.format(e))
    return render_template("home.html", cards=[])


@app.route("/", methods=['POST'])
def result():
    """
        Function that outputs the result of a card name query from user card name and number of cards inputs
        Returns:
            Renders the query.html page if it runs successfully, defaults to error.html if an error occurs
    """
    if request.method == 'POST':
        cardname = request.form.get('cardname')
        numbcard = request.form.get('ncard0')
        try:
            # strip left and right whitespace
            cardname = cardname.rstrip().lstrip()
            # create connection
            conn = db.engine.connect().connection
            print(DB_USER, DB_PW, DATABASE)
            chsql = tomysql.MysqlAll(u=DB_USER, p=DB_PW, db=DATABASE, schema='msia423_db', isflask=True)
            sql0 = "SELECT * FROM msia423_db.cluster_result WHERE `name` = \"{0}\" and card != \"{0}\"".format(cardname)
            km1 = chsql.read_table(query=sql0, cursor=conn)
            logger.info('Obtained data for {} from database'.format(cardname))

            km1 = km1[km1['kmgroups'] == km1['matchgroup']]
            km1 = km1.sort_values(by=['distance'])
            # get top n
            km10 = km1.iloc[:int(numbcard)]
            km10 = km10.drop(['scryfallId'], axis=1)

            # get card image
            imagecard0 = [cardname] + km10['card'].values.tolist()
            imagecard1 = ', '.join(['\"' + i + '\"' for i in imagecard0])
            isql = "SELECT `name`, image_url FROM msia423_db.merge_raw WHERE `name` IN ({}) " \
                   "AND image_url IS NOT NULL".format(imagecard1)
            idf0 = chsql.read_table(query=isql, cursor=conn)
            logger.info('Obtained image url for {} from database'.format(cardname))

            # rename and drop duplicates
            idf0 = idf0.rename(columns={'name': 'card'})
            idf0 = idf0.dropna(subset=['card'])
            idf0 = idf0.drop_duplicates(subset=['card'], keep='first')
            if idf0.empty:
                idf1 = ''
                logger.warning('Nothing queried for {}'.format(cardname))
            else:
                idf1 = idf0['image_url'][idf0['card'] == cardname].values[0]
            # merge image url to kmeans dataframe
            idf2 = idf0[idf0['card'] != cardname]
            km11 = pd.merge(km10, idf2, on='card', how='left')

            return render_template("query.html", tkmean=km11.to_dict(orient='records'), card_name=cardname,
                                   card_image_url=idf1, headers=km11.columns.to_list())
        except Exception as e:
            traceback.print_exc()
            logger.error('Error with query! {}'.format(e))
            return render_template('error.html')


@app.route("/query/")
def query():
    """Function that renders the default query.html page"""
    df1 = pd.DataFrame(['Click button to search!'], columns=['Enter a card name from Standard!'])
    df2 = df1.to_html(classes='dataframe', header="true", index=False)
    return render_template("query.html", tables=[df2])


@app.route("/statistics/", methods=['GET', 'POST'])
def statistics():
    """
        Function that outputs the result of GEE and OLS function output dataframes
        Returns:
            Renders the statistics.html page if it runs successfully, defaults to error.html if an error occurs
    """
    try:
        conn = db.engine.connect().connection
        chsql = tomysql.MysqlAll(u=DB_USER, p=DB_PW, db=DATABASE, schema='msia423_db')
        sql1 = "SELECT * FROM msia423_db.gee_result"
        gee1 = chsql.read_table(query=sql1, cursor=conn)
        gee2 = gee1.to_html(classes='dataframe', header="true", index=False)
        logger.info('GEE model results queried')

        sql2 = "SELECT * FROM msia423_db.ols_result"
        ols1 = chsql.read_table(query=sql2, cursor=conn)
        ols2 = ols1.to_html(classes='dataframe', header="true", index=False)
        logger.info('OLS model results queried')
        print(gee1)
        print(ols1)

        return render_template("statistics.html", tgee=[gee2], tols=[ols2])
    except Exception as e:
        traceback.print_exc()
        logger.error('Error with statistics page! {}'.format(e))
        return render_template('error.html')


@app.route("/refresh/", methods=['GET', 'POST'])
def refresh():
    """
        Function that refreshes the data store in both S3 and RDS
        Returns:
            Renders the refresh.html page if it runs successfully, defaults to error.html if an error occurs
    """
    logs = ''
    status = ''
    if request.method == 'POST':
        yamlpath = os.path.join('config', 'plebmtg.yaml')
        with open(yamlpath, 'r') as f:
            yaml0 = yaml.load(f, Loader=yaml.FullLoader)

        runbool = 1
        status = "Data hasn't been updated"
        if os.path.isfile(yaml0['app']['refresh']['refreshfile']):
            strdate = []
            with open(yaml0['app']['refresh']['refreshfile']) as f:
                for line in f.readlines():
                    strdate.append(line)
                f.close()
            if datetime.now().strftime('%Y-%m-%d') == strdate[0]:
                status = 'Data already refreshed today! ' + strdate[0]
                runbool = 0
                logger.warning('Data already refreshed today! {}'.format(strdate[0]))
            else:
                status = 'Data last refreshed on ' + strdate[0]

        if runbool == 1:
            startt = time.time()
            try:
                mtg = get_data.MTGAPI()
                scry0 = mtg.scryfall_api()
                prices = mtg.mtgjson_api()

                # upload raw data to S3
                s3tofrom.to_s3(scry0, customname="chrawdata/scryfall1", **yaml0['s3tofrom'])
                s3tofrom.to_s3(prices, customname="chrawdata/mtgjson1", **yaml0['s3tofrom'])
                s3_time = 'Finished raw data upload to S3 at: ' + str(time.time() - startt)

                # merge scryfall and mtgjson data + clean them
                cclean = cleandata.Clean(scry0, prices, **yaml0['get_data']['merge_all'])
                mergeraw = cclean.merge_all()
                dgee = cclean.for_gee()
                dkmean = cclean.for_kmeans()
                clean_time = 'Finished data cleaning at: ' + str(time.time() - startt)

                kcenter1, kmdf0, score1 = clustering.run_kmeans(dkmean, **yaml0['clustering']['run_kmeans'])
                rdf0, rmodel0 = regression.run_reg(dgee, modeltype='gee', **yaml0['regression']['run_reg'])
                rdf1, rmodel1 = regression.run_reg(dkmean, modeltype='linear', **yaml0['regression']['run_reg'])
                model_time = 'Finished statistical calculations at: ' + str(time.time() - startt)

                # save model to s3
                s3tofrom.model_save(rmodel0, s3pathfile='chmodel/gee.joblib', **yaml0['s3tofrom'])
                s3tofrom.model_save(rmodel1, s3pathfile='chmodel/ols.joblib', **yaml0['s3tofrom'])

                # get all unique card names
                namedf = pd.DataFrame(list(set(dkmean['name'].values.tolist())), columns=['cardname'])

                print(DB_USER, DB_PW, DATABASE)
                chsql = tomysql.MysqlAll(u=DB_USER, p=DB_PW, db=DATABASE, schema='msia423_db', isflask=True)

                chsql.insert_df(kmdf0, name='cluster_result', replace=True)
                chsql.insert_df(rdf0, name='gee_result', replace=True)
                chsql.insert_df(rdf1, name='ols_result', replace=True)
                chsql.insert_df(mergeraw, name='merge_raw', replace=True)
                chsql.insert_df(namedf, name='cards', replace=True)
                db_time = 'Finished database updates at: ' + str(time.time() - startt)
                # write update date to a text file
                with open(yaml0['app']['refresh']['refreshfile'], 'w') as file:
                    file.write(datetime.now().strftime('%Y-%m-%d'))
                    file.close()
                # + s3_time + '   '
                logs = logs + '<br>' + clean_time + '<br>' + model_time + '<br>' + db_time
                logger.info(logs)
            except Exception as e:
                traceback.print_exc()
                logger.error('Error with the refresh page! {}'.format(e))
                return render_template('error.html')
    return render_template("refresh.html", logs=logs, status=status)


@app.route('/error/', methods=['POST'])
def error():
    """View that process a POST with new song input

    :return: redirect to index page
    """

    return render_template('error.html')


if __name__ == '__main__':
    app.run(debug=app.config["DEBUG"], port=app.config["PORT"], host=app.config["HOST"])
