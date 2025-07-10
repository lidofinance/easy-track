from brownie import web3

def get_last_block_revert_reason():
    latest_block_number = web3.eth.block_number

    block = web3.eth.get_block(latest_block_number, full_transactions=True)
    if not block.transactions:
        return None

    tx = block.transactions[-1]

    receipt = web3.eth.get_transaction_receipt(tx.hash)
    if receipt["status"] != 0:
        return None

    call_data = {
        "from": tx["from"],
        "to": tx["to"],
        "data": tx["input"],
        "value": tx.get("value", 0),
        "gas": 5_000_000
    }

    try:
        web3.eth.call(call_data, block_identifier=latest_block_number)
    except ValueError as e:
        error_data = e.args[0]
        return (
            error_data
            .get('data', {})
            .get('0x', {})
            .get('reason')
        )

    return None
