import pytest
from brownie import (
    AllowConsolidationPair,
    ConsolidationMigratorStub,
    CSModuleNodeOperatorsStub,
    NodeOperatorsRegistryStub,
    reverts,
)  # type: ignore

from utils.evm_script import encode_call_script, encode_calldata

SOURCE_MODULE_ID = 1
TARGET_MODULE_ID = 2
SOURCE_OPERATOR_ID = 0
TARGET_OPERATOR_ID = 3


def _encode_input(source_operator_id=SOURCE_OPERATOR_ID, target_operator_id=TARGET_OPERATOR_ID):
    return encode_calldata(["uint256", "uint256"], [source_operator_id, target_operator_id])


@pytest.fixture(scope="module")
def target_module_stub(owner):
    module = owner.deploy(CSModuleNodeOperatorsStub)
    module.setNodeOperatorsCount(TARGET_OPERATOR_ID + 2, {"from": owner})
    return module


@pytest.fixture(scope="module")
def source_module_stub(owner):
    registry = owner.deploy(NodeOperatorsRegistryStub, owner)
    registry.setDesiredNodeOperatorCount(SOURCE_OPERATOR_ID + 1, {"from": owner})
    registry.setNodeOperatorRewardAddress(SOURCE_OPERATOR_ID, owner, {"from": owner})
    return registry


@pytest.fixture(scope="module")
@pytest.fixture(scope="module")
def consolidation_migrator_stub(owner, source_module_stub, target_module_stub):
    return owner.deploy(
        ConsolidationMigratorStub,
        SOURCE_MODULE_ID,
        TARGET_MODULE_ID,
        source_module_stub,
        target_module_stub,
    )


@pytest.fixture(scope="module")
def allow_consolidation_pair_factory(
    owner,
    source_module_stub,
    target_module_stub,
    consolidation_migrator_stub,
):
    return owner.deploy(
        AllowConsolidationPair,
        consolidation_migrator_stub,
    )


def test_deploy(
    allow_consolidation_pair_factory,
    source_module_stub,
    target_module_stub,
    consolidation_migrator_stub,
):
    assert allow_consolidation_pair_factory.sourceModule() == source_module_stub
    assert allow_consolidation_pair_factory.targetModule() == target_module_stub
    assert allow_consolidation_pair_factory.consolidationMigrator() == consolidation_migrator_stub
    assert allow_consolidation_pair_factory.sourceModuleId() == SOURCE_MODULE_ID
    assert allow_consolidation_pair_factory.targetModuleId() == TARGET_MODULE_ID


def test_create_evm_script_called_by_stranger(stranger, allow_consolidation_pair_factory):
    calldata = _encode_input()
    with reverts("CALLER_IS_NOT_SOURCE_OPERATOR_OWNER"):
        allow_consolidation_pair_factory.createEVMScript(stranger, calldata, {"from": stranger})


def test_source_operator_must_exist(owner, allow_consolidation_pair_factory):
    calldata = _encode_input(source_operator_id=SOURCE_OPERATOR_ID + 1)
    with reverts("SOURCE_OPERATOR_ID_OUT_OF_RANGE"):
        allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})


def test_source_operator_out_of_range(owner, source_module_stub, allow_consolidation_pair_factory):
    source_module_stub.setDesiredNodeOperatorCount(SOURCE_OPERATOR_ID, {"from": owner})
    calldata = _encode_input()
    with reverts("SOURCE_OPERATOR_ID_OUT_OF_RANGE"):
        allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})
    source_module_stub.setDesiredNodeOperatorCount(SOURCE_OPERATOR_ID + 1, {"from": owner})


def test_caller_must_match_owner(owner, stranger, source_module_stub, allow_consolidation_pair_factory):
    source_module_stub.setNodeOperatorRewardAddress(SOURCE_OPERATOR_ID, stranger, {"from": owner})
    calldata = _encode_input()
    with reverts("CALLER_IS_NOT_SOURCE_OPERATOR_OWNER"):
        allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})
    source_module_stub.setNodeOperatorRewardAddress(SOURCE_OPERATOR_ID, owner, {"from": owner})


def test_target_operator_out_of_range(owner, target_module_stub, allow_consolidation_pair_factory):
    target_module_stub.setNodeOperatorsCount(TARGET_OPERATOR_ID, {"from": owner})
    calldata = _encode_input()
    with reverts("TARGET_OPERATOR_ID_OUT_OF_RANGE"):
        allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})
    target_module_stub.setNodeOperatorsCount(TARGET_OPERATOR_ID + 2, {"from": owner})


def test_pair_already_allowed(
    owner,
    consolidation_migrator_stub,
    allow_consolidation_pair_factory,
):
    consolidation_migrator_stub.setPairStatus(SOURCE_OPERATOR_ID, TARGET_OPERATOR_ID, True, {"from": owner})
    calldata = _encode_input()
    with reverts("PAIR_ALREADY_ALLOWED"):
        allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})
    consolidation_migrator_stub.setPairStatus(SOURCE_OPERATOR_ID, TARGET_OPERATOR_ID, False, {"from": owner})


def test_create_evm_script(
    owner,
    allow_consolidation_pair_factory,
    consolidation_migrator_stub,
):
    calldata = _encode_input()
    evm_script = allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})
    expected_evm_script = encode_call_script(
        [
            (
                consolidation_migrator_stub.address,
                consolidation_migrator_stub.allowPair.encode_input(
                    SOURCE_OPERATOR_ID, TARGET_OPERATOR_ID
                ),
            )
        ]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(allow_consolidation_pair_factory):
    calldata = _encode_input()
    decoded = allow_consolidation_pair_factory.decodeEVMScriptCallData(calldata)
    assert decoded == (
        SOURCE_OPERATOR_ID,
        TARGET_OPERATOR_ID,
    )
