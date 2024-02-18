# This file contains the basic web3 functions to sign and send transactions, as well as to check the status of a transaction and to approve a token.

from web3 import Web3
import os
import json
import time
from web3.exceptions import TransactionNotFound

# Loading fallbalck abi for ERC20
abi_erc_20 = os.path.join(os.path.dirname(__file__), "../abis/syncswap/ABI_erc20.json")
with open(abi_erc_20, "r") as file:
    ERC_20_ABI = json.load(file)

# The function to sign a transaction
def sign_transaction(transaction, w3, private_key, GAS_MULTIPLIER):
    gas = int(w3.eth.estimate_gas(transaction) * GAS_MULTIPLIER)
    transaction.update({"gas": gas})

    signed_transaction = w3.eth.account.sign_transaction(transaction, private_key)

    return signed_transaction

# The function to send a raw transaction (broadcasting the signed transaction to the network for processing)
def send_raw_transaction(signed_transaction, w3):
    transaction_hash = w3.eth.send_raw_transaction(signed_transaction.rawTransaction)

    return transaction_hash

# The function to check if the contract exists and if so to get contract instance or fallback to ERC20 contract
def get_contract(contract_address: str, w3, abi=None):
        contract_address = Web3.to_checksum_address(contract_address)

        if abi is None:
            abi = ERC_20_ABI

        contract = w3.eth.contract(address=contract_address, abi=abi)

        return contract

# The function to wait for the transaction to be processed, it basically helps to keep order of transaction execution 
def wait_for_transaction_finish(hash: str, account, w3, max_waiting_time=120):
    starting_time = time.time()
    while True:
        try:
            transaction_receipts = w3.eth.get_transaction_receipt(hash)
            transaction_status = transaction_receipts.get("status")
            
            if transaction_status == 1:
                print(f"✅ [{account.address}] {hash} successfully!")
                return True
            
            elif transaction_status is None:
                time.sleep(1)
            
            else:
                print(f"❌ [{account.address}] {hash} failed!")
                return False
            
        except TransactionNotFound:
            if time.time() - starting_time > max_waiting_time:
                print(f"❓ [{account.address}] transaction not found: {hash}")
                return False
            time.sleep(1)

# The function to check the allowance to contract of a token
def check_token_allowance(token_address: str, contract_address: str, account, w3) -> float:
    token_address = Web3.to_checksum_address(token_address)
    contract_address = Web3.to_checksum_address(contract_address)

    contract = w3.eth.contract(address=token_address, abi=ERC_20_ABI)
    amount_approved = contract.functions.allowance(account.address, contract_address).call()

    return amount_approved

# The function to approve a token to contract
def approve(amount: float, token_address: str, contract_address: str, account, w3):
    token_address = Web3.to_checksum_address(token_address)
    contract_address = Web3.to_checksum_address(contract_address)

    contract = w3.eth.contract(address=token_address, abi=ERC_20_ABI)

    allowance_amount = check_token_allowance(token_address, contract_address, account, w3)

    if amount > allowance_amount or amount == 0:
        print(f"🗿🗿🗿 Success [{account.address}] Make approve")

        approval_transaction = {
            "chainId": w3.eth.chain_id,
            "from": account.address,
            "nonce": w3.eth.get_transaction_count(account.address),
            "gasPrice": w3.eth.gas_price
        }

        # approving the max allowed amount to mitigate the need to approve again
        approve_amount = 2 ** 128 if amount > allowance_amount else 0

        transaction = contract.functions.approve(
            contract_address,
            approve_amount
        ).build_transaction(approval_transaction)

        signed_transaction = sign_transaction(transaction, w3, account.private_key, 1)

        transaction_hash = send_raw_transaction(signed_transaction, w3)

        wait_for_transaction_finish(transaction_hash.hex(), account, w3)

        time.sleep(10)