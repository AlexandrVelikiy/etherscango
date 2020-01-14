# -*- coding: utf-8 -*-

# config
MASTERPASS="JL5rslduQE3c38od"
ETH_NODE ='https://mainnet.infura.io/ca7647192cca4daf8193b9bae3921910'
ABI_FILE_PATH = 'json.abi'


CONTRACT_ADD = '0x1680CfdAD75dA2bb56Ded4f36BB9423C86ffa7B7'

COLD_WALLET = '0x525c9e7c5cec37adfcddf2c70eea25dfa6004693'

OUT_WALLET = '0x85567eb0322d392b1E3946fBAbC42f42617381b4'
OUT_PRIVKEY='56b4d4015d2b221740bc11f1149bd1491f3382122fabab6e9f2e079f8387f384'

ETH_FEE = 3

DEBUG = True
TOKEN = '5UZG48NFB3PF1SCU83V2I9UXEHKHSRQYFT'

TIME_OUT = 0.25 # ограничим не более 4-х запросов в секунду
TIME_OUT_AFTER_HTTPERROR_429 = 45 # пауза после ошибки

SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://alex:passw0rd159@localhost/wtp_mining'
#путь к лог файлу
LOG_PATH = '/home/alex/proj/etherscango/tokensend_bot.log'