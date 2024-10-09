import pytest
from brownie import reverts, CSMSettleElStealingPenalty, ZERO_ADDRESS # type: ignore

from utils.evm_script import encode_call_script, encode_calldata
from utils.test_helpers import set_account_balance

def create_calldata(ids):
    return encode_calldata(["uint256[]"], [ids])


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
    if not cs_module.publicRelease():
        cs_module.grantRole(cs_module.MODULE_MANAGER_ROLE(), owner, {"from": admin})
        cs_module.activatePublicRelease({"from": owner})
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
    EMPTY_CALLDATA = create_calldata([])
    with reverts('EMPTY_NODE_OPERATORS_IDS'):
        csm_settle_el_stealing_penalty_factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_operator_id_out_of_range(owner, csm_settle_el_stealing_penalty_factory, cs_module):
    "Must revert with message 'OUT_OF_RANGE_NODE_OPERATOR_ID' when operator id gt operators count"

    node_operators_count = cs_module.getNodeOperatorsCount()
    CALLDATA = create_calldata([node_operators_count])
    with reverts('OUT_OF_RANGE_NODE_OPERATOR_ID'):
        csm_settle_el_stealing_penalty_factory.createEVMScript(owner, CALLDATA)

def test_create_evm_script(owner, csm_settle_el_stealing_penalty_factory, cs_module, fill_cs_module):
    "Must create correct EVMScript if all requirements are met"
    input_params = [0]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params)
    evm_script = csm_settle_el_stealing_penalty_factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(cs_module.address, cs_module.settleELRewardsStealingPenalty.encode_input(input_params))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(csm_settle_el_stealing_penalty_factory):
    "Must decode EVMScript call data correctly"
    input_params = [0, 1, 2]

    EVM_SCRIPT_CALLDATA = create_calldata(input_params)
    assert csm_settle_el_stealing_penalty_factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA) == input_params
