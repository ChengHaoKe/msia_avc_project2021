import logging.config
import time
import sqlalchemy
import mysql.connector
import pandas as pd


try:
    from src.utils import minifuncs as minif
except ModuleNotFoundError:
    from utils import minifuncs as minif


logger = logging.getLogger(__name__)
logger.setLevel("INFO")


class MysqlAll:
    """
        Class to insert entire dataframes into a database and to query tables back into Python
        Args:
            connstring = a connection string including username, password and host
            u = username
            p = password
            db = database name
            schema = schema name within which the SQL table can be accessed / inserted
            port = an integer specifying the port
        Note:
            - if a connection string is provided, then username and password are not needed
            - if neither connection string nor username + password are provided, will default to local sqlite
    """
    def __init__(self, connstring='', u='', p='', db="msia423_db", schema='msia423_db', port=3306, isflask=False):
        self.db = db
        self.port = port
        self.sche = schema
        self.u = u
        self.p = p
        self.connstring = connstring
        self.default = 'sqlite:///data/{}.db'
        self.customengine = 'mysql+pymysql://{0}:{1}@nw-msia423-ch.cpmox8xcm0d8.us-east-2.rds.amazonaws.com/{2}'
        self.isflask = isflask

    # get connection
    def conn(self, want='cursor'):
        """
            Depending on which input is received, this function would provide a connection sqlalchemy engine or
            a mysql connection cursor.
        """

        if self.connstring != '':
            engine = sqlalchemy.create_engine(self.connstring)
            logging.info('Connection string {} received.'.format(self.connstring))
            return engine
        elif (self.u == '') and (self.p == ''):
            print('No password file, please use command line arguments! Will create default local sqlite database!')
            eng0 = self.default.format(self.db)
            if want == 'cursor':
                # Create a SQL connection to local SQLite database
                engine = sqlalchemy.create_engine(eng0)
            else:
                engine = sqlalchemy.create_engine(eng0)
            logging.info('No connection string, user name or password supplied! Defaulting to local sqlite.')
            return engine
        else:
            user = self.u
            pwd = self.p
            if want in ['cursor', 'conn', 'c']:
                # connect to mysql
                conn = mysql.connector.connect(host="nw-msia423-ch.cpmox8xcm0d8.us-east-2.rds.amazonaws.com",
                                               user=user, password=pwd, database=self.db, port=self.port)
                logging.info('Connection cursor object has been created using mysql connector')
                return conn
            else:
                eng0 = self.customengine.format(user, pwd, self.db)
                engine = sqlalchemy.create_engine(eng0)
                logging.info('Engine has been created using sqlalchemy')
                return engine

    def create_empty(self, createsql=''):
        """
            Creates an empty SQL table based on a SQL string specifying the table construction.
        """

        print("Create Table")
        cursor = self.conn(want='cursor')
        # default sample table creation sql
        if createsql == '':
            ndays = minif.ndays()

            createsql = """
                CREATE TABLE {0}.{1}
                (
                    uuid VARCHAR(255) NOT NULL,
                    mtgjsonId VARCHAR(255),
                    scryfallid VARCHAR(255) NOT NULL,
                    scryfallIllustrationId VARCHAR(255),
                    scryfallOracleId VARCHAR(255),
            """.format(self.sche, 'test1')
            dcols = ', '.join(['pd{} DECIMAL(30, 10)'.format(i) for i in range(ndays)])
            createsql = createsql + dcols + ')'

        cursor.execute(createsql)
        cursor.commit()

    def insert_df(self, df, name='raw_table', replace=False, tojson=False):
        """
            Function to insert an entire dataframe into a database
            Args:
                df (dataframe): dataframe
                name (string): name of the SQL table
                replace (bool): whether to replace the table if it exists
                tojson (bool): whether to turn all dictionary columns into json format
        """
        start_time = time.time()

        eng1 = self.conn(want='sqlalchemy')
        if replace:
            if tojson:
                df.to_sql(name, con=eng1, schema=self.sche, if_exists='replace', index=False,
                          dtype={col1: sqlalchemy.types.JSON for col1 in df})
            else:
                df.to_sql(name, con=eng1, schema=self.sche, if_exists='replace', index=False)
        else:
            if tojson:
                df.to_sql(name, con=eng1, schema=self.sche, if_exists='append', index=False,
                          dtype={col1: sqlalchemy.types.JSON for col1 in df})
            else:
                df.to_sql(name, con=eng1, schema=self.sche, if_exists='append', index=False)

        print("Insertion ran for: {0} seconds ({1} mins)".format(str(round(time.time() - start_time, 2)),
                                                                 str(round((time.time() - start_time) / 60))))
        logging.info('Table {0} has been created under schema {1} with replace as {2}. Ran for {3} seconds'
                     ''.format(name, self.sche, replace, round(time.time() - start_time, 2)))

    def read_table(self, query, want='cursor', cursor=None):
        """
            Function to read a SQL table into Python as a dataframe with the provided query
            Args:
                query = SQL query
            Returns:
                Pandas dataframe
        """

        start_time = time.time()
        if self.isflask:
            conn = cursor
        else:
            conn = self.conn(want)

        df = pd.read_sql(query, conn)
        print("Query ran for: {0} seconds ({1} mins)".format(str(round(time.time() - start_time, 2)),
                                                             str(round((time.time() - start_time) / 60))))
        logging.info('{0} query ran for {1} seconds'.format(query, round(time.time() - start_time, 2)))
        return df


if __name__ == '__main__':
    dftest = pd.DataFrame([1, 2, 3, 4, 5])

    chsql = MysqlAll()
    chsql.insert_df(dftest, 'test0')
    dft1 = chsql.read_table("SELECT * FROM msia423_db.test0")
    pass
