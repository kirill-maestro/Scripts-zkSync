from web3 import Web3
import os
import json
from utils.transaction_utils import sign_transaction, send_raw_transaction, wait_for_transaction_finish, approve, get_amount_wei
from zkSyncData import ZKSYNC_TOKENS, WOOFI_CONTRACT

# Loading the ABIs of the syncswap contracts
abi_path_router = os.path.join(
    os.path.dirname(__file__), "abis/woofi/router.json")
with open(abi_path_router, "r") as file:
    WOOFI_ROUTER_ABI = json.load(file)

GAS_MULTIPLIER = 1.01


def woofi_swap(private_key, amount, from_token, to_token, slippage):
    # Connect to the Ethereum network -> put your own RPC URL here
    w3 = Web3(Web3.HTTPProvider(
        "https://rpc.ankr.com/zksync_era/"))

    # Load the private key and get the account
    account = w3.eth.account.from_key(private_key)

    # Set the default account
    w3.eth.default_account = account.address

    # Create the contract instance using the ABI and contract address
    contract_address = WOOFI_CONTRACT['router']

    contract_swap = w3.eth.contract(
        address=contract_address, abi=WOOFI_ROUTER_ABI)

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

    # Get the minimum amount out -> this is the minimum amount of the 'to_token' that will be received

    def get_min_amount_out(from_token: str, to_token: str, amount: int, slippage: float):
        min_amount_out = contract_swap.functions.querySwap(
            Web3.to_checksum_address(from_token),
            Web3.to_checksum_address(to_token),
            amount
        ).call()
        return int(min_amount_out - (min_amount_out / 100 * slippage))

    def swap():
        try:
            print(
                f"[{account.address}] Swap on WooFi: {from_token} -> {to_token} | {amount} {from_token}")

            if from_token == "ETH":
                from_token_address = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"
                to_token_address = Web3.to_checksum_address(
                    ZKSYNC_TOKENS[to_token])
                transaction.update({"value": amount_wei})
            else:
                from_token_address = Web3.to_checksum_address(
                    ZKSYNC_TOKENS[from_token])
                to_token_address = "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE"

                approve(amount_wei, from_token_address,
                        WOOFI_CONTRACT["router"], account, w3)
                transaction.update(
                    {"nonce": w3.eth.get_transaction_count(account.address)})

            min_amount_out = get_min_amount_out(
                from_token_address, to_token_address, amount_wei, slippage)

            contract_transaction = contract_swap.functions.swap(
                from_token_address,
                to_token_address,
                amount_wei,
                min_amount_out,
                account.address,
                account.address
            ).build_transaction(transaction)

            try:
                signed_transaction = sign_transaction(
                    contract_transaction, w3, private_key, GAS_MULTIPLIER)
            except Exception as error:
                print(f"sign_transaction failed | {error}")

            transaction_hash = send_raw_transaction(signed_transaction, w3)

            wait_for_transaction_finish(transaction_hash.hex(), account, w3)
            print(
                f"[{account.address}] WooFi swaped [{amount}] [{from_token}] to [{to_token}]")

        except Exception as error:
            print(f"❌ WooFi swap failed [{account.address}] {error}")
    swap()


def main():
    # SETTINGS START HERE:
    amount = 1  # How much of from_token do you want to swap?
    from_token = 'USDC'  # ETH, WETH, WBTC, USDT, USDC, BUSD, MATIC available
    to_token = 'ETH'  # ETH, WETH, WBTC, USDT, USDC, BUSD, MATIC available
    slippage = 1  # The slippage tolerance in percentage
    # SETTINGS END HERE

    with open('keys.txt', 'r') as file:
        for private_key in file:
            private_key = private_key.strip()
            woofi_swap(private_key, amount, from_token, to_token, slippage)


main()
