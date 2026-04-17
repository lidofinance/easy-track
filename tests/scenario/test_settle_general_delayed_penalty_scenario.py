import pytest
import brownie
from brownie import AccountingStub, BaseModuleStub, SettleGeneralDelayedPenalty

from utils.evm_script import encode_calldata


FACTORY_NAME = "CSM v3"
GENERAL_DELAYED_PENALTY_SETTLED_TOPIC0 = brownie.web3.keccak(
    text="GeneralDelayedPenaltySettled(uint256[],uint256[])"
).hex()


def create_calldata(node_operator_ids, max_amounts):
    return encode_calldata(["uint256[]", "uint256[]"], [node_operator_ids, max_amounts])


@pytest.fixture(scope="module")
def accounting(owner, use_deployed_contracts_from_env, active_cs_module):
    if use_deployed_contracts_from_env:
        return brownie.interface.IAccounting(active_cs_module.ACCOUNTING())

    return owner.deploy(AccountingStub)


@pytest.fixture(scope="module")
def module(
    owner,
    use_deployed_contracts_from_env,
    active_cs_module,
    accounting,
    ensure_module_in_staking_router,
    ensure_module_unpaused,
):
    if use_deployed_contracts_from_env:
        ensure_module_in_staking_router(active_cs_module, "CSM")
        ensure_module_unpaused(active_cs_module)
        return active_cs_module

    module = owner.deploy(BaseModuleStub)
    module.mock_setNodeOperatorsCount(1000, {"from": owner})
    module.mock_setAccounting(accounting.address, {"from": owner})
    # Pre-set locked bond so `ensure_module_locked_bond` short-circuits for the stub path.
    accounting.mock_setLockedBond(0, 1000, {"from": owner})
    return module


@pytest.fixture(scope="module")
def node_operator_id(module, ensure_module_operator):
    return ensure_module_operator(module)


@pytest.fixture(scope="module")
def settle_general_delayed_penalty_factory(
    owner,
    commitee_multisig,
    voting,
    et_contracts,
    module,
):
    factory = owner.deploy(
        SettleGeneralDelayedPenalty,
        commitee_multisig,
        FACTORY_NAME,
        module.address,
    )

    permissions = module.address + module.settleGeneralDelayedPenalty.signature[2:]
    et_contracts.easy_track.addEVMScriptFactory(factory.address, permissions, {"from": voting})
    assert et_contracts.easy_track.isEVMScriptFactory(factory.address)

    return factory


def test_settle_general_delayed_penalty_scenario(
    commitee_multisig,
    easytrack_executor,
    module,
    accounting,
    node_operator_id,
    use_deployed_contracts_from_env,
    settle_general_delayed_penalty_factory,
    ensure_module_locked_bond,
):
    node_operator_ids = [node_operator_id]
    ensure_module_locked_bond(module, node_operator_ids[0], 10**16)
    locked_before = accounting.getLockedBond(node_operator_ids[0])
    assert locked_before > 0
    max_amounts = [locked_before]
    evm_script_calldata = create_calldata(node_operator_ids, max_amounts)

    tx = easytrack_executor(
        commitee_multisig,
        settle_general_delayed_penalty_factory,
        evm_script_calldata,
    )

    has_settle_event = False
    for log in tx.logs:
        log_address = log.get("address")
        topics = log.get("topics", [])
        if not topics:
            continue
        topic0 = topics[0]
        topic0 = topic0.hex() if hasattr(topic0, "hex") else str(topic0)
        if not topic0.startswith("0x"):
            topic0 = "0x" + topic0
        if (
            log_address.lower() == module.address.lower()
            and topic0.lower() == GENERAL_DELAYED_PENALTY_SETTLED_TOPIC0.lower()
        ):
            has_settle_event = True
            break

    assert has_settle_event, "GeneralDelayedPenaltySettled event was not found in raw logs"

    if not use_deployed_contracts_from_env:
        assert module.lastSettledCount() == 1
        assert module.lastSettledFirstNodeOperatorId() == node_operator_ids[0]
        assert module.lastSettledFirstMaxAmount() == max_amounts[0]
    assert accounting.getLockedBond(node_operator_ids[0]) == 0
