from web3 import Web3
import os
import json
import time
from web3.exceptions import TransactionNotFound
from eth_abi import abi

SYNCSWAP_CONTRACT = {
    "router": "0x2da10A1e27bF85cEdD8FFb1AbBe97e53391C0295",
    "classic_pool": "0xf2DAd89f2788a8CD54625C60b55cD3d2D0ACa7Cb"
}

ZKSYNC_TOKENS = {
    "ETH": "0x5aea5775959fbc2557cc8789bc1bf90a239d9a91",
    "WETH": "0x5aea5775959fbc2557cc8789bc1bf90a239d9a91",
    "USDC": "0x3355df6D4c9C3035724Fd0e3914dE96A5a83aaf4",
    "USDT": "0x493257fd37edb34451f62edf8d2a0c418852ba4c",
    "BUSD": "0x2039bb4116b4efc145ec4f0e2ea75012d6c0f181",
    "MATIC": "0x28a487240e4d45cff4a2980d334cc933b7483842",
    "OT": "0xd0ea21ba66b67be636de1ec4bd9696eb8c61e9aa",
    "MAV": "0x787c09494ec8bcb24dcaf8659e7d5d69979ee508",
    "WBTC": "0xbbeb516fb02a01611cbbe0453fe3c580d7281011",
}

abi_path_router = os.path.join(os.path.dirname(__file__), "abis/syncswap/router.json")
with open(abi_path_router, "r") as file:
    SYNCSWAP_ROUTER_ABI = json.load(file)

abi_path_pool = os.path.join(os.path.dirname(__file__), "abis/syncswap/classic_pool.json")
with open(abi_path_pool, "r") as file:
    SYNCSWAP_CLASSIC_POOL_ABI = json.load(file)

abi_path_pool = os.path.join(os.path.dirname(__file__), "abis/syncswap/classic_pool_data.json")
with open(abi_path_pool, "r") as file:
    SYNCSWAP_CLASSIC_POOL__DATA_ABI = json.load(file)

abi_erc_20 = os.path.join(os.path.dirname(__file__), "abis/syncswap/ABI_erc20.json")
with open(abi_erc_20, "r") as file:
    ERC_20_ABI = json.load(file)

GAS_MULTIPLIER = 1.01

def syncswap_swap(private_key, amount, chain, from_token, to_token):
    # Connect to the Ethereum network -> put your own RPC URL here
    w3 = Web3(Web3.HTTPProvider("https://rpc.ankr.com/zksync_era/72e6ee41b6e696261935e39b2b12db5cea4009c7e931c7d23f47f3d180656f2b"))

    # Load the private key and get the account
    account = w3.eth.account.from_key(private_key)

    # Set the default account
    w3.eth.default_account = account.address

    # Create the contract instance using the ABI and contract address
    contract_address = SYNCSWAP_CONTRACT['router']
    
    contract_swap = w3.eth.contract(address=contract_address, abi=SYNCSWAP_ROUTER_ABI)

    # Convert amount to wei format
    amount_wei = w3.to_wei(amount, 'ether')
    
    def sign(transaction):
        gas = w3.eth.estimate_gas(transaction)
        gas = int(gas * GAS_MULTIPLIER)

        transaction.update({"gas": gas})

        signed_txn = w3.eth.account.sign_transaction(transaction, private_key)

        return signed_txn
    
    def send_raw_transaction(signed_txn):
        txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)

        return txn_hash
    
    def get_contract(contract_address: str, abi=None):
        contract_address = Web3.to_checksum_address(contract_address)

        if abi is None:
            abi = ERC_20_ABI

        contract = w3.eth.contract(address=contract_address, abi=abi)

        return contract
    
    def wait_until_tx_finished(hash: str, max_wait_time=180):
        start_time = time.time()
        while True:
            try:
                receipts = w3.eth.get_transaction_receipt(hash)
                status = receipts.get("status")
                if status == 1:
                    print(f"[{account.address}] {hash} successfully!")
                    return True
                elif status is None:
                    time.sleep(0.3)
                else:
                    print(f"[{account.address}] {hash} failed!")
                    return False
            except TransactionNotFound:
                if time.time() - start_time > max_wait_time:
                    print(f'FAILED TX: {hash}')
                    return False
                time.sleep(1)

    def check_allowance(token_address: str, contract_address: str) -> float:
        token_address = Web3.to_checksum_address(token_address)
        contract_address = Web3.to_checksum_address(contract_address)

        contract = w3.eth.contract(address=token_address, abi=ERC_20_ABI)
        amount_approved = contract.functions.allowance(account.address, contract_address).call()

        return amount_approved

    def approve(amount: float, token_address: str, contract_address: str):
        token_address = Web3.to_checksum_address(token_address)
        contract_address = Web3.to_checksum_address(contract_address)

        contract = w3.eth.contract(address=token_address, abi=ERC_20_ABI)

        allowance_amount = check_allowance(token_address, contract_address)

        if amount > allowance_amount or amount == 0:
            print(f"Success [{account.address}] Make approve")

            approve_amount = 2 ** 128 if amount > allowance_amount else 0

            tx = {
                "chainId": w3.eth.chain_id,
                "from": account.address,
                "nonce": w3.eth.get_transaction_count(account.address),
                "gasPrice": w3.eth.gas_price
            }

            transaction = contract.functions.approve(
                contract_address,
                approve_amount
            ).build_transaction(tx)

            signed_txn = sign(transaction)

            txn_hash = send_raw_transaction(signed_txn)

            wait_until_tx_finished(txn_hash.hex())

            time.sleep(5)


    # Get the gas price
    gas_price = w3.eth.gas_price

    # Construct the transaction
    transaction = {
        'chainId': 324,  # Replace with the desired chain ID
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gasPrice': gas_price,
    }

    # Get the pool address -> this is the address of the pool that will be used for the swap
    def get_pool(from_token: str, to_token: str):
            contract_get_pool = get_contract(SYNCSWAP_CONTRACT["classic_pool"], SYNCSWAP_CLASSIC_POOL_ABI)

            pool_address = contract_get_pool.functions.getPool(
                Web3.to_checksum_address(ZKSYNC_TOKENS[from_token]),
                Web3.to_checksum_address(ZKSYNC_TOKENS[to_token])
            ).call()

            return pool_address
    
    # Get the minimum amount out -> this is the minimum amount of the 'to_token' that will be received
    def get_min_amount_out(pool_address: str, token_address: str, amount: int, slippage: float):
        pool_contract = get_contract(pool_address, SYNCSWAP_CLASSIC_POOL__DATA_ABI)
        min_amount_out = pool_contract.functions.getAmountOut(
            token_address,
            amount,
            account.address
        ).call()
        return int(min_amount_out - (min_amount_out / 100 * slippage))
    

    def swap(
            w3,
            from_token: str,
            to_token: str,
            slippage: float
    ):
        token_address = Web3.to_checksum_address(ZKSYNC_TOKENS[from_token])

        pool_address = get_pool(from_token, to_token)

        if pool_address != "0x0000000000000000000000000000000000000000":
            if from_token == "ETH":
                transaction.update({"value": amount_wei})
            else:
                approve(amount_wei, token_address, Web3.to_checksum_address(SYNCSWAP_CONTRACT["router"]))
                transaction.update({"nonce": w3.w3.eth.get_transaction_count(account.address)})

            min_amount_out = get_min_amount_out(pool_address, token_address, amount_wei, slippage)

            steps = [{
                "pool": pool_address,
                "data": abi.encode(["address", "address", "uint8"], [token_address, account.address, 1]),
                "callback": "0x0000000000000000000000000000000000000000",
                "callbackData": "0x"
            }]

            paths = [{
                "steps": steps,
                "tokenIn": "0x0000000000000000000000000000000000000000" if from_token == "ETH" else token_address,
                "amountIn": amount_wei
            }]

            deadline = int(time.time()) + 1000000

            contract_txn = contract_swap.functions.swap(
                paths,
                min_amount_out,
                deadline
            ).build_transaction(transaction)

            signed_txn = sign(contract_txn)

            txn_hash = send_raw_transaction(signed_txn)

            wait_until_tx_finished(txn_hash.hex())
        else:
            print(f"[{account.address}] Swap path {from_token} to {to_token} not found!")

    swap(w3, from_token, to_token, amount)


# Example usage
private_key = '-'
amount = 0.0001
chain = 'mainnet'
from_token = 'ETH'
to_token = 'USDC'

syncswap_swap(private_key, amount, chain, from_token, to_token)
