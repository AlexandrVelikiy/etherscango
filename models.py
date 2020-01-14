# -*- coding: utf-8 -*-
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Integer, String, MetaData, Boolean, Float, DateTime, CHAR
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import  logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
Base = declarative_base()

class User_wallets(Base):
    __tablename__ = 'user_wallets'
    id = Column('id', Integer, primary_key=True)
    user_id = Column('user_id', Integer)
    balance = Column('balance', Float)
    wallet = Column('wallet', String)

class Incoming(Base):
    __tablename__ = 'incoming'
    id = Column('id', Integer, primary_key=True)
    user_id = Column('user_id', Integer)
    wallet = Column('wallet', String)
    amount = Column('amount', Float)
    txhash = Column('txhash', String)
    type = Column('type', Integer)
    viewed = Column('viewed', Integer)
    bot = Column('bot', Integer)
    status = Column('status', Integer)
    created_at = Column('created_at', DateTime)
    updated_at = Column('updated_at', DateTime)

class Wallets(Base):
    __tablename__ = 'wallets'
    id = Column('id', Integer, primary_key=True)
    wallet = Column('wallet', String)
    privkey = Column('privkey', String)
    passwd = Column('passwd', String)
    currency = Column('currency', String(4))
    status = Column('status', Integer)

def connect_to_db(db_url):
    try:
        _conn = create_engine(db_url,encoding='utf8')
        _metadata = MetaData()
        _metadata.reflect(bind=_conn)
        Base.metadata.create_all(_conn)
        Session = sessionmaker(bind=_conn)
        return Session()
    except Exception as e:
        logger.exception(e)