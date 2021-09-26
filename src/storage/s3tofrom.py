import io
import logging.config
import joblib
import aiohttp
import pandas as pd
import boto3
from botocore.exceptions import ParamValidationError, ClientError


logger = logging.getLogger(__name__)
logger.setLevel("INFO")


def to_s3(df, customname='raw_data1', bucket="2021-msia423-ke-chenghao",
          aws_access_key_id='', aws_secret_access_key=''):
    """
        Function to insert a pandas dataframe into S3
        Args:
            df (dataframe): dataframe
            customname (string): name of the object in S3
            bucket (string): bucket name
            aws_access_key_id (string): the AWS_ACCESS_KEY_ID if needed
            aws_secret_access_key (string): the AWS_SECRET_ACCESS_KEY if needed
    """
    if '/' not in customname:
        # add default folder if user doesn't add one to custom item name
        folder = 'chrawdata/'
    else:
        folder = ''
    try:
        df.to_csv('s3://{0}/{1}'.format(bucket, folder) + customname, index=False, encoding='utf_8_sig')
        logging.info('Item {0} has been created inside bucket {1}'. format(customname, bucket))
    except (ClientError, ParamValidationError, aiohttp.client_exceptions.ClientConnectorCertificateError):
        try:
            df.to_csv('s3://{0}/{1}'.format(bucket, folder) + customname, index=False, encoding='utf_8_sig',
                      storage_options={"key": aws_access_key_id, "secret": aws_secret_access_key})
        except (ClientError, ParamValidationError, aiohttp.client_exceptions.ClientConnectorCertificateError) as e:
            logging.error('Error with S3 credentials: {}'.format(e))


def from_s3(s3pathfile='chrawdata/raw_data1', bucket="2021-msia423-ke-chenghao",
            aws_access_key_id='', aws_secret_access_key=''):
    """
        Function to read csv object from S3 into Python as a Pandas dataframe
        Args:
            s3pathfile (string): path and name of the s3 object to read into Python
            bucket (string): bucket name
            aws_access_key_id (string): the AWS_ACCESS_KEY_ID if needed
            aws_secret_access_key (string): the AWS_SECRET_ACCESS_KEY if needed
        Returns:
            Pandas dataframe
    """
    try:
        df0 = pd.read_csv('s3://{}/'.format(bucket) + s3pathfile)
        return df0
    except (ClientError, ParamValidationError, aiohttp.client_exceptions.ClientConnectorCertificateError):
        try:
            df0 = pd.read_csv('s3://{}/'.format(bucket) + s3pathfile,
                              storage_options={"key": aws_access_key_id, "secret": aws_secret_access_key})
            return df0
        except (ClientError, ParamValidationError, aiohttp.client_exceptions.ClientConnectorCertificateError) as e:
            print(e)
            print('Invalid bucket name!')
            logging.error('Invalid bucket name: {}'.format(bucket))


def delete_s3obj(delobj='chrawdata/raw_data1', bucket="2021-msia423-ke-chenghao"):
    """
        Function to delete an object inside S3
        Args:
            delobj (string): path and name of the S3 object to be deleted
            bucket (string): name of the bucket
    """
    s3 = boto3.client("s3")
    s3.delete_object(Bucket=bucket, Key=delobj)
    logger.info("S3 {0} item from bucket {1} has been deleted (Note: this code will run successfully even if "
                "the wrong object name is given!".format(delobj, bucket))


def model_save(modelobj, s3pathfile='chmodel/gee.joblib', bucket="2021-msia423-ke-chenghao"):
    """
        Function to insert a statistical model object into S3
        Args:
            modelobj (obj): a statistical model object
            s3pathfile (string): name of the object in S3
            bucket (string): bucket name
    """
    with io.BytesIO() as f:
        joblib.dump(modelobj, f)
        f.seek(0)
        boto3.client("s3").upload_fileobj(Bucket=bucket, Key=s3pathfile, Fileobj=f)
    logger.info('Model successfully saved {}'.format(s3pathfile))


def model_load(s3pathfile='chmodel/gee.joblib', bucket="2021-msia423-ke-chenghao"):
    """
        Function to load a statistical model object from S3
        Args:
            s3pathfile (string): name of the object in S3
            bucket (string): bucket name
        Returns:
            Statistical model object
    """
    with io.BytesIO() as f:
        boto3.client("s3").download_fileobj(Bucket=bucket, Key=s3pathfile, Fileobj=f)
        f.seek(0)
        modelfile = joblib.load(f)
        logger.info('Model successfully loaded {}'.format(s3pathfile))
        return modelfile


if __name__ == '__main__':
    dftest = pd.DataFrame([1, 2, 3, 4, 5])
    to_s3(dftest)
    x0 = from_s3()
    print(x0)
    delete_s3obj()

    # CH notes to self
    # bucket = s3.Bucket(bucket)
    pass
