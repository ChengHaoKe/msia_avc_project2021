import os
import yaml
import argparse
import logging.config
import pandas as pd

try:
    from src.ingestion import get_data as getd, cleandata
    from src.storage import s3tofrom, tomysql
    from config.flaskconfig import SQLALCHEMY_DATABASE_URI
    from src.storage import msia423_sql as m423
    from src.statistics import clustering, regression
except ModuleNotFoundError:
    from ingestion import get_data as getd, cleandata
    from storage import tos3, tomysql
    from flaskconfig import SQLALCHEMY_DATABASE_URI
    from statistics import clustering, regression


logging.config.fileConfig(os.path.join('config', 'logging', 'local.conf'))
logger = logging.getLogger('ch-plebMTG')


if __name__ == '__main__':
    yamlpath = os.path.join('config', 'plebmtg.yaml')
    with open(yamlpath, 'r') as f:
        yaml0 = yaml.load(f, Loader=yaml.FullLoader)

    # Add parsers for both creating a database and adding songs to it
    parser = argparse.ArgumentParser(description="Create and/or add data to database")
    subparsers = parser.add_subparsers(dest='subparser_name')

    # Sub-parser for creating a database
    sb_create = subparsers.add_parser("s3rds", description="Create a table and ingest data from s3")
    sb_create.add_argument("--engine_string", default=SQLALCHEMY_DATABASE_URI,
                           help="SQLAlchemy connection URI for database")

    # optional arguments if u want to directly change the connection string
    sb_create.add_argument("--schema", default='msia423_db', help="Database table schema")
    sb_create.add_argument("--user", default='', help="Database username")
    sb_create.add_argument("--password", default='', help="Database password")
    sb_create.add_argument("--dbname", default='msia423_db', help="Database name")
    sb_create.add_argument("--replace", default='yes', help="Whether to replace an existing table")
    sb_create.add_argument("--bucket", default="2021-msia423-ke-chenghao", help="Name of the S3 bucket to get data")
    sb_create.add_argument("--item1", default="chrawdata/gold1", help="Name of the mtggoldfish raw data item")
    sb_create.add_argument("--item2", default="chrawdata/scryfall1", help="Name of the scryfall raw data item")
    sb_create.add_argument("--item3", default="chrawdata/mtgjson1", help="Name of the mtgjson raw data item")

    # parser to create only an empty table
    sb_create = subparsers.add_parser("sqlempty", description="Create an empty sql table")
    sb_create.add_argument("--engine_string", default=SQLALCHEMY_DATABASE_URI,
                           help="SQLAlchemy connection URI for database")

    # Sub-parser for ingesting new data
    sb_ingest = subparsers.add_parser("ingests3", description="Add data to s3 bucket")
    sb_ingest.add_argument("--item1", default="gold1", help="Name of the mtggoldfish raw data item")
    sb_ingest.add_argument("--item2", default="scryfall1", help="Name of the scryfall raw data item")
    sb_ingest.add_argument("--item3", default="mtgjson1", help="Name of the mtgjson raw data item")
    sb_ingest.add_argument("--bucket", default="2021-msia423-ke-chenghao", help="Name of the S3 bucket to upload data")

    # Sub-parser for only doing modeling (random google form requirement...)
    sb_ingest = subparsers.add_parser("fgoogle", description="Add data to s3 bucket")
    sb_ingest.add_argument("--item2", default="scryfall1", help="Name of the scryfall raw data item")
    sb_ingest.add_argument("--item3", default="mtgjson1", help="Name of the mtgjson raw data item")

    args = parser.parse_args()
    sp_used = args.subparser_name

    if sp_used == 'ingests3':
        # get raw data from the API
        mtg = getd.MTGAPI()
        scry0 = mtg.scryfall_api()
        prices = mtg.mtgjson_api()

        # upload raw data to S3
        s3tofrom.to_s3(scry0, customname=args.item2, bucket=args.bucket)
        s3tofrom.to_s3(prices, customname=args.item3, bucket=args.bucket)

    elif sp_used == 's3rds':
        # download raw data from s3
        s3scry = s3tofrom.from_s3(bucket=args.bucket, s3pathfile=args.item2)
        s3json = s3tofrom.from_s3(bucket=args.bucket, s3pathfile=args.item3)

        # merge scryfall and mtgjson data + clean them
        cclean = cleandata.Clean(s3scry, s3json, **yaml0['get_data']['merge_all'])
        mergeraw = cclean.merge_all()
        dgee = cclean.for_gee()
        dkmean = cclean.for_kmeans()

        kcenter1, kmdf0, score1 = clustering.run_kmeans(dkmean, **yaml0['clustering']['run_kmeans'])
        rdf0, rmodel0 = regression.run_reg(dgee, modeltype='gee', **yaml0['regression']['run_reg'])
        rdf1, rmodel1 = regression.run_reg(dkmean, modeltype='linear', **yaml0['regression']['run_reg'])
        # get all unique card names
        namedf = pd.DataFrame(list(set(dkmean['name'].values.tolist())), columns=['cardname'])

        # if the user and password arguments are not provided
        if (args.user != '') and (args.password != ''):
            chsql = tomysql.MysqlAll(u=args.user, p=args.password, db=args.dbname, schema=args.schema)
        else:
            chsql = tomysql.MysqlAll(connstring=args.engine_string, schema=args.schema)

        # whether the user wants to replace an existing table or append to it
        replace0 = True if args.replace == 'yes' else False

        chsql.insert_df(kmdf0, name='cluster_result', replace=replace0)
        chsql.insert_df(rdf0, name='gee_result', replace=replace0)
        chsql.insert_df(rdf1, name='ols_result', replace=replace0)
        chsql.insert_df(mergeraw, name='merge_raw', replace=replace0)
        chsql.insert_df(namedf, name='cards', replace=replace0)

    elif sp_used == 'fgoogle':
        # this only reads data from S3 and runs the models, no insertion back into RDS
        # (so basically it is only for fulfilling the google form requirement...)
        # download raw data from s3
        s3scry = s3tofrom.from_s3(bucket=args.bucket, s3pathfile=args.item2)
        s3json = s3tofrom.from_s3(bucket=args.bucket, s3pathfile=args.item3)

        # merge scryfall and mtgjson data + clean them
        cclean = cleandata.Clean(s3scry, s3json, **yaml0['get_date']['merge_all'])
        mergeraw = cclean.merge_all()
        dgee = cclean.for_gee()
        dkmean = cclean.for_kmeans()

        kcenter1, kmdf0, score1 = clustering.run_kmeans(dkmean, **yaml0['clustering']['run_kmeans'])
        rdf0, rmodel0 = regression.run_reg(dgee, modeltype='gee', **yaml0['regression']['run_reg'])
        rdf1, rmodel1 = regression.run_reg(dkmean, modeltype='linear', **yaml0['regression']['run_reg'])

        # save model to s3
        s3tofrom.model_save(rmodel0, s3pathfile='chmodel/gee.joblib', bucket="2021-msia423-ke-chenghao")
        s3tofrom.model_save(rmodel1, s3pathfile='chmodel/ols.joblib', bucket="2021-msia423-ke-chenghao")

    elif sp_used == 'sqlempty':
        m423.create_db(args.engine_string)
    else:
        parser.print_help()



