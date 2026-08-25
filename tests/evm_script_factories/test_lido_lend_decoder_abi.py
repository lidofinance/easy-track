import pytest
from brownie import (
    LidoLendExitBookActions,
    LidoLendGuardianActions,
    LidoLendIrmActions,
    LidoLendMarketManagerActions,
)


@pytest.mark.parametrize(
    "factory,function_name,expected_names",
    [
        (
            LidoLendMarketManagerActions,
            "decodeSetCollateralActivationConfigPayload",
            ["marketId", "newCfg"],
        ),
        (LidoLendMarketManagerActions, "decodeSetSettlementConfigPayload", ["marketId", "newConfig"]),
        (LidoLendMarketManagerActions, "decodeSetSupplyCapPayload", ["marketId", "newCap"]),
        (LidoLendGuardianActions, "decodeSetGuardiansQuorumPayload", ["marketId", "newQuorum"]),
        (LidoLendGuardianActions, "decodeSetSuspectWindowPayload", ["marketId", "newSuspectWindow"]),
        (LidoLendIrmActions, "decodeSetMarketIrmPayload", ["marketId", "newIrm"]),
        (
            LidoLendExitBookActions,
            "decodeSetMorphoExitBookAllowedPayload",
            ["exitBook", "marketParamsList", "allowed"],
        ),
    ],
)
def test_frontend_decoder_output_names(factory, function_name, expected_names):
    decoder = next(entry for entry in factory.abi if entry.get("name") == function_name)
    assert [output["name"] for output in decoder["outputs"]] == expected_names
