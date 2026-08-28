import pytest
from brownie import (
    LidoLendExitBookActions,
    LidoLendGuardianActions,
    LidoLendMarketManagerActions,
    LidoLendCircuitBreakerActions,
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
        (LidoLendGuardianActions, "decodeUnbanAccountsPayload", ["marketIds", "accounts"]),
        (LidoLendCircuitBreakerActions, "decodeRegisterPauserPayload", ["marketId", "pauser"]),
        (LidoLendCircuitBreakerActions, "decodeConfigValuePayload", ["value"]),
        (
            LidoLendExitBookActions,
            "decodeSetMorphoExitBookAllowedPayload",
            ["marketParamsList", "allowed"],
        ),
    ],
)
def test_frontend_decoder_output_names(factory, function_name, expected_names):
    decoder = next(entry for entry in factory.abi if entry.get("name") == function_name)
    assert [output["name"] for output in decoder["outputs"]] == expected_names


def test_collateral_activation_decoder_component_names():
    decoder = next(
        entry
        for entry in LidoLendMarketManagerActions.abi
        if entry.get("name") == "decodeSetCollateralActivationConfigPayload"
    )
    assert [component["name"] for component in decoder["outputs"][1]["components"]] == [
        "minActivationDelay",
        "maxActivationDelay",
        "maxDelayInflow",
        "minDepositAmount",
        "activatingLockDuration",
        "minActivationAmount",
        "maxGuardiansQuorumDelay",
        "delayPerStrike",
        "delayPerSuspect",
    ]
