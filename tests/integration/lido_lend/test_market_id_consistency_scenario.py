from brownie import web3
from eth_abi import encode

from utils.lido_lend import MARKET_PARAMS_ABI_TYPE as MP_TYPE


def test_market_id_derivation(lido_lend):
    "Lock the Morpho id derivation the factories rely on — id == keccak256(abi.encode(marketParams)) — against the on-chain source of truth (the deployed controller's marketId), not the descriptor's own id. Confirms the descriptor's marketParams field order/types match the real market, which is exactly what the factories' CONTROLLER_MISMATCH / VAULT_MARKET_MISMATCH checks and the IRM/exit-book resolution depend on."
    m = lido_lend.market
    market_params = (m["loanToken"], m["collateralToken"], m["oracle"], m["irm"], m["lltv"])
    computed = web3.keccak(encode([MP_TYPE], [market_params])).hex()  # web3 v6 HexBytes.hex() is 0x-prefixed

    on_chain_id = lido_lend.contract("controller").marketId()  # authoritative, set at controller deploy
    assert computed == on_chain_id
