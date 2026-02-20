import pytest
from brownie import reverts, SettleGeneralDelayedPenalty, ZERO_ADDRESS  # type: ignore

from utils.evm_script import encode_call_script, encode_calldata
from utils.test_helpers import set_account_balance


FACTORY_NAME = "MODULE"
PENALTY_TYPE = "0x" + "11" * 32


def create_calldata(ids, amounts):
    return encode_calldata(["uint256[]", "uint256[]"], [ids, amounts])


@pytest.fixture(scope="module", params=["cs_module", "curated_module"])
def module_case(request):
    return request.param


@pytest.fixture(scope="module")
def module(request, module_case):
    return request.getfixturevalue(module_case)


@pytest.fixture(scope="module")
def factory(owner, module):
    return SettleGeneralDelayedPenalty.deploy(owner, FACTORY_NAME, module, {"from": owner})


@pytest.fixture()
def fill_module(module, owner):
    admin = module.getRoleMember(module.DEFAULT_ADMIN_ROLE(), 0)
    set_account_balance(admin)
    if module.isPaused():
        module.grantRole(module.RESUME_ROLE(), owner, {"from": admin})
        module.resume({"from": owner})
    if module.getNodeOperatorsCount() == 0:
        module.addNodeOperatorETH(
            1,
            # some random pubkey and signature
            "0x8bb1db218877a42047b953bdc32573445a78d93383ef5fd08f79c066d4781961db4f5ab5a7cc0cf1e4cbcc23fd17f9d7",
            "0xad17ef7cdf0c4917aaebc067a785b049d417dda5d4dd66395b21bbd50781d51e28ee750183eca3d32e1f57b324049a06135ad07d1aa243368bca9974e25233f050e0d6454894739f87faace698b90ea65ee4baba2758772e09fec4f1d8d35660",
            [ZERO_ADDRESS, ZERO_ADDRESS, False],
            [],
            ZERO_ADDRESS,
            {"from": owner, "value": 32 * 10**18}
        )
    reporter = module.getRoleMember(module.REPORT_GENERAL_DELAYED_PENALTY_ROLE(), 0)
    module.reportGeneralDelayedPenalty(
        0,
        PENALTY_TYPE,
        32 * 10**18,
        "test",
        {"from": reporter}
    )


def test_deploy(owner, module, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.module() == module
    assert factory.name() == FACTORY_NAME


def test_create_evm_script_called_by_stranger(stranger, factory):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    EVM_SCRIPT_CALLDATA = "0x"
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, EVM_SCRIPT_CALLDATA)


def test_empty_calldata(owner, factory):
    EMPTY_CALLDATA = create_calldata([], [])
    with reverts("EMPTY_NODE_OPERATORS_IDS"):
        factory.createEVMScript(owner, EMPTY_CALLDATA)


def test_operator_id_out_of_range(owner, factory, module):
    "Must revert with message 'OUT_OF_RANGE_NODE_OPERATOR_ID' when operator id gt operators count"
    node_operators_count = module.getNodeOperatorsCount()
    CALLDATA = create_calldata([node_operators_count], [1])
    with reverts("OUT_OF_RANGE_NODE_OPERATOR_ID"):
        factory.createEVMScript(owner, CALLDATA)


def test_create_evm_script(owner, factory, module, fill_module):
    "Must create correct EVMScript if all requirements are met"
    node_operator_ids = [0]
    max_amounts = [1000 * 10 ** 18]

    EVM_SCRIPT_CALLDATA = create_calldata(node_operator_ids, max_amounts)
    evm_script = factory.createEVMScript(owner, EVM_SCRIPT_CALLDATA)
    expected_evm_script = encode_call_script(
        [(module.address, module.settleGeneralDelayedPenalty.encode_input(node_operator_ids, max_amounts))]
    )

    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory):
    "Must decode EVMScript call data correctly"
    node_operator_ids = [0, 1, 2]
    max_amounts = [1000, 2000, 3000]

    EVM_SCRIPT_CALLDATA = create_calldata(node_operator_ids, max_amounts)
    decoded_ids, decoded_amounts = factory.decodeEVMScriptCallData(EVM_SCRIPT_CALLDATA)
    assert decoded_ids == node_operator_ids
    assert decoded_amounts == max_amounts


def test_node_operators_ids_and_max_amounts_length_mismatch(owner, factory):
    "Must revert with message 'NODE_OPERATORS_IDS_AND_MAX_AMOUNTS_LENGTH_MISMATCH' when arrays have different lengths"
    node_operator_ids = [0, 1]
    max_amounts = [1000]  # Different length

    CALLDATA = create_calldata(node_operator_ids, max_amounts)
    with reverts("NODE_OPERATORS_IDS_AND_MAX_AMOUNTS_LENGTH_MISMATCH"):
        factory.createEVMScript(owner, CALLDATA)


def test_max_amount_should_be_greater_than_zero(owner, factory, fill_module):
    "Must revert with message 'MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO' when max amount is zero"
    node_operator_ids = [0]
    max_amounts = [0]  # Zero amount

    CALLDATA = create_calldata(node_operator_ids, max_amounts)
    with reverts("MAX_AMOUNT_SHOULD_BE_GREATER_THAN_ZERO"):
        factory.createEVMScript(owner, CALLDATA)


def test_max_amount_should_be_greater_than_actual_locked(owner, factory, module, fill_module):
    "Must revert with message 'MAX_AMOUNT_SHOULD_BE_GREATER_OR_EQUAL_THAN_ACTUAL_LOCKED' when max amount is less than actual locked"
    node_operator_ids = [0]
    max_amounts = [1]

    CALLDATA = create_calldata(node_operator_ids, max_amounts)
    with reverts("MAX_AMOUNT_SHOULD_BE_GREATER_OR_EQUAL_THAN_ACTUAL_LOCKED"):
        factory.createEVMScript(owner, CALLDATA)
