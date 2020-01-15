#!/usr/bin/python3
# -*- coding: utf-8 -*-
from models import Wallets,Incoming, User_wallets, connect_to_db
import logging
import time, os
from Crypto.Cipher import AES
from base64 import b64decode, b64encode
import json
from requests.exceptions import HTTPError
from web3.auto import w3
from web3 import Web3, HTTPProvider, IPCProvider

from config import DEBUG,CONTRACT_ADD, TIME_OUT, SQLALCHEMY_DATABASE_URI,LOG_PATH, ETH_NODE, \
                    OUT_WALLET, OUT_PRIVKEY, ETH_FEE, COLD_WALLET,ABI_FILE_PATH, MASTERPASS,TIME_OUT_AFTER_HTTPERROR_429

logger = logging.getLogger(__file__)
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(LOG_PATH)
fh.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
if DEBUG:
    formatter = logging.Formatter('[LINE:%(lineno)d]#%(asctime)s: %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
else:
    formatter = logging.Formatter('%(asctime)s: %(message)s')

fh.setFormatter(formatter)
logger.addHandler(fh)


cold_wallet=Web3.toChecksumAddress(COLD_WALLET)
out_wallet=Web3.toChecksumAddress(OUT_WALLET)

w3 = Web3(HTTPProvider(ETH_NODE))
out_nonce=0


def str_to_bytes(data):
    u_type = type(b''.decode('utf8'))
    if isinstance(data, u_type):
        return data.encode('utf8')
    return data

def _pad(s):
    bs=16
    return s + (bs - len(s) % bs) * str_to_bytes(chr(bs - len(s) % bs))

def _unpad(s):
    return s[:-ord(s[len(s)-1:])]


def decrypt(enc, password):
    salt, iv, payload = b64decode(enc).decode().split("-")
    key = salt+password
    enc = b64decode(payload)
    cipher = AES.new(key.encode(), AES.MODE_CBC, iv.encode())
    data=cipher.decrypt(enc)
    return _unpad(data.decode())



def send_eth(wallet):
    # пополняем кошелек ефиром
    global out_nonce
    balance=w3.eth.getBalance(out_wallet)
    if balance<w3.toWei(ETH_FEE*21000, 'gwei'):
        logger.info("Not enough Ether on hot wallet")
        return False
    else:
        signed_txn = w3.eth.account.signTransaction(dict(
            nonce=out_nonce,
            gasPrice=w3.toWei(3, 'gwei'),
            gas=21000,
            to=w3.toChecksumAddress(wallet),
            value=w3.toWei(ETH_FEE*100000, 'gwei'),
            data=b'',
            ),
            OUT_PRIVKEY,
        )
        txhash=w3.eth.sendRawTransaction(signed_txn.rawTransaction)
        logger.info(txhash.hex())
        out_nonce=out_nonce+1
        return txhash

def send_wtp_tokens():

    global out_nonce

    out_nonce=w3.eth.getTransactionCount(out_wallet)
    logger.info(f'out_wallet nouce {out_nonce}')

    hashes=[]
    pending=[]

    contract_address=Web3.toChecksumAddress(CONTRACT_ADD)

    contract_abi=json.loads(open(ABI_FILE_PATH,"r").read())
    contract=w3.eth.contract(address=contract_address, abi=contract_abi)


    session = connect_to_db(SQLALCHEMY_DATABASE_URI)

    #wallets = session.query(User_wallets).filter(Incoming.status==0).all()

    wallets = session.query(User_wallets).all()
    logger.info(f'In table User_wallets found {len(wallets)} wallets')

    for i, w in enumerate(wallets) :
        time.sleep(TIME_OUT)
        # если баланс WTP токенов 0 то пропускаем этот кошелек
        logger.info(f'~Check {i+1} wallet {w.wallet}')
        try:
            token_balance = contract.functions.balanceOf(Web3.toChecksumAddress(w.wallet)).call()
        except HTTPError:
            logger.info(f'HTTPERROR_429, pause {TIME_OUT_AFTER_HTTPERROR_429} c...')
            time.sleep(TIME_OUT_AFTER_HTTPERROR_429)
            continue
        except:
            logger.info(f'wallet {w.wallet} not correct, skipping')
            continue


        if token_balance < 0.01:
            logger.info(f'Wallet: {w.wallet} no balance WTP token')
            continue


        logger.info(f'Wallet: {w.wallet} balance WTP token {token_balance}')

        balance = w3.eth.getBalance(Web3.toChecksumAddress(w.wallet))
        logger.info(f"Eth balance: {balance}")

        # проверяет баланс эфира, если достаточно то можно отправить токены
        if balance < w3.toWei(ETH_FEE * 100000, 'gwei'):
            logger.info(f"Not enough ETH on wallet {w.wallet}. sending ether from hot wallet.")
            txhash = send_eth(w.wallet)
            if txhash:
                # тут можно вынести в отдельый воркер
                logger.info(f"tx hash: {txhash.hex()}")
                hashes.append(txhash)
                pending.append(w)
            else:
                continue
        else:
            #token_balance = contract.functions.balanceOf(Web3.toChecksumAddress(w.wallet)).call()

            logger.info(f'Send {token_balance} tokens to cold wallet .....')
            nonce = w3.eth.getTransactionCount(Web3.toChecksumAddress(w.wallet))
            # получаем ключ для нашего кошелька
            try:
                wall_from_db= session.query(Wallets).filter(Wallets.wallet==w.wallet).one()
            except:
                logger.info(f'not found wallet password for {w.wallet}')
                continue

            privkey = decrypt(wall_from_db.privkey, MASTERPASS) # пароль из wallets  не подходит по длине

            txn = contract.functions.transfer(
                Web3.toChecksumAddress(cold_wallet),
                int(token_balance),
            ).buildTransaction({
                'chainId': 1,
                'gas': 100000,
                'gasPrice': w3.toWei(ETH_FEE, 'gwei'),
                'nonce': nonce,
            })
            signed_txn = w3.eth.account.signTransaction(txn, private_key=privkey)
            txhash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)

            logger.info(f'Transaction {txhash.hex()} send...')


    # тут обрабатываем транзакции где не хватило ефира для отправки если такие есть

    if len(hashes)>0:
        logger.info(f'Waiting for eth transactions receitps for {len(hashes)} transactions ....')
        p=True

        try:
            while p:
                for h in hashes:
                    if not w3.eth.getTransactionReceipt(h):
                        p=True
                        break
                    else:
                        p=False
                time.sleep(10)
        except:
            logger.exception('Waiting for eth transactions')

        logger.info('Eth transactions completed')

        logger.info("Sending tokens from left wallets..")

        for w in pending:
            time.sleep(TIME_OUT)
            token_balance = contract.functions.balanceOf(Web3.toChecksumAddress(w.wallet)).call()
            nonce = w3.eth.getTransactionCount(Web3.toChecksumAddress(w.wallet))
            logger.info(f'Send {token_balance} tokens to cold wallet .....')
            # получаем ключ для нашего кошелька
            try:
                wall_from_db = session.query(Wallets).filter(Wallets.wallet == w.wallet).one()
            except:
                logger.info(f'not found wallet password for {w.wallet}')
                continue

            privkey = decrypt(wall_from_db.privkey, MASTERPASS)

            txn = contract.functions.transfer(
                Web3.toChecksumAddress(cold_wallet),
                int(token_balance),
            ).buildTransaction({
                'chainId': 1,
                'gas': 100000,
                'gasPrice': w3.toWei(ETH_FEE, 'gwei'),
                'nonce': nonce,
            })
            signed_txn = w3.eth.account.signTransaction(txn, private_key=privkey)
            txhash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
            logger.info(f"txhash: {txhash.hex()}")

    logger.info('all transaction completed')



if __name__ == '__main__':
    send_wtp_tokens()