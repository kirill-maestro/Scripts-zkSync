from web3 import Web3
import os
import json
import time
from web3.exceptions import TransactionNotFound
from eth_abi import abi
from utils.transaction_utils import sign_transaction, send_raw_transaction, get_contract, wait_for_transaction_finish, approve, get_amount_wei
from zkSyncData import ZKSYNC_TOKENS, IZUMI_CONTRACT, ZERO_ADDRESS

# Loading the ABIs of the syncswap contracts
abi_path_swap = os.path.join(os.path.dirname(__file__), "abis/iZUMi/swap.json")
with open(abi_path_swap, "r") as file:
    IZUMI_SWAP_ABI = json.load(file)

abi_path_router = os.path.join(os.path.dirname(__file__), "abis/iZUMi/router.json")
with open(abi_path_router, "r") as file:
    IZUMI_ROUTER_ABI = json.load(file)

GAS_MULTIPLIER = 1.1


def iZUMi_swap(private_key, amount, from_token, to_token):

     # Connect to the Ethereum network -> put your own RPC URL here
    w3 = Web3(Web3.HTTPProvider("https://rpc.ankr.com/zksync_era/72e6ee41b6e696261935e39b2b12db5cea4009c7e931c7d23f47f3d180656f2b"))

    # Load the private key and get the account
    account = w3.eth.account.from_key(private_key)

    # Set the default account
    w3.eth.default_account = account.address

    # Create the contract instance using the ABI and contract address
    contract_address_router = IZUMI_CONTRACT['router']
    contract_address_swap = IZUMI_CONTRACT['swap']
    
    contract_swap = w3.eth.contract(address=contract_address_swap, abi=IZUMI_SWAP_ABI)

    # Convert amount to wei format
    amount_wei = get_amount_wei(from_token, w3, account, amount)

    # Get the gas price
    gas_price = w3.eth.gas_price

    # Construct the transaction
    transaction = {
        'chainId': 324, 
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gasPrice': gas_price,
    }

     # Get the minimum amount out -> this is the minimum amount of the 'to_token' that will be received
    def get_min_amount_out(amount: int, token_in_address: str,token_out_address: str, slippage: float):
        router_contract = get_contract(contract_address_router, w3, IZUMI_ROUTER_ABI)
        min_amount_out = router_contract.functions.getAmountOut(
            amount,
            token_in_address,
            token_out_address
        ).call()
        
        return int(min_amount_out[0] - (min_amount_out[0] / 100 * slippage))

    def fee_2_hex(fee: int):
        n0 = fee % 16
        n1 = (fee // 16) % 16
        n2 = (fee // 256) % 16
        n3 = (fee // 4096) % 16
        n4 = 0
        n5 = 0
        return '0x' + num_2_hex(n5) + num_2_hex(n4) + num_2_hex(n3) + num_2_hex(n2) + num_2_hex(n1) + num_2_hex(n0)

    def num_2_hex(num: int):

        if num < 10:
            return str(num)
        strs = 'ABCDEF'
        return strs[num - 10]
    
    def get_path(token_chain: list, fee_chain: list):
        hex_str = token_chain[0]
        for i in range(len(fee_chain)):
            hex_str += fee_2_hex(fee_chain[i])
            hex_str += token_chain[i+1]

        return hex_str


    def swap():
        try:
            deadline = int(time.time()) + 1000000

            if (from_token == 'ETH' and to_token == 'USDC') or (from_token == 'USDC' and to_token == 'ETH'):
                fee = 400 # 0.2%
                token_chain = [
                    Web3.to_checksum_address(ZKSYNC_TOKENS[from_token]), 
                    Web3.to_checksum_address(ZKSYNC_TOKENS['USDT']),
                    Web3.to_checksum_address(ZKSYNC_TOKENS[to_token])
                ]
                fee_chain = [fee, fee]
            if (from_token == 'ETH' and to_token == 'USDT') or (from_token == 'USDT' and to_token == 'ETH'):
                fee = 500 # 0.05%
            
                token_chain = [
                    Web3.to_checksum_address(ZKSYNC_TOKENS[from_token]),
                    Web3.to_checksum_address(ZKSYNC_TOKENS[to_token])
                ]
            
                fee_chain = [fee]

            if (from_token == 'ETH' and to_token == 'WETH') or (from_token == 'WETH' and to_token == 'ETH'):
                fee = 0 # 0.0%
            
                token_chain = [
                    Web3.to_checksum_address(ZKSYNC_TOKENS[from_token]),
                    Web3.to_checksum_address(ZKSYNC_TOKENS[to_token])
                ]
            
                fee_chain = [fee]

            # So basically the idea is the following: there are no router functions or similar in ABIs that gives us the path directly, so we need to create it manually.
            # The front end shows that the most favorable path for ETH to USDC is ETH -> USDT -> USDC path (it might change).   
            # We need to put the fees in hex inbetween the token addresses: like ETH_address + fee in hex + USDT_address + fee in hex + USDC_address
            path = get_path(token_chain, fee_chain)

            # Removing “0x” part
            path = path.replace("0x", "")

            if from_token != 'ETH':
                approve(amount_wei, Web3.to_checksum_address(ZKSYNC_TOKENS[from_token]), Web3.to_checksum_address(IZUMI_CONTRACT["router"]), account, w3)

            min_amount_out = get_min_amount_out(amount_wei, Web3.to_checksum_address(ZKSYNC_TOKENS[from_token]), Web3.to_checksum_address(ZKSYNC_TOKENS[to_token]), slippage)

            args = [[
                Web3.to_bytes(hexstr=path),
                account.address if from_token == 'ETH' else Web3.to_checksum_address(ZERO_ADDRESS),
                amount_wei,
                min_amount_out,
                deadline,
            ]]
            encode_data = contract_swap.encodeABI(fn_name='swapAmount', args=args)
            print("encode_data", encode_data)
            
            if from_token == 'ETH':
                call_args = [
                    encode_data,
                    Web3.to_bytes(hexstr='0x12210e8a')  # refundETH 4bytes method-id
                ]
            else:
                call_args = [
                    encode_data,
                    contract_swap.encodeABI(fn_name='unwrapWETH9', args=[
                        0,
                        account.address
                    ])
                ]

            contract_transaction = contract_swap.functions.multicall(call_args).build_transaction({
                'value': amount_wei if from_token == 'ETH' else 0,
                'nonce': w3.eth.get_transaction_count(account.address),
                'from': account.address,
                'maxFeePerGas': 0,
                'maxPriorityFeePerGas': 0,
                'gas': 0
            })

            contract_transaction.update({'maxFeePerGas': w3.eth.gas_price})
            contract_transaction.update({'maxPriorityFeePerGas': w3.eth.gas_price})

            signed_transaction = sign_transaction(contract_transaction, w3, private_key, GAS_MULTIPLIER)

            transaction_hash = send_raw_transaction(signed_transaction, w3)

            wait_for_transaction_finish(transaction_hash.hex(), account, w3)
        except Exception as error:
            print(f"❌ iZUMi swap failed [{account.address}] {error}")
    swap()

# Example usage
private_key = '-'
amount = 0.000001
from_token = 'ETH'
to_token = 'USDC'
slippage = 0.005

iZUMi_swap(private_key, amount, from_token, to_token)