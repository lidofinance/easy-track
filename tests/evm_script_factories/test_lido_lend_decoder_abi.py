import pytest
from brownie import (
    LidoLendExitBookActions,
    LidoLendGuardianActions,
    LidoLendMarketManagerActions,
    LidoLendCircuitBreakerActions,
    LidoLendTrailingAnchorOracleActions,
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
        (LidoLendMarketManagerActions, "decodeUnfreezeMarketsPayload", ["marketIds"]),
        (LidoLendGuardianActions, "decodeSetGuardiansQuorumPayload", ["marketId", "newQuorum"]),
        (LidoLendGuardianActions, "decodeSetSuspectWindowPayload", ["marketId", "newSuspectWindow"]),
        (LidoLendGuardianActions, "decodeUnbanAccountsPayload", ["requests"]),
        (LidoLendCircuitBreakerActions, "decodeRegisterPauserPayload", ["marketId", "pauser"]),
        (LidoLendCircuitBreakerActions, "decodeConfigValuePayload", ["value"]),
        (
            LidoLendExitBookActions,
            "decodeSetMorphoExitBookAllowedPayload",
            ["marketParamsList", "allowed"],
        ),
        (LidoLendTrailingAnchorOracleActions, "decodeSetParametersPayload", ["oracle", "parameters"]),
        (LidoLendTrailingAnchorOracleActions, "decodeSetPricingResumesAtPayload", ["oracle", "resumesAt"]),
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


def test_trailing_anchor_oracle_parameters_decoder_component_names():
    decoder = next(
        entry for entry in LidoLendTrailingAnchorOracleActions.abi if entry.get("name") == "decodeSetParametersPayload"
    )
    assert [component["name"] for component in decoder["outputs"][1]["components"]] == [
        "maxPriceAboveAnchor",
        "maxPriceBelowAnchor",
        "maxAnchorContinuousRiseRate",
        "maxAnchorContinuousFallRate",
        "maxAnchorBelowBase",
        "maxAnchorAboveBase",
        "reanchorDelay",
        "reanchorWindow",
    ]


def test_unban_request_decoder_component_names():
    decoder = next(entry for entry in LidoLendGuardianActions.abi if entry.get("name") == "decodeUnbanAccountsPayload")
    assert [component["name"] for component in decoder["outputs"][0]["components"]] == [
        "account",
        "marketIds",
    ]
