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
TARGET_OPERATOR_IDS = [3, 4]
MANAGE_SIGNING_KEYS_ROLE = (
    "0x75abc64490e17b40ea1e66691c3eb493647b24430b358bd87ec3e5127f1621ee"
)


def _encode_input_with_submitter(
    submitter,
    source_operator_id=SOURCE_OPERATOR_ID,
    target_operator_ids=None,
):
    if target_operator_ids is None:
        target_operator_ids = TARGET_OPERATOR_IDS
    return encode_calldata(
        ["address", "uint256", "uint256[]"],
        [submitter, source_operator_id, target_operator_ids],
    )


def _expected_evm_script(consolidation_migrator_stub, submitter, target_operator_ids):
    return encode_call_script(
        [
            (
                consolidation_migrator_stub.address,
                consolidation_migrator_stub.allowPair.encode_input(
                    SOURCE_OPERATOR_ID,
                    target_operator_id,
                    submitter,
                ),
            )
            for target_operator_id in target_operator_ids
        ]
    )


@pytest.fixture(scope="module")
def target_module_stub(owner):
    module = owner.deploy(CSModuleNodeOperatorsStub)
    module.setNodeOperatorsCount(TARGET_OPERATOR_IDS[-1] + 2, {"from": owner})
    for target_operator_id in TARGET_OPERATOR_IDS:
        module.setNodeOperatorIsActive(target_operator_id, True, {"from": owner})
    return module


@pytest.fixture(scope="module")
def source_module_stub(owner):
    registry = owner.deploy(NodeOperatorsRegistryStub, owner)
    registry.setDesiredNodeOperatorCount(SOURCE_OPERATOR_ID + 1, {"from": owner})
    registry.setNodeOperatorRewardAddress(SOURCE_OPERATOR_ID, owner, {"from": owner})
    return registry


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
    calldata = _encode_input_with_submitter(stranger.address)
    with reverts("CALLER_IS_NOT_SOURCE_OPERATOR_OWNER_OR_MANAGER"):
        allow_consolidation_pair_factory.createEVMScript(stranger, calldata, {"from": stranger})


def test_source_operator_must_exist(owner, allow_consolidation_pair_factory):
    calldata = _encode_input_with_submitter(
        owner.address,
        source_operator_id=SOURCE_OPERATOR_ID + 1,
    )
    with reverts("SOURCE_OPERATOR_ID_DOES_NOT_EXIST"):
        allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})


def test_source_operator_out_of_range(owner, source_module_stub, allow_consolidation_pair_factory):
    source_module_stub.setDesiredNodeOperatorCount(SOURCE_OPERATOR_ID, {"from": owner})
    calldata = _encode_input_with_submitter(owner.address)
    with reverts("SOURCE_OPERATOR_ID_DOES_NOT_EXIST"):
        allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})
    source_module_stub.setDesiredNodeOperatorCount(SOURCE_OPERATOR_ID + 1, {"from": owner})


def test_source_operator_must_be_active(owner, source_module_stub, allow_consolidation_pair_factory):
    source_module_stub.setActive(SOURCE_OPERATOR_ID, False, {"from": owner})
    calldata = _encode_input_with_submitter(owner.address)
    with reverts("NODE_OPERATOR_IS_NOT_ACTIVE"):
        allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})
    source_module_stub.setActive(SOURCE_OPERATOR_ID, True, {"from": owner})


def test_caller_must_match_owner(owner, stranger, source_module_stub, allow_consolidation_pair_factory):
    source_module_stub.setNodeOperatorRewardAddress(SOURCE_OPERATOR_ID, stranger, {"from": owner})
    calldata = _encode_input_with_submitter(owner.address)
    with reverts("CALLER_IS_NOT_SOURCE_OPERATOR_OWNER_OR_MANAGER"):
        allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})
    source_module_stub.setNodeOperatorRewardAddress(SOURCE_OPERATOR_ID, owner, {"from": owner})


def test_caller_with_manage_signing_keys_role_can_create_script(
    owner,
    stranger,
    source_module_stub,
    allow_consolidation_pair_factory,
    consolidation_migrator_stub,
):
    source_module_stub.setCanPerform(
        stranger,
        MANAGE_SIGNING_KEYS_ROLE,
        SOURCE_OPERATOR_ID,
        True,
        {"from": owner},
    )

    calldata = _encode_input_with_submitter(owner.address)
    evm_script = allow_consolidation_pair_factory.createEVMScript(
        stranger,
        calldata,
        {"from": owner},
    )

    assert evm_script == _expected_evm_script(
        consolidation_migrator_stub,
        owner.address,
        TARGET_OPERATOR_IDS,
    )


def test_validation_uses_creator_not_tx_sender(
    owner,
    stranger,
    allow_consolidation_pair_factory,
    consolidation_migrator_stub,
):
    calldata = _encode_input_with_submitter(owner.address)
    evm_script = allow_consolidation_pair_factory.createEVMScript(
        owner,
        calldata,
        {"from": stranger},
    )

    assert evm_script == _expected_evm_script(
        consolidation_migrator_stub,
        owner.address,
        TARGET_OPERATOR_IDS,
    )


def test_target_operator_ids_must_not_be_empty(owner, allow_consolidation_pair_factory):
    calldata = _encode_input_with_submitter(owner.address, target_operator_ids=[])
    with reverts("EMPTY_TARGET_OPERATOR_IDS"):
        allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})


def test_create_evm_script_preserves_unsorted_target_ids_order(
    owner,
    allow_consolidation_pair_factory,
    consolidation_migrator_stub,
):
    unsorted_target_ids = [4, 3]
    calldata = _encode_input_with_submitter(owner.address, target_operator_ids=unsorted_target_ids)
    evm_script = allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})

    assert evm_script == _expected_evm_script(
        consolidation_migrator_stub,
        owner.address,
        unsorted_target_ids,
    )


def test_target_operator_ids_must_not_have_duplicates(owner, allow_consolidation_pair_factory):
    calldata = _encode_input_with_submitter(owner.address, target_operator_ids=[3, 3])
    with reverts("DUPLICATE_TARGET_OPERATOR_ID"):
        allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})


def test_target_operator_must_be_active(owner, target_module_stub, allow_consolidation_pair_factory):
    target_module_stub.setNodeOperatorIsActive(TARGET_OPERATOR_IDS[0], False, {"from": owner})
    calldata = _encode_input_with_submitter(owner.address)
    with reverts("NODE_OPERATOR_IS_NOT_ACTIVE"):
        allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})
    target_module_stub.setNodeOperatorIsActive(TARGET_OPERATOR_IDS[0], True, {"from": owner})


def test_create_evm_script_when_pair_is_already_allowed(
    owner,
    consolidation_migrator_stub,
    allow_consolidation_pair_factory,
):
    consolidation_migrator_stub.setPairStatus(SOURCE_OPERATOR_ID, TARGET_OPERATOR_IDS[0], True, {"from": owner})
    calldata = _encode_input_with_submitter(owner.address)
    evm_script = allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})

    assert evm_script == _expected_evm_script(
        consolidation_migrator_stub,
        owner.address,
        TARGET_OPERATOR_IDS,
    )
    consolidation_migrator_stub.setPairStatus(SOURCE_OPERATOR_ID, TARGET_OPERATOR_IDS[0], False, {"from": owner})


def test_consolidation_migrator_stub_overwrites_submitter_without_duplicate_target(
    owner,
    stranger,
    consolidation_migrator_stub,
):
    target_operator_id = TARGET_OPERATOR_IDS[0]

    consolidation_migrator_stub.allowPair(
        SOURCE_OPERATOR_ID,
        target_operator_id,
        owner.address,
        {"from": owner},
    )
    assert consolidation_migrator_stub.getSubmitter(SOURCE_OPERATOR_ID, target_operator_id) == owner.address
    assert consolidation_migrator_stub.getAllowedTargets(SOURCE_OPERATOR_ID) == [target_operator_id]

    consolidation_migrator_stub.allowPair(
        SOURCE_OPERATOR_ID,
        target_operator_id,
        stranger.address,
        {"from": owner},
    )
    assert consolidation_migrator_stub.getSubmitter(SOURCE_OPERATOR_ID, target_operator_id) == stranger.address
    assert consolidation_migrator_stub.getAllowedTargets(SOURCE_OPERATOR_ID) == [target_operator_id]

    consolidation_migrator_stub.disallowPair(SOURCE_OPERATOR_ID, target_operator_id, {"from": owner})
    assert consolidation_migrator_stub.getSubmitter(SOURCE_OPERATOR_ID, target_operator_id) == "0x0000000000000000000000000000000000000000"
    assert consolidation_migrator_stub.getAllowedTargets(SOURCE_OPERATOR_ID) == []


def test_create_evm_script(
    owner,
    allow_consolidation_pair_factory,
    consolidation_migrator_stub,
):
    calldata = _encode_input_with_submitter(owner.address)
    evm_script = allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})

    assert evm_script == _expected_evm_script(
        consolidation_migrator_stub,
        owner.address,
        TARGET_OPERATOR_IDS,
    )


def test_create_evm_script_with_single_target(owner, allow_consolidation_pair_factory, consolidation_migrator_stub):
    single_target_ids = [TARGET_OPERATOR_IDS[0]]
    calldata = _encode_input_with_submitter(owner.address, target_operator_ids=single_target_ids)
    evm_script = allow_consolidation_pair_factory.createEVMScript(owner, calldata, {"from": owner})

    assert evm_script == _expected_evm_script(
        consolidation_migrator_stub,
        owner.address,
        single_target_ids,
    )


def test_decode_evm_script_call_data(owner, allow_consolidation_pair_factory):
    calldata = _encode_input_with_submitter(owner.address)
    decoded = allow_consolidation_pair_factory.decodeEVMScriptCallData(calldata)
    assert decoded == (
        owner.address,
        SOURCE_OPERATOR_ID,
        TARGET_OPERATOR_IDS,
    )


def test_decode_evm_script_call_data_reverts_on_invalid_calldata(allow_consolidation_pair_factory):
    with reverts():
        allow_consolidation_pair_factory.decodeEVMScriptCallData("0x")
