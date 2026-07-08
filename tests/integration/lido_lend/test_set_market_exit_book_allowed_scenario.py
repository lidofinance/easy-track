
import pytest
from brownie import LidoLendActivateMarket, LidoLendSetMarketExitBookAllowed, EasyTrack, accounts, web3
from eth_abi import encode

PAUSER_COMMITTEE = "0x" + "cc" * 20


def _market_params(lido_lend):
    m = lido_lend.market
    return (m["loanToken"], m["collateralToken"], m["oracle"], m["irm"], m["lltv"])


def _admin(lido_lend):
    a = accounts.at(lido_lend.admin, force=True)
    web3.provider.make_request("anvil_setBalance", [a.address, hex(10**22)])
    return a


def _register(easy_track, lido_lend, factory, perm):
    voting = accounts.at(lido_lend.easy_track_admin, force=True)
    web3.provider.make_request("anvil_setBalance", [voting.address, hex(10**22)])
    easy_track.addEVMScriptFactory(factory, perm, {"from": voting})


def _activate(lido_lend, deployer, trusted_caller, easy_track, enact_motion):
    "Create the market via an ActivateMarket motion (setMarketIrm -> createMarket -> registerPauser)."
    owner = lido_lend.contract("owner")
    irm_router = lido_lend.contract("irmRouter")
    circuit_breaker = lido_lend.contract("circuitBreaker")
    factory = deployer.deploy(LidoLendActivateMarket, trusted_caller, owner, irm_router, circuit_breaker)
    create_sel = web3.keccak(text="createMarket((address,address,address,address,uint256),address,bool)").hex()[2:10]
    perm = (
        "0x"
        + irm_router.address[2:] + irm_router.setMarketIrm.signature[2:]
        + owner.address[2:] + create_sel
        + circuit_breaker.address[2:] + circuit_breaker.registerPauser.signature[2:]
    )
    _register(easy_track, lido_lend, factory, perm)
    owner.grantRole(owner.MARKET_CREATOR_ROLE(), easy_track.evmScriptExecutor(), {"from": _admin(lido_lend)})
    calldata = "0x" + encode(
        ["(address,address,address,address,uint256)", "address", "address", "address", "bool"],
        [_market_params(lido_lend), lido_lend.market["curve"], lido_lend.market["controller"], PAUSER_COMMITTEE, True],
    ).hex()
    enact_motion(easy_track, factory, calldata, trusted_caller)


def test_set_market_exit_book_allowed_scenario(lido_lend, deployer, trusted_caller, enact_motion):
    "Allow-list a freshly-activated market on both exit books via one motion, then dis-allow via another."
    core = lido_lend.contract("core")
    m = lido_lend.market
    market_id = m["id"]

    if core.market(market_id)["lastUpdate"] != 0:
        pytest.skip("descriptor market already created on the core; this scenario activates a fresh market first")
    if not lido_lend.has("circuitBreaker") or not lido_lend.easy_track:
        pytest.skip("descriptor lacks circuitBreaker / real easyTrack; scenario needs both")
    circuit_breaker = lido_lend.contract("circuitBreaker")
    easy_track = EasyTrack.at(lido_lend.easy_track)
    if easy_track.evmScriptExecutor() != circuit_breaker.ADMIN():
        pytest.skip("descriptor easyTrack executor is not the CircuitBreaker admin; cannot activate here")

    morpho = lido_lend.contract("morphoExitBook")
    erc4626 = lido_lend.contract("erc4626ExitBook")

    _activate(lido_lend, deployer, trusted_caller, easy_track, enact_motion)
    assert core.market(market_id)["lastUpdate"] != 0
    assert not morpho.isMarketAllowed(market_id)
    assert not erc4626.isVaultAllowed(m["vault"])

    admin = _admin(lido_lend)
    executor = easy_track.evmScriptExecutor()
    morpho.grantRole(morpho.ALLOWLIST_MANAGER_ROLE(), executor, {"from": admin})
    erc4626.grantRole(erc4626.ALLOWLIST_MANAGER_ROLE(), executor, {"from": admin})

    factory = deployer.deploy(LidoLendSetMarketExitBookAllowed, trusted_caller, morpho, erc4626)
    perm = (
        "0x"
        + morpho.address[2:] + morpho.setMarketAllowed.signature[2:]
        + erc4626.address[2:] + erc4626.setVaultAllowed.signature[2:]
    )
    _register(easy_track, lido_lend, factory, perm)

    def calldata(allowed):
        return "0x" + encode(
            ["(address,address,address,address,uint256)", "address", "bool"],
            [_market_params(lido_lend), m["vault"], allowed],
        ).hex()

    enact_motion(easy_track, factory, calldata(True), trusted_caller)
    assert morpho.isMarketAllowed(market_id)
    assert erc4626.isVaultAllowed(m["vault"])

    enact_motion(easy_track, factory, calldata(False), trusted_caller)
    assert not morpho.isMarketAllowed(market_id)
    assert not erc4626.isVaultAllowed(m["vault"])
