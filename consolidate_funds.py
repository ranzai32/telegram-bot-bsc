#!/usr/bin/env python3
"""
Script to consolidate all funds from subwallets to owner wallet on BSC Testnet
"""
import asyncio
from web3 import Web3
from eth_account import Account
from decimal import Decimal

# BSC Testnet RPC
RPC_URL = "https://go.getblock.io/923881e880164978873bfe7ccd8ab5b0"

# Owner wallet to receive all funds
OWNER_PRIVATE_KEY = "24eea37c6b5d99925785cce160bb42270d8de1d9cd0f2d1a2da84b9a8e7752e4"

# Subwallet private keys from logs
SUBWALLET_PRIVATE_KEYS = [
    "6d405ccedec90bad065750043c6f8b99755e1753eca105e37363aa81062a736f",
    "6811b5bc3870de842eeecf76dc75222aa960d7104ef52e1a6bf5d165ae58be8a",
    "3d61af825848b4817a3fb063030016ec36e3597b6e7e34501c5329b581a82ee4",
    "d2a227398c0c9eae85309b87768e7caac6df318b77641ce762cdeac593ecda55",
    "3dddadaeb1b21365793d69d68436281cee0f85ead5b6246c11710a66f19c64a4",
    "375c79a9bb2299b1256c5e346d6f0e7d919890d2099484ac2d0dd44f67c4ac93",
    "5dc5c15a4ac38b11a702214d6b65846b7731900672b05769a75a18f0c70604dc",
    "6cac61cd9b59c34194ddb74cdaae81570b7be148b77f1084b72875c2f4d466c6",
    "8f59f637865224459ad0439eaf85ac6272ca1274df9b1b1e154c610324645a8d",
    "7564dad6b38c500ce66731d3f31df5475c5253e81d81104679d6cd53dc240c6b",
    "78e43341966d115f12411f4880d1508d823b85e33590b3a054d42b659b5327ae",
    "773bbedb65d14c5ab4865eee3a3f475c0831813d5a5bc5a40fea7b2480b4e51a",
    "f642c7b9454172f3d14831b578d063d670101c532027cb432ef06a5b06435b26",
    "02d1dc623724a44f39f5cf6cf1fdfa6d93e71a831fce16dd8cac731fcc1c9c4a",
    "6a630e56b0bb9684cf2f18dd64fa51c82aeaa2617bc7e5900c604180d71f7990",
    "87f3768a99a2b1d508120ff188dda9e87a20ffa7ec500795fb94798c4bebe51f",
    "af8b5f74912a2ba770fa10731dad8fa9588011af568354bd9fb5225b811a9ac8",
    "a4b222d1725e4a0b5d203652200e30b255b611b211646d7a25982adf81a6aa69",
    "d54a37285d325994513a674eaeb24b54d4ab1af4b62332198467b306a8dd1528",
    "c6d544150c062cb0680f5ff80ad433664eaf10203d637aaccba7a1357852924e",
]

# Gas settings
GAS_LIMIT = 21000  # Standard transfer gas limit
GAS_PRICE_GWEI = 3  # BSC testnet typical gas price


def consolidate_wallet(w3: Web3, subwallet_pk: str, owner_address: str) -> tuple[bool, str]:
    """
    Transfer all BNB from a subwallet to owner address
    Returns: (success: bool, message: str)
    """
    try:
        # Get subwallet account
        account = Account.from_key(subwallet_pk)
        subwallet_address = account.address
        
        # Get balance
        balance_wei = w3.eth.get_balance(subwallet_address)
        balance_bnb = Decimal(balance_wei) / Decimal(10**18)
        
        if balance_wei == 0:
            return True, f"[SKIP] {subwallet_address}: Balance is 0"
        
        # Calculate gas cost
        gas_price = w3.to_wei(GAS_PRICE_GWEI, 'gwei')
        gas_cost = GAS_LIMIT * gas_price
        
        # Calculate amount to send (all balance minus gas)
        amount_to_send = balance_wei - gas_cost
        
        if amount_to_send <= 0:
            return False, f"[INSUFFICIENT] {subwallet_address}: {balance_bnb:.6f} BNB (not enough for gas)"
        
        # Get nonce
        nonce = w3.eth.get_transaction_count(subwallet_address)
        
        # Build transaction
        transaction = {
            'nonce': nonce,
            'to': owner_address,
            'value': amount_to_send,
            'gas': GAS_LIMIT,
            'gasPrice': gas_price,
            'chainId': 97  # BSC Testnet
        }
        
        # Sign transaction
        signed_txn = w3.eth.account.sign_transaction(transaction, subwallet_pk)
        
        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        
        # Wait for receipt
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        amount_sent_bnb = Decimal(amount_to_send) / Decimal(10**18)
        
        if receipt['status'] == 1:
            return True, f"[SUCCESS] {subwallet_address}: {amount_sent_bnb:.6f} BNB → {tx_hash.hex()}"
        else:
            return False, f"[FAILED] {subwallet_address}: Transaction reverted → {tx_hash.hex()}"
            
    except Exception as e:
        return False, f"[ERROR] {subwallet_address if 'subwallet_address' in locals() else 'Unknown'}: {str(e)}"


def main():
    print("=" * 80)
    print("BSC Testnet Fund Consolidation Script")
    print("=" * 80)
    
    # Initialize Web3
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Check connection
    if not w3.is_connected():
        print("❌ Failed to connect to BSC Testnet RPC")
        return
    
    print(f"✅ Connected to BSC Testnet (Chain ID: {w3.eth.chain_id})")
    
    # Get owner address
    owner_account = Account.from_key(OWNER_PRIVATE_KEY)
    owner_address = owner_account.address
    
    print(f"📍 Owner address: {owner_address}")
    
    # Get initial owner balance
    initial_balance = w3.eth.get_balance(owner_address)
    initial_balance_bnb = Decimal(initial_balance) / Decimal(10**18)
    print(f"💰 Initial owner balance: {initial_balance_bnb:.6f} BNB")
    print("=" * 80)
    
    # Process each subwallet
    total_subwallets = len(SUBWALLET_PRIVATE_KEYS)
    successful = 0
    failed = 0
    skipped = 0
    
    for idx, pk in enumerate(SUBWALLET_PRIVATE_KEYS, 1):
        print(f"\n[{idx}/{total_subwallets}] Processing subwallet...")
        success, message = consolidate_wallet(w3, pk, owner_address)
        print(f"    {message}")
        
        if success:
            if "[SKIP]" in message:
                skipped += 1
            else:
                successful += 1
        else:
            failed += 1
    
    # Get final owner balance
    print("\n" + "=" * 80)
    final_balance = w3.eth.get_balance(owner_address)
    final_balance_bnb = Decimal(final_balance) / Decimal(10**18)
    recovered_bnb = final_balance_bnb - initial_balance_bnb
    
    print(f"💰 Final owner balance: {final_balance_bnb:.6f} BNB")
    print(f"📈 Recovered: {recovered_bnb:.6f} BNB")
    print("=" * 80)
    print(f"\n✅ Successful: {successful}")
    print(f"⏭️  Skipped (0 balance): {skipped}")
    print(f"❌ Failed: {failed}")
    print("=" * 80)


if __name__ == "__main__":
    main()
