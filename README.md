
![Group 80](https://github.com/kirill-maestro/Scripts-zkSync/assets/69819227/7644850c-963f-43d8-ae15-df1b2a883b1d)

# 🏛️ Scripts-zkSync 🏛️
This is the script for zkSync Era chain that help people semi-automate transactions. 
You do not need to use slow front end to do the transactions. 

**🎣🎣🎣 This script is the gateway to securing airdrops with ease. 🎣🎣🎣**

## What are the supported functions?
1. **Orbiter Finance**: Bridge ETH from zkSync Era to other EVM-compatible chains.
2. **Woofi Swap**: Execute token swaps on zkSync Era.
3. **iZUMi Swap**: Execute token swaps on zkSync Era.
4. **Sync Swap**: Execute token swaps on zkSync Era.
5. **Dmail**: Send dmails on zkSync Era. 

## Is it safe? 
The scipt is as simple as possible with only the neccessary and reliable libraries used. Only the signed messages are communicated online meaning your private keys are saved on your local machine and thus are safe from being leaked. We have developed this script and use it for own purposes. 


## Set up:

1. Clone the repository and install dependencies:
```
git clone https://github.com/kirill-maestro/Scripts-zkSync

cd Scripts-zkSync

pip install -r requirements.txt

```

2. Insert your rpc to each module:
```
w3 = Web3(Web3.HTTPProvider("https://rpc.ankr.com/zksync_era/")) <- put your link here if you want to have different RPC.
```

3. Insert your private keys to keys.txt file


## Run: 

1. Navigate to your desired module.
2. Go down till you see "# SETTINGS START HERE".
3. Adjust the settings according to your requirements.
4. Run the code of the module.
