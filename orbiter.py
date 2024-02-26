from web3 import Web3
import requests
import asyncio
from utils.transaction_utils import sign_transaction, send_raw_transaction, wait_for_transaction_finish

# The address of the Orbiter bridging contract
ORBITER_CONTRACT = "0x80c67432656d59144ceff962e8faf8926599bcf8"

# The chain IDs of the supported chains for later use
CHAIN_IDs = {
    "ethereum": "1",
    "arbitrum": "42161",
    "optimism": "10",
    "zksync": "324",
    "nova": "42170",
    "zkevm": "1101",
    "scroll": "534352",
    "base": "8453",
    "linea": "59144",
    "zora": "7777777",
    "manta": "169"
}

GAS_MULTIPLIER = 1.01


async def orbiter_bridge(private_key, amount, from_chain, destination_chain):
    # Connect to the Ethereum network -> put your own RPC URL here
    w3 = Web3(Web3.HTTPProvider(
        "https://rpc.ankr.com/zksync_era/"))

    # Load the private key and get the account
    account = w3.eth.account.from_key(private_key)

    # Set the default account
    w3.eth.default_account = account.address

    # Get the gas price
    gas_price = w3.eth.gas_price

    # Construct the transaction
    transaction = {
        'chainId': w3.eth.chain_id,
        'from': account.address,
        'nonce': w3.eth.get_transaction_count(account.address),
        'gasPrice': gas_price,
        'to': Web3.to_checksum_address(ORBITER_CONTRACT),
    }

    # It is so, that orbiter finance bridge understands the chain distination by the last 4 digits of the amount,
    # so we have to communicate with orbiter finance API to get the right amount for the chosen destination chain.
    async def get_bridge_amount(from_chain: str, to_chain: str, amount: float):
        url = "https://openapi.orbiter.finance/explore/v3/yj6toqvwh1177e1sexfy0u1pxx5j8o47"

        headers = {"Content-Type": "application/json"}

        payload = {
            "id": 1,
            "jsonrpc": "2.0",
            "method": "orbiter_calculatedAmount",
            "params": [f"{CHAIN_IDs[from_chain]}-{CHAIN_IDs[to_chain]}:ETH-ETH", float(amount)]
        }

        response = requests.request(
            "POST",
            url,
            headers=headers,
            json=payload,
        )

        response_data = response.json()

        if response_data.get("result").get("error", None) is None:
            return int(response_data.get("result").get("_sendValue"))

        else:
            error_data = response_data.get("result").get("error")
            return False

    async def bridge():

        print(
            f"[{account.address}] Bridging {from_chain} –> {destination_chain} | {amount} ETH")

        bridge_amount = await get_bridge_amount(from_chain, destination_chain, amount)

        if bridge_amount is False:
            return

        transaction.update({'value': bridge_amount})

        balance = w3.eth.get_balance(account.address)

        if bridge_amount > balance:

            print(f"[{account.address}] ERROR: Insufficient funds!")
        else:

            signed_transaction = sign_transaction(
                transaction, w3, private_key, GAS_MULTIPLIER)

            transaction_hash = send_raw_transaction(signed_transaction, w3)

            wait_for_transaction_finish(transaction_hash.hex(), account, w3)
            print(f"[{account.address}] bridged [{amount}] from [{from_chain}] to [{destination_chain}]")

    await bridge()



async def main():
    # SETTINGS START HERE:
    amount = 0.005  # How much ETH do you want to bridge?
    # if you change it, make sure to adjust your RPC! -> if you bridge from zksync, the rpc has to be for zksync. If from scroll - scroll.
    from_chain = 'zksync'
    destination_chain = 'scroll'
    # SETTINGS END HERE

    with open('keys.txt', 'r') as file:
        for private_key in file:
            private_key = private_key.strip()
            await orbiter_bridge(private_key, amount, from_chain, destination_chain)
asyncio.run(main())
