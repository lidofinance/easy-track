import pytest
from eth_abi import encode
from eth_utils import keccak
from brownie import (
    reverts,
    ZERO_ADDRESS,
    LidoLendSetMarketExitBookAllowed,
    MorphoExitBookStub,
    Erc4626ExitBookStub,
    LidoLendVaultStub,
)

from utils.evm_script import encode_call_script

from utils.lido_lend import MARKET_PARAMS_ABI_TYPE as MP_TYPE
CALLDATA_TYPES = [MP_TYPE, "address", "bool"]

LOAN_TOKEN = f"0x{1:040x}"
COLLATERAL_TOKEN = f"0x{2:040x}"
ORACLE = f"0x{3:040x}"
IRM = f"0x{4:040x}"
LLTV = 800000000000000000

MARKET_PARAMS = (LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, IRM, LLTV)
MARKET_ID = keccak(encode([MP_TYPE], [MARKET_PARAMS]))
OTHER_MARKET_ID = keccak(b"other")


def create_calldata(market_params, vault, allowed):
    return "0x" + encode(CALLDATA_TYPES, [market_params, vault, allowed]).hex()


@pytest.fixture(scope="module")
def morpho_exit_book_stub(owner):
    return MorphoExitBookStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def erc4626_exit_book_stub(owner):
    return Erc4626ExitBookStub.deploy({"from": owner})


@pytest.fixture(scope="module")
def vault(owner):
    "A vault whose marketId matches MARKET_PARAMS (so the factory's cross-check passes)."
    v = LidoLendVaultStub.deploy({"from": owner})
    v.setMarketId(MARKET_ID, {"from": owner})
    return v


@pytest.fixture(scope="module")
def factory(owner, morpho_exit_book_stub, erc4626_exit_book_stub):
    return LidoLendSetMarketExitBookAllowed.deploy(
        owner, morpho_exit_book_stub, erc4626_exit_book_stub, {"from": owner}
    )


def test_deploy(owner, morpho_exit_book_stub, erc4626_exit_book_stub, factory):
    "Must deploy contract with correct data"
    assert factory.trustedCaller() == owner
    assert factory.morphoExitBook() == morpho_exit_book_stub
    assert factory.erc4626ExitBook() == erc4626_exit_book_stub


def test_create_evm_script_called_by_stranger(stranger, factory, vault):
    "Must revert with message 'CALLER_IS_FORBIDDEN' if creator isn't trustedCaller"
    calldata = create_calldata(MARKET_PARAMS, vault.address, True)
    with reverts("CALLER_IS_FORBIDDEN"):
        factory.createEVMScript(stranger, calldata)


def test_create_evm_script_zero_address(owner, factory, vault):
    "Must revert with the matching ZERO_* message if any required address is the zero address"
    cases = [
        ((ZERO_ADDRESS, COLLATERAL_TOKEN, ORACLE, IRM, LLTV), vault.address, "ZERO_LOAN_TOKEN"),
        ((LOAN_TOKEN, ZERO_ADDRESS, ORACLE, IRM, LLTV), vault.address, "ZERO_COLLATERAL_TOKEN"),
        ((LOAN_TOKEN, COLLATERAL_TOKEN, ZERO_ADDRESS, IRM, LLTV), vault.address, "ZERO_ORACLE"),
        ((LOAN_TOKEN, COLLATERAL_TOKEN, ORACLE, ZERO_ADDRESS, LLTV), vault.address, "ZERO_IRM"),
        (MARKET_PARAMS, ZERO_ADDRESS, "ZERO_VAULT"),
    ]
    for market_params, vlt, error in cases:
        with reverts(error):
            factory.createEVMScript(owner, create_calldata(market_params, vlt, True))


def test_create_evm_script_vault_market_mismatch(owner, factory):
    "Must revert with 'VAULT_MARKET_MISMATCH' if the vault does not belong to the given market"
    other = LidoLendVaultStub.deploy({"from": owner})
    other.setMarketId(OTHER_MARKET_ID, {"from": owner})
    with reverts("VAULT_MARKET_MISMATCH"):
        factory.createEVMScript(owner, create_calldata(MARKET_PARAMS, other.address, True))


@pytest.mark.parametrize("allowed", [True, False])
def test_create_evm_script(owner, morpho_exit_book_stub, erc4626_exit_book_stub, factory, vault, allowed):
    "Must create both exit-book calls in order, forwarding the target allowed state to each book"
    calldata = create_calldata(MARKET_PARAMS, vault.address, allowed)
    evm_script = factory.createEVMScript(owner, calldata)

    expected_evm_script = encode_call_script(
        [
            (
                morpho_exit_book_stub.address,
                morpho_exit_book_stub.setMarketAllowed.encode_input(MARKET_PARAMS, allowed),
            ),
            (
                erc4626_exit_book_stub.address,
                erc4626_exit_book_stub.setVaultAllowed.encode_input(vault.address, allowed),
            ),
        ]
    )
    assert evm_script == expected_evm_script


def test_decode_evm_script_call_data(factory, vault):
    "Must decode EVMScript call data correctly"
    calldata = create_calldata(MARKET_PARAMS, vault.address, True)
    market_params, decoded_vault, allowed = factory.decodeEVMScriptCallData(calldata)
    assert market_params == MARKET_PARAMS
    assert decoded_vault == vault.address
    assert allowed is True
