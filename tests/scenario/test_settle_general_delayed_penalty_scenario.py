import pytest
import brownie
from brownie import AccountingStub, BaseModuleStub, SettleGeneralDelayedPenalty, Wei

from utils.evm_script import encode_calldata


FACTORY_NAME = "CSM v3"
GENERAL_DELAYED_PENALTY_SETTLED_TOPIC0 = brownie.web3.keccak(
    text="GeneralDelayedPenaltySettled(uint256)"
).hex()


def create_calldata(lock_info_list):
    return encode_calldata(["(uint256,uint256)[]"], [lock_info_list])


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
    accounting.mock_setLock(0, Wei(1000), 42, {"from": owner})
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
    settle_general_delayed_penalty_factory,
    ensure_module_locked_bond,
):
    ensure_module_locked_bond(module, node_operator_id, 10**16)
    nonce = accounting.getBondLockNonce(node_operator_id)
    evm_script_calldata = create_calldata([(node_operator_id, nonce)])

    tx = easytrack_executor(
        commitee_multisig,
        settle_general_delayed_penalty_factory,
        evm_script_calldata,
    )

    assert "GeneralDelayedPenaltySettled" in tx.events, "GeneralDelayedPenaltySettled event not found"
    assert tx.events["GeneralDelayedPenaltySettled"]["nodeOperatorId"] == node_operator_id
    assert accounting.getLockedBond(node_operator_id) == 0
