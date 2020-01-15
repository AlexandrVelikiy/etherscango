#!/usr/bin/python3
# -*- coding: utf-8 -*-
from models import  Withdrawals, connect_to_db
import logging
import time, os
from Crypto.Cipher import AES
from base64 import b64decode
import json
from web3.auto import w3
from web3 import Web3, HTTPProvider

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

out_wallet=Web3.toChecksumAddress(OUT_WALLET)
out_nonce=0
w3 = Web3(HTTPProvider(ETH_NODE))

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


def chek_receipt_transaction():
    try:
        global hashes
        if len(hashes) > 0:
            logger.info(f'Waiting for  transactions receitps for {len(hashes)} transactions ....')
            p = True

            try:
                while p:
                    for h in hashes:
                        if not w3.eth.getTransactionReceipt(h):

                            # тут удаляем эту транзакцию из списка ожидания
                            hashes.pop(h)

                            p = True
                            break
                        else:
                            p = False
                    time.sleep(10)
            except:
                logger.exception('Waiting for eth transactions')

    except:
        logger.exception('chek_receipt_transaction')

def send_wtp_tokens():
    global out_nonce

    r = w3.eth.getTransactionReceipt('0x538732ad1a4ca17069730ef068b281555da0d983e790bc3cbb029f31851af3d0')

    out_nonce = w3.eth.getTransactionCount(out_wallet)
    logger.info(f'out_wallet nouce {out_nonce}')

    hashes=[]
    pending=[]

    contract_address=Web3.toChecksumAddress(CONTRACT_ADD)

    try:
        contract_abi = json.loads(open(ABI_FILE_PATH,"r").read())
    except:
        logger.info(f'ABI file {ABI_FILE_PATH} not found')
        return False

    contract = w3.eth.contract(address=contract_address, abi=contract_abi)

    session = connect_to_db(SQLALCHEMY_DATABASE_URI)

    withdrawals = session.query(Withdrawals).filter(Withdrawals.status == 0).all()
    logger.info(f'In table Withdrawals found {len(withdrawals)} wallets')

    try:
        for i, w in enumerate(withdrawals):
            time.sleep(TIME_OUT)

            logger.info(f'Send {w.amount} WTP tokens to {w.wallet} ...')
            nonce = w3.eth.getTransactionCount(Web3.toChecksumAddress(out_wallet))

            txn = contract.functions.transferFrom(
                Web3.toChecksumAddress(out_wallet),
                Web3.toChecksumAddress(w.wallet),
                #int(w.amount),
                int(1),
            ).buildTransaction({
                'chainId': 1,
                'gas': 100000,
                'gasPrice': w3.toWei(ETH_FEE, 'gwei'),
                'nonce': nonce,
            })
            signed_txn = w3.eth.account.signTransaction(txn, private_key=OUT_PRIVKEY)

            try:
                txhash = w3.eth.sendRawTransaction(signed_txn.rawTransaction)
            except:
                logger.exception('sendRawTransaction')

            # ставим  pending и сохраням txhash
            w.pending = 1
            w.txhash = txhash
            session.commit()
            hashes.append(txhash)

        # проверяем отправились ли транзакции
        res = chek_receipt_transaction()



    except:
        logger.exception('send wtp')



if __name__ == '__main__':
    send_wtp_tokens()