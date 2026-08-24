from brownie import LidoLendSetFeeRecipient
from eth_abi import encode


def test_set_fee_recipient_scenario(
    lido_lend,
    created_markets,
    easy_track,
    deployer,
    trusted_caller,
    stranger,
    permission,
    register_factory,
    enact_motion,
):
    "A recipient motion accrues every listed market before changing the global fee recipient."
    core = lido_lend.contract("core")
    owner = lido_lend.contract("owner")
    market_ids = [market["id"] for market in lido_lend.markets]
    new_recipient = stranger.address
    if core.feeRecipient() == new_recipient:
        new_recipient = deployer.address

    accrued_before = core.accrueInterestCalls() if lido_lend.local else None
    factory = deployer.deploy(LidoLendSetFeeRecipient, trusted_caller, owner)
    register_factory(
        factory,
        permission((core, core.accrueInterest), (owner, owner.setFeeRecipient)),
    )
    enact_motion(
        easy_track,
        factory,
        "0x" + encode(["bytes32[]", "address"], [market_ids, new_recipient]).hex(),
        trusted_caller,
    )

    assert core.feeRecipient() == new_recipient
    if lido_lend.local:
        assert core.accrueInterestCalls() == accrued_before + len(market_ids)
        assert [core.accruedMarketIds(accrued_before + i) for i in range(len(market_ids))] == market_ids
