from web3 import Web3
import os
import json
import random
import time
from web3.exceptions import TransactionNotFound
from eth_abi import abi
from utils.transaction_utils import sign_transaction, send_raw_transaction, get_contract, wait_for_transaction_finish, approve, get_amount_wei
from zkSyncData import ZKSYNC_TOKENS, DMAIL_CONTRACT, ZERO_ADDRESS

# Loading the ABIs of the syncswap contracts
abi_path_dmail = os.path.join(os.path.dirname(__file__), "abis/dmail/dmail.json")
with open(abi_path_dmail, "r") as file:
    DMAIL_ABI = json.load(file)

GAS_MULTIPLIER = 1.01

RANDOM_RECEIVER = True

def dmail(private_key):
    # Connect to the Ethereum network -> put your own RPC URL here
    w3 = Web3(Web3.HTTPProvider("https://rpc.ankr.com/zksync_era/72e6ee41b6e696261935e39b2b12db5cea4009c7e931c7d23f47f3d180656f2b"))

    # Load the private key and get the account
    account = w3.eth.account.from_key(private_key)

    # Set the default account
    w3.eth.default_account = account.address

    # Create the contract instance using the ABI and contract address
    contract_address = DMAIL_CONTRACT['dmail']
    
    contract_send_dmail = w3.eth.contract(address=contract_address, abi=DMAIL_ABI)

    # Get the gas price
    gas_price = w3.eth.gas_price

    # Construct the transaction
    transaction = {
        'chainId': 324,  # Replace with the desired chain ID
        'from': account.address,
        'to': Web3.to_checksum_address(DMAIL_CONTRACT['dmail']),
        'nonce': w3.eth.get_transaction_count(account.address),
        'gasPrice': gas_price,
    }


    def get_random_email():
        domain_list = ["@gmail.com", "@dmail.ai"]

        domain_address = "".join(random.sample([chr(i) for i in range(97, 123)], random.randint(7, 15)))

        return domain_address + random.choice(domain_list)

    
    
    def send_mail(random_receiver: bool):
        print(f"[{account.address}] Send email")

        email_address = get_random_email() if random_receiver else f"{account.address}@dmail.ai"

        data = contract_send_dmail.encodeABI("send_mail", args=(email_address, email_address))

        transaction.update({"data": data})
        
        signed_transcation = sign_transaction(transaction, w3, private_key, GAS_MULTIPLIER)

        transaction_hash = send_raw_transaction(signed_transcation, w3)

        wait_for_transaction_finish(transaction_hash.hex(), account, w3)


    send_mail(RANDOM_RECEIVER)


# Example usage
private_key = '-'

dmail(private_key)
