import pytest
import brownie
from eth_abi import encode
from brownie import SDVTSubmitExitRequestHashes, NodeOperatorsRegistryStub, ZERO_ADDRESS, convert, web3
from utils.evm_script import encode_calldata, encode_call_script

NODE_OPERATOR_ID = 1


class ExitRequestInput:
    def __init__(self, module_id, node_op_id, val_index, val_pubkey, val_pubkey_index):
        self.module_id = module_id
        self.node_op_id = node_op_id
        self.val_index = val_index
        self.val_pubkey = val_pubkey
        self.val_pubkey_index = val_pubkey_index

    def to_tuple(self):
        return (self.module_id, self.node_op_id, self.val_index, self.val_pubkey, self.val_pubkey_index)


def pubkey_to_bytes(pubkey):
    return "0x" + convert.to_bytes(pubkey, "bytes").hex()


@pytest.fixture(scope="module")
def sdvt(owner, node_operator, staking_router_stub, submit_exit_hashes_factory_config):
    registry = NodeOperatorsRegistryStub.deploy(node_operator, {"from": owner})
    staking_router_stub.setStakingModule(
        submit_exit_hashes_factory_config["module_ids"]["sdvt"], registry.address, {"from": owner}
    )

    registry.setSigningKey(NODE_OPERATOR_ID, submit_exit_hashes_factory_config["pubkeys"][0])

    return registry


@pytest.fixture(scope="module")
def sdvt_submit_exit_request_hashes(owner, staking_router_stub, sdvt, validator_exit_bus_oracle):
    return SDVTSubmitExitRequestHashes.deploy(
        owner,
        staking_router_stub,
        sdvt,
        validator_exit_bus_oracle,
        {"from": owner},
    )


def create_calldata(exit_request_inputs: list[ExitRequestInput]):
    return encode_calldata(
        ["(uint256,uint256,uint64,bytes,uint256)[]"],
        [exit_request_inputs],
    )


def create_exit_requests_hashes(requests, data_format=1):
    """
    requests: list of objects with attributes
      - moduleId: int
      - nodeOpId: int
      - valIndex: int
      - valPubkey: str or bytes (48-byte hex str with '0x' or raw bytes)
    """

    # helper to normalize pubkey to raw bytes
    def _pub(r):
        if isinstance(r.val_pubkey, str):
            h = r.val_pubkey[2:] if r.val_pubkey.startswith("0x") else r.val_pubkey
            return bytes.fromhex(h)
        return r.val_pubkey

    packed = b"".join(
        r.module_id.to_bytes(3, "big") + r.node_op_id.to_bytes(5, "big") + r.val_index.to_bytes(8, "big") + _pub(r)
        for r in requests
    )

    # abi.encode(bytes, uint256) then keccak256
    digest = web3.keccak(encode(["bytes", "uint256"], [packed, data_format]))
    return digest.hex()


## ---- Deployment tests ----


def test_deploy(
    owner,
    staking_router_stub,
    sdvt,
    validator_exit_bus_oracle,
    SDVTSubmitExitRequestHashes,
):
    "Must deploy contract with correct data"
    contract = owner.deploy(SDVTSubmitExitRequestHashes, owner, staking_router_stub, sdvt, validator_exit_bus_oracle)

    assert contract.trustedCaller() == owner
    assert contract.stakingRouter() == staking_router_stub
    assert contract.validatorsExitBusOracle() == validator_exit_bus_oracle
    assert contract.sdvtNodeOperatorsRegistry() == sdvt


def test_deploy_zero_staking_router_stub(
    owner,
    sdvt,
    validator_exit_bus_oracle,
):
    "Must deploy contract with zero staking router"
    contract = SDVTSubmitExitRequestHashes.deploy(
        owner,
        ZERO_ADDRESS,
        sdvt,
        validator_exit_bus_oracle,
        {"from": owner},
    )
    assert contract.stakingRouter() == ZERO_ADDRESS


def test_deploy_zero_validator_exit_bus_oracle(
    owner,
    staking_router_stub,
    sdvt,
):
    "Must deploy contract with zero validator exit bus oracle"
    contract = SDVTSubmitExitRequestHashes.deploy(owner, staking_router_stub, sdvt, ZERO_ADDRESS, {"from": owner})
    assert contract.validatorsExitBusOracle() == ZERO_ADDRESS


def test_deploy_zero_node_operators_registry(
    owner,
    staking_router_stub,
    validator_exit_bus_oracle,
):
    "Must deploy contract with zero node operators registry"
    contract = SDVTSubmitExitRequestHashes.deploy(
        owner, staking_router_stub, ZERO_ADDRESS, validator_exit_bus_oracle, {"from": owner}
    )
    assert contract.sdvtNodeOperatorsRegistry() == ZERO_ADDRESS


## ---- EVM Script Calldata decoding ----


def test_decode_calldata(sdvt_submit_exit_request_hashes, submit_exit_hashes_factory_config):
    "Must decode calldata correctly"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    exit_request_inputs = [
        ExitRequestInput(sdvt_module_id, 2, 3, submit_exit_hashes_factory_config["pubkeys"][0], 0),
        ExitRequestInput(sdvt_module_id, 6, 7, submit_exit_hashes_factory_config["pubkeys"][0], 0),
    ]

    calldata = create_calldata([req.to_tuple() for req in exit_request_inputs])

    decoded_data = sdvt_submit_exit_request_hashes.decodeEVMScriptCallData(calldata)
    request_input_with_bytes = [
        (req.module_id, req.node_op_id, req.val_index, pubkey_to_bytes(req.val_pubkey), req.val_pubkey_index)
        for req in exit_request_inputs
    ]

    assert decoded_data == request_input_with_bytes


def test_decode_calldata_empty(sdvt_submit_exit_request_hashes):
    "Must revert decoding empty calldata"
    with brownie.reverts():
        sdvt_submit_exit_request_hashes.decodeEVMScriptCallData("0x")


def test_decode_calldata_is_permissionless(
    stranger, submit_exit_hashes_factory_config, sdvt_submit_exit_request_hashes
):
    "Must allow stranger to decode calldata"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    exit_request_inputs = [
        ExitRequestInput(sdvt_module_id, 2, 3, submit_exit_hashes_factory_config["pubkeys"][0], 0),
    ]

    calldata = create_calldata([req.to_tuple() for req in exit_request_inputs])
    decoded_data = sdvt_submit_exit_request_hashes.decodeEVMScriptCallData(calldata, {"from": stranger})

    request_input_with_bytes = [
        (req.module_id, req.node_op_id, req.val_index, pubkey_to_bytes(req.val_pubkey), req.val_pubkey_index)
        for req in exit_request_inputs
    ]

    assert decoded_data == request_input_with_bytes


# ## ---- EVM Script Creation ----


def test_create_evm_script(
    owner,
    submit_exit_hashes_factory_config,
    validator_exit_bus_oracle,
    sdvt_submit_exit_request_hashes,
):
    "Must create correct EVM script if all requirements are met"
    sdvt_module_id = submit_exit_hashes_factory_config["module_ids"]["sdvt"]

    exit_request_input = [
        ExitRequestInput(sdvt_module_id, NODE_OPERATOR_ID, 3, submit_exit_hashes_factory_config["pubkeys"][0], 0)
    ]

    calldata = create_calldata([req.to_tuple() for req in exit_request_input])
    evm_script = sdvt_submit_exit_request_hashes.createEVMScript(owner, calldata)

    exit_request_hash = create_exit_requests_hashes(exit_request_input)

    expected_evm_script = encode_call_script(
        [
            (
                validator_exit_bus_oracle.address,
                validator_exit_bus_oracle.submitExitRequestsHash.encode_input(exit_request_hash),
            )
        ]
    )

    assert evm_script == expected_evm_script
