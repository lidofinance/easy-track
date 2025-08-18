import pytest
from brownie import reverts, CSMSettleElStealingPenalty, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata
from utils.test_helpers import set_account_balance

def create_calldata(ids, amounts):
    return encode_calldata(["uint256[]", "uint256[]"], [ids, amounts])


@pytest.fixture(scope="module")
def csm_settle_el_stealing_penalty_factory(owner, cs_module):
    return CSMSettleElStealingPenalty.deploy(owner, cs_module, {"from": owner})

@pytest.fixture()
def fill_cs_module(cs_module, owner):
    admin = cs_module.getRoleMember(cs_module.DEFAULT_ADMIN_ROLE(), 0)
    set_account_balance(admin)
    if cs_module.isPaused():
        cs_module.grantRole(cs_module.RESUME_ROLE(), owner, {"from": admin})
        cs_module.resume({"from": owner})
    if cs_module.getNodeOperatorsCount() == 0:
        cs_module.addNodeOperatorETH(
            1,
            # some random pubkey and signature
            "0x8bb1db218877a42047b953bdc32573445a78d93383ef5fd08f79c066d4781961db4f5ab5a7cc0cf1e4cbcc23fd17f9d7",
            "0xad17ef7cdf0c4917aaebc067a785b049d417dda5d4dd66395b21bbd50781d51e28ee750183eca3d32e1f57b324049a06135ad07d1aa243368bca9974e25233f050e0d6454894739f87faace698b90ea65ee4baba2758772e09fec4f1d8d35660",
            [ZERO_ADDRESS, ZERO_ADDRESS, False],
            [],
            ZERO_ADDRESS,
            {"from": owner, "value": 32 * 10**18}
        )
    reporter = cs_module.getRoleMember(cs_module.REPORT_EL_REWARDS_STEALING_PENALTY_ROLE(), 0)
    cs_module.reportELRewardsStealingPenalty(
        0,
        "0x98072b6713156c15b02608fa7301c86ecd37affde73356623fdba88a23e2abdb",
        32 * 10**18,
        {"from": reporter}
    )


def test_deploy(owner, cs_module, csm_settle_el_stealing_penalty_factory):
    "Must deploy contract with correct data"
    assert csm_settle_el_stealing_penalty_factory.trustedCaller() == owner
    assert csm_settle_el_stealing_penalty_factory.csm() == cs_module


def test_create_evm_script_called_by_stranger(stranger, csm_settle_el_stealing_penalty_factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        csm_settle_el_stealing_penalty_factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_calldata(owner, csm_settle_el_stealing_penalty_factory):
    EMPTY_CALLDATA = create_calldata([], [])
    with reverts('EMPTY_NODE_OPERATORS_IDS'):
        csm_settle_el_stealing_penalty_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_operator_id_out_of_range(owner, csm_settle_el_stealing_penalty_factory, cs_module):
    "Must revert with message 'OUT_OF_RANGE_NODE_OPERATOR_ID' when operator id gt operators count"

    node_operators_count = cs_module.getNodeOperatorsCount()
    CALLDATA = create_calldata([node_operators_count], [1])
    with reverts('OUT_OF_RANGE_NODE_OPERATOR_ID'):
        csm_settle_el_stealing_penalty_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, csm_settle_el_stealing_penalty_factory, cs_module, fill_cs_module):
    "Must create correct EVMScript if all requirements are met"
    node_operator_ids = [0]
    max_amounts = [33 * 10 ** 18]

    EVM_SCRIPT_CALLDATA = create_calldata(node_operator_ids, max_amounts)
    evm_script = csm_settle_el_stealing_penalty_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(cs_module.address, cs_module.settleELRewardsStealingPenalty.encode_input(node_operator_ids, max_amounts))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(csm_settle_el_stealing_penalty_factory):
    "Must decode EVMScript call data correctly"
    node_operator_ids = [0, 1, 2]
    max_amounts = [1000, 2000, 3000]

    EVM_SCRIPT_CALLDATA = create_calldata(node_operator_ids, max_amounts)
    decoded_ids, decoded_amounts = csm_settle_el_stealing_penalty_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    assert decoded_ids == node_operator_ids
    assert decoded_amounts == max_amounts


def test_node_operators_ids_and_max_amounts_length_mismatch(owner, csm_settle_el_stealing_penalty_factory):
    "Must revert with message 'NODE_OPERATORS_IDS_AND_MAX_AMOUNTS_LENGTH_MISMATCH' when arrays have different lengths"
    node_operator_ids = [0, 1]
    max_amounts = [1000]  # Different length
    
    CALLDATA = create_calldata(node_operator_ids, max_amounts)
    with reverts('NODE_OPERATORS_IDS_AND_MAX_AMOUNTS_LENGTH_MISMATCH'):
        csm_settle_el_stealing_penalty_factory.createEVMScript(owner, CALLDATA)


def test_max_amount_should_be_greater_than_zero(owner, csm_settle_el_stealing_penalty_factory, fill_cs_module):
    "Must revert with message 'MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO' when max amount is zero"
    node_operator_ids = [0]
    max_amounts = [0]  # Zero amount
    
    CALLDATA = create_calldata(node_operator_ids, max_amounts)
    with reverts('MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO'):
        csm_settle_el_stealing_penalty_factory.createEVMScript(owner, CALLDATA)

def test_max_amount_should_be_greater_than_actual_locked(owner, csm_settle_el_stealing_penalty_factory, cs_module, fill_cs_module):
    "Must revert with message 'MAX_AMOUNT_SHOULD_BE_GREATER_OR_EQUAL_THAN_ACTUAL_LOCKED' when max amount is less than actual locked"
    node_operator_ids = [0]
    max_amounts = [1]

    CALLDATA = create_calldata(node_operator_ids, max_amounts)
    with reverts('MAX_AMOUNT_SHOULD_BE_GREATER_OR_EQUAL_THAN_ACTUAL_LOCKED'):
        csm_settle_el_stealing_penalty_factory.createEVMScript(owner, CALLDATA)
