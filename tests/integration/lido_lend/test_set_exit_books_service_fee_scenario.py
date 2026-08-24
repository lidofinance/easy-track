import pytest
from brownie import LidoLendSetExitBooksServiceFee
from eth_abi import encode


SERVICE_FEE = 10**17
FEE_RECIPIENT = "0x" + "fe" * 20
ZERO_ADDRESS = "0x" + "00" * 20


def test_set_exit_books_service_fee_scenario(
    lido_lend,
    easy_track,
    deployer,
    trusted_caller,
    enact_motion,
):
    if not lido_lend.has("morphoExitBook") or not lido_lend.has("erc4626ExitBook"):
        if lido_lend.local:
            pytest.skip("deployment has no exit books")
        raise pytest.UsageError("deployment has no exit books")

    books = [
        lido_lend.contract("morphoExitBook"),
        lido_lend.contract("erc4626ExitBook"),
    ]
    factory = deployer.deploy(
        LidoLendSetExitBooksServiceFee,
        trusted_caller,
    )
    permission = "0x" + "".join(book.address[2:] + book.setServiceFee.signature[2:] for book in books)
    easy_track.addEVMScriptFactory(factory, permission, {"from": deployer})

    def calldata(recipient, fee):
        return (
            "0x"
            + encode(
                ["address[]", "address", "uint256"],
                [[book.address for book in books], recipient, fee],
            ).hex()
        )

    enact_motion(easy_track, factory, calldata(FEE_RECIPIENT, SERVICE_FEE), trusted_caller)
    for book in books:
        assert book.feeRecipient() == FEE_RECIPIENT
        assert book.serviceFee() == SERVICE_FEE

    # The target setter permits repeated values, so a fixed-size batch remains enactable.
    enact_motion(easy_track, factory, calldata(FEE_RECIPIENT, SERVICE_FEE), trusted_caller)

    enact_motion(easy_track, factory, calldata(ZERO_ADDRESS, 0), trusted_caller)
    for book in books:
        assert book.feeRecipient() == ZERO_ADDRESS
        assert book.serviceFee() == 0
