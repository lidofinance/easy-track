from datetime import datetime

from brownie.network import chain
from brownie import accounts, reverts

from eth_abi import encode_single


def test_top_up_factory_evm_script_validation(
    AllowedRecipientsRegistry,
    TopUpAllowedRecipients,
    owner,
    finance,
    ldo,
    easy_track,
    voting,
    bokkyPooBahsDateTimeContract,
    stranger,
):
    deployer = owner
    trusted_caller = owner
    manager = accounts[7]
    recipient = deployer.address

    registry = deployer.deploy(
        AllowedRecipientsRegistry,
        voting,
        [manager],
        [manager],
        [manager],
        [manager],
        bokkyPooBahsDateTimeContract,
    )
    registry.addRecipient(recipient, "Test Recipient", {"from": manager})
    registry.setLimitParameters(int(100e18), 12, {"from": manager})

    top_up_factory = deployer.deploy(
        TopUpAllowedRecipients, trusted_caller, registry, finance, ldo, easy_track
    )

    def make_call_data(recipients, amounts):
        return encode_single("(address[],uint256[])", [recipients, amounts])

    with reverts("EMPTY_DATA"):
        top_up_factory.createEVMScript(trusted_caller, make_call_data([], []))

    with reverts("LENGTH_MISMATCH"):
        top_up_factory.createEVMScript(trusted_caller, make_call_data([recipient], []))

    with reverts("LENGTH_MISMATCH"):
        top_up_factory.createEVMScript(trusted_caller, make_call_data([], [123]))

    with reverts("ZERO_AMOUNT"):
        top_up_factory.createEVMScript(trusted_caller, make_call_data([recipient], [0]))

    with reverts("ZERO_AMOUNT"):
        top_up_factory.createEVMScript(
            trusted_caller, make_call_data([recipient, recipient], [123, 0])
        )

    with reverts("RECIPIENT_NOT_ALLOWED"):
        top_up_factory.createEVMScript(trusted_caller, make_call_data([stranger.address], [123]))

    payout = int(1e18)
    call_data = make_call_data([recipient], [payout])
    evm_script = top_up_factory.createEVMScript(trusted_caller, call_data)
    assert top_up_factory.decodeEVMScriptCallData(call_data) == ([recipient], [payout])
    assert "Top up allowed recipients".encode("utf-8").hex() in str(evm_script)
