import random
import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider


# If you use one of the suggested infrastructure providers, the url will be of the form
# now_url  = f"https://eth.nownodes.io/{now_token}"
# alchemy_url = f"https://eth-mainnet.alchemyapi.io/v2/{alchemy_token}"
# infura_url = f"https://mainnet.infura.io/v3/{infura_token}"

def connect_to_eth():
	# TODO insert your code for this method from last week's assignment
	url = "https://eth-mainnet.g.alchemy.com/v2/hXBhP5nsfedxBq3T7R3nrcHEKYrC8MNn"  # FILL THIS IN
	w3 = Web3(HTTPProvider(url))
	assert w3.is_connected(), f"Failed to connect to provider at {url}"

	return w3


def connect_with_middleware(contract_json):
	# TODO insert your code for this method from last week's assignment
	with open(contract_json, "r") as f:
		d = json.load(f)
		d = d['bsc']
		address = d['address']
		abi = d['abi']

	# TODO complete this method
	# The first section will be the same as "connect_to_eth()" but with a BNB url
	# w3 = 0
	bnb_testnet_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
	w3 = Web3(HTTPProvider(bnb_testnet_url))

	# The second section requires you to inject middleware into your w3 object and
	# create a contract object. Read more on the docs pages at https://web3py.readthedocs.io/en/stable/middleware.html
	# and https://web3py.readthedocs.io/en/stable/web3.contract.html
	w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

	assert w3.is_connected(), f"Failed to connect to BNB testnet at {bnb_testnet_url}"

	contract = w3.eth.contract(address=address, abi=abi)

	return w3, contract


def is_ordered_block(w3, block_num):
	"""
	Takes a block number
	Returns a boolean that tells whether all the transactions in the block are ordered by priority fee

	Before EIP-1559, a block is ordered if and only if all transactions are sorted in decreasing order of the gasPrice field

	After EIP-1559, there are two types of transactions
		*Type 0* The priority fee is tx.gasPrice - block.baseFeePerGas
		*Type 2* The priority fee is min( tx.maxPriorityFeePerGas, tx.maxFeePerGas - block.baseFeePerGas )

	Conveniently, most type 2 transactions set the gasPrice field to be min( tx.maxPriorityFeePerGas + block.baseFeePerGas, tx.maxFeePerGas )
	"""
	block = w3.eth.get_block(block_num, full_transactions=True)
	base_fee = block.get("baseFeePerGas", 0)
	priority_fees = []

	for tx in block.transactions:
		tx_type = tx.get("type", "0x0")     # default to legacy if missing
		effective_priority = 0 # always define it

		if tx_type == "0x2":     # EIP-1559 type 2
			max_priority = tx.get("maxPriorityFeePerGas")
			max_fee = tx.get("maxFeePerGas")

			# Calculate effective priority fee
			if max_priority is not None and max_fee is not None and base_fee is not None:
				# priority fee = min(maxPriorityFeePerGas, maxFeePerGas - baseFeePerGas)
				calculated_priority = max_fee - base_fee
				if max_priority < calculated_priority:
					effective_priority = max_priority
				else:
					effective_priority = calculated_priority
			else:
				effective_priority = tx.get("gasPrice", 0)

		elif tx_type == "0x0" or tx_type is None:     # EIP-1559 type 0
			gas_price = tx.get("gasPrice", 0)

			if "baseFeePerGas" in block and base_fee is not None:
				effective_priority = gas_price - base_fee
			else:
				effective_priority = gas_price

		else:
			# unknown or unsupported type
			priority_fees.append(tx.get("gasPrice", 0))

		priority_fees.append(effective_priority)

	# Check is the priority_fees are in non-ascending order
	ordered = True
	for i in range(len(priority_fees) - 1):
		if priority_fees[i] < priority_fees [i + 1]:
			ordered = False
			break

	return ordered


def get_contract_values(contract, admin_address, owner_address):
	"""
	Takes a contract object, and two addresses (as strings) to be used for calling
	the contract to check current on chain values.
	The provided "default_admin_role" is the correctly formatted solidity default
	admin value to use when checking with the contract
	To complete this method you need to make three calls to the contract to get:
	  onchain_root: Get and return the merkleRoot from the provided contract
	  has_role: Verify that the address "admin_address" has the role "default_admin_role" return True/False
	  prime: Call the contract to get and return the prime owned by "owner_address"

	check on available contract functions and transactions on the block explorer at
	https://testnet.bscscan.com/address/0xaA7CAaDA823300D18D3c43f65569a47e78220073
	"""
	default_admin_role = int.to_bytes(0, 32, byteorder="big")

	# TODO complete the following lines by performing contract calls
	# Get and return the merkleRoot from the provided contract
	onchain_root = contract.functions.merkleRoot().call()

	# Check the contract to see if the address "admin_address" has the role "default_admin_role"
	has_role = contract.functions.hasRole(default_admin_role, admin_address).call()

	# Call the contract to get the prime owned by "owner_address"
	prime = contract.functions.getPrimeByOwner(owner_address).call()

	return onchain_root, has_role, prime


"""
	This might be useful for testing (main is not run by the grader feel free to change 
	this code anyway that is helpful)
"""
if __name__ == "__main__":
	# These are addresses associated with the Merkle contract (check on contract
	# functions and transactions on the block explorer at
	# https://testnet.bscscan.com/address/0xaA7CAaDA823300D18D3c43f65569a47e78220073
	admin_address = "0xAC55e7d73A792fE1A9e051BDF4A010c33962809A"
	owner_address = "0x793A37a85964D96ACD6368777c7C7050F05b11dE"
	contract_file = "contract_info.json"

	eth_w3 = connect_to_eth()
	cont_w3, contract = connect_with_middleware(contract_file)

	latest_block = eth_w3.eth.get_block_number()
	london_hard_fork_block_num = 12965000
	assert latest_block > london_hard_fork_block_num, f"Error: the chain never got past the London Hard Fork"

	n = 5
	for _ in range(n):
		block_num = random.randint(1, latest_block)
		ordered = is_ordered_block(block_num)
		if ordered:
			print(f"Block {block_num} is ordered")
		else:
			print(f"Block {block_num} is not ordered")
