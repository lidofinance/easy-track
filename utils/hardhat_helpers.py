from brownie import chain

def get_last_tx_revert_reason():
    return chain.get_transaction(chain[-1].transactions[-1]).revert_msg
