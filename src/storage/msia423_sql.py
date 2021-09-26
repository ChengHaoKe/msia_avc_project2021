import logging.config
import sqlalchemy
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String  # , MetaData, Integer
# from sqlalchemy.orm import sessionmaker
# from flask_sqlalchemy import SQLAlchemy


logger = logging.getLogger(__name__)
logger.setLevel("INFO")

Base = declarative_base()


class MTGSQL(Base):
    """Create a data model for the database to be set up for capturing songs
    """

    __tablename__ = 'table_created_withsqlalchemy'

    uuid = Column(String(255), primary_key=True)
    mtgjsonId = Column(String(255), nullable=True)
    scryfallid = Column(String(255), nullable=False)
    scryfallIllustrationId = Column(String(255), nullable=True)
    scryfallOracleId = Column(String(255), nullable=True)

    def __repr__(self):
        return '<Card uuid %r>' % self.uuid


def create_db(engine_string: str) -> None:
    """Create database from provided engine string
    Args:
        engine_string: str - Engine string
    Returns: None
    """
    engine = sqlalchemy.create_engine(engine_string)

    Base.metadata.create_all(engine)
    logger.info("Database created.")
