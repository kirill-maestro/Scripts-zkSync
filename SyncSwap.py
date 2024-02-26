from web3 import Web3
import os
import json
import time
from eth_abi import abi
from utils.transaction_utils import sign_transaction, send_raw_transaction, get_contract, wait_for_transaction_finish, approve, get_amount_wei
from zkSyncData import ZKSYNC_TOKENS, SYNCSWAP_CONTRACT, ZERO_ADDRESS

# Loading the ABIs of the syncswap contracts
abi_path_router = os.path.join(os.path.dirname(
    __file__), "abis/syncswap/router.json")
with open(abi_path_router, "r") as file:
    SYNCSWAP_ROUTER_ABI = json.load(file)

abi_path_pool = os.path.join(os.path.dirname(
    __file__), "abis/syncswap/classic_pool.json")
with open(abi_path_pool, "r") as file:
    SYNCSWAP_CLASSIC_POOL_ABI = json.load(file)

abi_path_pool = os.path.join(os.path.dirname(
    __file__), "abis/syncswap/classic_pool_data.json")
with open(abi_path_pool, "r") as file:
    SYNCSWAP_CLASSIC_POOL__DATA_ABI = json.load(file)

GAS_MULTIPLIER = 1.01


def syncswap_swap(private_key, amount, from_token, to_token, slippage=1):
    # Connect to the Ethereum network -> put your own RPC URL here
    w3 = Web3(Web3.HTTPProvider(
        "https://rpc.ankr.com/zksync_era/"))

    # Load the private key and get the account
    account = w3.eth.account.from_key(private_key)

    # Create the contract instance using the ABI and contract address
    contract_address = SYNCSWAP_CONTRACT['router']

    contract_swap = w3.eth.contract(
        address=contract_address, abi=SYNCSWAP_ROUTER_ABI)

    # Convert amount to wei format (depending on the token decimal, e.g. USDC has 6 decimals and ETH has 18 decimals)
    amount_wei = get_amount_wei(from_token, w3, account, amount)

    # Get the gas price
    gas_price = w3.eth.gas_price

    # Construct the transaction
    transaction = {
        'chainId': w3.eth.chain_id,
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gasPrice': gas_price,
    }

    # Get the pool address -> this is the address of the pool that will be used for the swap
    def get_pool(from_token: str, to_token: str):
        contract_get_pool = get_contract(
            SYNCSWAP_CONTRACT["classic_pool"], w3, SYNCSWAP_CLASSIC_POOL_ABI)

        pool_address = contract_get_pool.functions.getPool(
            Web3.to_checksum_address(ZKSYNC_TOKENS[from_token]),
            Web3.to_checksum_address(ZKSYNC_TOKENS[to_token])
        ).call()

        return pool_address

    # Get the minimum amount out -> this is the minimum amount of the 'to_token' that will be received
    def get_min_amount_out(pool_address: str, token_address: str, amount: int, slippage: float):
        pool_contract = get_contract(
            pool_address, w3, SYNCSWAP_CLASSIC_POOL__DATA_ABI)
        min_amount_out = pool_contract.functions.getAmountOut(
            token_address,
            amount,
            account.address
        ).call()
        return int(min_amount_out - (min_amount_out / 100 * slippage))

    def swap():
        token_address = Web3.to_checksum_address(ZKSYNC_TOKENS[from_token])

        pool_address = get_pool(from_token, to_token)

        if pool_address != ZERO_ADDRESS:
            if from_token == "ETH":
                transaction.update({"value": amount_wei})
            else:
                approve(amount_wei, token_address, Web3.to_checksum_address(
                    SYNCSWAP_CONTRACT["router"]), account, w3)
                transaction.update(
                    {"nonce": w3.w3.eth.get_transaction_count(account.address)})

            min_amount_out = get_min_amount_out(
                pool_address, token_address, amount_wei, slippage)

            steps = [{
                "pool": pool_address,
                "data": abi.encode(["address", "address", "uint8"], [token_address, account.address, 1]),
                "callback": ZERO_ADDRESS,
                "callbackData": "0x"
            }]

            paths = [{
                "steps": steps,
                "tokenIn": ZERO_ADDRESS if from_token == "ETH" else token_address,
                "amountIn": amount_wei
            }]

            deadline = int(time.time()) + 1000000

            contract_transaction = contract_swap.functions.swap(
                paths,
                min_amount_out,
                deadline
            ).build_transaction(transaction)

            signed_transaction = sign_transaction(
                contract_transaction, w3, private_key, GAS_MULTIPLIER)

            transaction_hash = send_raw_transaction(signed_transaction, w3)

            wait_for_transaction_finish(transaction_hash.hex(), account, w3)
            print(f"[{account.address}] swaped from amount [{amount}] [{from_token}] to [{to_token}]")
        else:
            print(
                f"[{account.address}] Swap path [{from_token}] to [{to_token}] not found!")

    swap()

def main():
    # SETTINGS START HERE:
    amount = 0.0001  # How much of from_token do you want to bridge?
    from_token = 'ETH' # ETH, WETH, WBTC, USDT, USDC, BUSD, MATIC available
    to_token = 'USDC' # ETH, WETH, WBTC, USDT, USDC, BUSD, MATIC available
    slippage = 1  # The slippage tolerance in percentage
    # SETTINGS END HERE

    with open('keys.txt', 'r') as file:
        for private_key in file:
            private_key = private_key.strip()
            syncswap_swap(private_key, amount, from_token, to_token, slippage)


main()
