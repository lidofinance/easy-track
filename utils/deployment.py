from dataclasses import dataclass
from brownie import (
    chain,
    interface,
    web3,
    ZERO_ADDRESS,
    EasyTrack,
    TopUpLegoProgram,
    EVMScriptExecutor,
    AddRewardProgram,
    RemoveRewardProgram,
    TopUpRewardPrograms,
    RewardProgramsRegistry,
    IncreaseNodeOperatorStakingLimit,
    AddAllowedRecipient,
    RemoveAllowedRecipient,
    TopUpAllowedRecipientsSingleToken,
    AllowedRecipientsRegistry,
)
from brownie.convert import to_address
from hexbytes import HexBytes
from utils import log

# Every role EasyTrack grants to `_admin` in its constructor, DEFAULT_ADMIN_ROLE last so it is renounced last
EASY_TRACK_ROLE_NAMES = ("PAUSE_ROLE", "UNPAUSE_ROLE", "CANCEL_ROLE", "DEFAULT_ADMIN_ROLE")


@dataclass
class AllowedRecipientsSingleTokenDeployConfig:
    token: str
    limit: int
    period: int
    spent_amount: int
    trusted_caller: str


@dataclass
class AllowedRecipientsSingleTokenSingleRecipientSetupDeployConfig(AllowedRecipientsSingleTokenDeployConfig):
    title: str


@dataclass
class AllowedRecipientsSingleTokenFullSetupDeployConfig(AllowedRecipientsSingleTokenDeployConfig):
    titles: list[str]
    recipients: list[str]


@dataclass
class AllowedRecipientsMultiTokenDeployConfig:
    tokens: [str]
    tokens_registry: str
    limit: int
    period: int
    spent_amount: int
    trusted_caller: str

@dataclass
class AllowedRecipientsMultiTokenSingleRecipientSetupDeployConfig(AllowedRecipientsMultiTokenDeployConfig):
    title: str

@dataclass
class AllowedRecipientsMultiTokenFullSetupDeployConfig(AllowedRecipientsMultiTokenDeployConfig):
    titles: [str]
    recipients: [str]
    grant_rights: bool


def _addr(value):
    return to_address(str(value))


def _role_hash(value):
    return str(value).lower()


def _easy_track_role_hashes(easy_track):
    return {name: _role_hash(getattr(easy_track, name)()) for name in EASY_TRACK_ROLE_NAMES}


def assert_governance_token_supports_snapshots(governance_token):
    """Fail before deploying anything if the token lacks the MiniMe snapshot views EasyTrack relies on."""
    token = interface.MiniMeToken(_addr(governance_token))
    token.balanceOfAt(ZERO_ADDRESS, chain.height)
    # objectToMotion divides by the total supply snapshot
    assert token.totalSupplyAt(chain.height) > 0, "governance token has zero total supply"


def deploy_easy_track(
    admin,
    governance_token,
    motion_duration,
    motions_count_limit,
    objections_threshold,
    tx_params,
):
    assert_governance_token_supports_snapshots(governance_token)
    return EasyTrack.deploy(
        governance_token,
        admin,
        motion_duration,
        motions_count_limit,
        objections_threshold,
        tx_params,
    )


def deploy_evm_script_executor(owner, easy_track, aragon_calls_script, tx_params):
    evm_script_executor = EVMScriptExecutor.deploy(aragon_calls_script, easy_track, tx_params)
    evm_script_executor.transferOwnership(owner, tx_params)
    easy_track.setEVMScriptExecutor(evm_script_executor, tx_params)
    return evm_script_executor


def handoff_easy_track_roles(easy_track, deployer, grants, tx_params):
    """Grant every (role_name, holder) in `grants` while the deployer is still admin, then renounce all
    EasyTrack roles from the deployer. Returns the receipts so the resulting role holders can be replayed."""
    deployer = _addr(deployer)
    assert _addr(tx_params["from"]) == deployer, "role handoff must be sent by the deployer"
    assert all(_addr(holder) != deployer for _, holder in grants), "deployer must not keep any EasyTrack role"

    role_hashes = _easy_track_role_hashes(easy_track)
    receipts = [easy_track.grantRole(role_hashes[name], holder, tx_params) for name, holder in grants]
    receipts += [easy_track.renounceRole(role_hashes[name], deployer, tx_params) for name in EASY_TRACK_ROLE_NAMES]
    return receipts


def expected_role_holders_from_grants(grants):
    holders = {name: set() for name in EASY_TRACK_ROLE_NAMES}
    for name, holder in grants:
        holders[name].add(_addr(holder))
    return holders


def easy_track_role_holders_from_receipts(easy_track, receipts):
    """Replay RoleGranted/RoleRevoked emitted by `easy_track` across `receipts` in log order.

    For a freshly deployed EasyTrack, the deployment receipt plus every receipt sent since give the
    exact holder set of each role, which AccessControl cannot enumerate on-chain."""
    names_by_hash = {role_hash: name for name, role_hash in _easy_track_role_hashes(easy_track).items()}
    holders = {name: set() for name in EASY_TRACK_ROLE_NAMES}
    for receipt in receipts:
        for event in receipt.events:
            if event.name not in ("RoleGranted", "RoleRevoked") or _addr(event.address) != _addr(easy_track):
                continue
            role_hash = _role_hash(event["role"])
            assert role_hash in names_by_hash, f"unexpected EasyTrack role {role_hash}"
            role_holders = holders[names_by_hash[role_hash]]
            account = _addr(event["account"])
            if event.name == "RoleGranted":
                role_holders.add(account)
            else:
                role_holders.discard(account)
    return holders


def validate_easy_track_deployment(
    easy_track,
    evm_script_executor,
    *,
    governance_token,
    aragon_calls_script,
    executor_owner,
    motion_duration,
    motions_count_limit,
    objections_threshold,
    expected_role_holders,
    deployer,
    receipts,
):
    """Assert the deployed pair is bound to the selected inputs and that each EasyTrack role is held
    exactly by `expected_role_holders`: replayed from `receipts` (deployment receipt included), then
    confirmed on-chain. The deployer must hold no role."""
    deployer = _addr(deployer)
    aragon_calls_script = _addr(aragon_calls_script)

    assert _addr(easy_track.governanceToken()) == _addr(governance_token), "governanceToken mismatch"
    assert _addr(easy_track.evmScriptExecutor()) == _addr(evm_script_executor), "evmScriptExecutor mismatch"
    log.ok("EasyTrack governanceToken", easy_track.governanceToken())
    log.ok("EasyTrack evmScriptExecutor", easy_track.evmScriptExecutor())

    assert _addr(evm_script_executor.easyTrack()) == _addr(easy_track), "executor easyTrack mismatch"
    assert _addr(evm_script_executor.owner()) == _addr(executor_owner), "executor owner mismatch"
    assert _addr(evm_script_executor.callsScript()) == aragon_calls_script, "executor callsScript mismatch"
    # aragonOS CallsScript identifies itself by this executor type
    assert HexBytes(interface.CallsScript(aragon_calls_script).executorType()) == web3.keccak(
        text="CALLS_SCRIPT"
    ), "callsScript is not an aragonOS CallsScript"
    log.ok("EVMScriptExecutor easyTrack", evm_script_executor.easyTrack())
    log.ok("EVMScriptExecutor owner", evm_script_executor.owner())
    log.ok("EVMScriptExecutor callsScript", evm_script_executor.callsScript())

    assert easy_track.motionDuration() == motion_duration, "motionDuration mismatch"
    assert easy_track.motionsCountLimit() == motions_count_limit, "motionsCountLimit mismatch"
    assert easy_track.objectionsThreshold() == objections_threshold, "objectionsThreshold mismatch"
    log.ok("EasyTrack motionDuration", easy_track.motionDuration())
    log.ok("EasyTrack motionsCountLimit", easy_track.motionsCountLimit())
    log.ok("EasyTrack objectionsThreshold", easy_track.objectionsThreshold())

    expected = {name: {_addr(holder) for holder in holders} for name, holders in expected_role_holders.items()}
    assert set(expected) == set(EASY_TRACK_ROLE_NAMES), "expected_role_holders must cover every EasyTrack role"
    assert all(deployer not in holders for holders in expected.values()), "deployer must not be an expected holder"
    replayed = easy_track_role_holders_from_receipts(easy_track, receipts)
    for name in EASY_TRACK_ROLE_NAMES:
        assert replayed[name] == expected[name], f"{name} holders {sorted(replayed[name])} != {sorted(expected[name])}"
        role = getattr(easy_track, name)()
        assert all(easy_track.hasRole(role, holder) for holder in expected[name]), f"{name} not granted on-chain"
        assert not easy_track.hasRole(role, deployer), f"deployer still holds {name}"
        log.ok(f"EasyTrack {name} holders", ", ".join(sorted(expected[name])) or "none")

    assert not easy_track.paused(), "EasyTrack is paused"
    log.ok("EasyTrack paused", False)


def deploy_reward_programs_registry(voting, evm_script_executor, tx_params):
    return RewardProgramsRegistry.deploy(
        voting, [voting, evm_script_executor], [voting, evm_script_executor], tx_params
    )


def deploy_allowed_recipients_registry(voting, evm_script_executor, date_time_contract, tx_params):
    return AllowedRecipientsRegistry.deploy(
        voting,
        [voting, evm_script_executor],
        [voting, evm_script_executor],
        [voting],
        [evm_script_executor],
        date_time_contract,
        tx_params,
    )


def deploy_increase_node_operator_staking_limit(node_operators_registry, tx_params):
    return IncreaseNodeOperatorStakingLimit.deploy(node_operators_registry, tx_params)


def deploy_top_up_lego_program(finance, lego_program, lego_committee_multisig, tx_params):
    return TopUpLegoProgram.deploy(lego_committee_multisig, finance, lego_program, tx_params)


def deploy_add_reward_program(reward_programs_registry, reward_programs_multisig, tx_params):
    return AddRewardProgram.deploy(reward_programs_multisig, reward_programs_registry, tx_params)


def deploy_remove_reward_program(reward_programs_registry, reward_programs_multisig, tx_params):
    return RemoveRewardProgram.deploy(reward_programs_multisig, reward_programs_registry, tx_params)


def deploy_top_up_reward_programs(
    finance,
    governance_token,
    reward_programs_registry,
    reward_programs_multisig,
    tx_params,
):
    return TopUpRewardPrograms.deploy(
        reward_programs_multisig,
        reward_programs_registry,
        finance,
        governance_token,
        tx_params,
    )


def deploy_add_allowed_recipient(allowed_recipients_registry, committee_multisig, tx_params):
    return AddAllowedRecipient.deploy(committee_multisig, allowed_recipients_registry, tx_params)


def deploy_remove_allowed_recipient(allowed_recipients_registry, committee_multisig, tx_params):
    return RemoveAllowedRecipient.deploy(committee_multisig, allowed_recipients_registry, tx_params)


def deploy_top_up_allowed_recipients(
    finance,
    governance_token,
    allowed_recipients_registry,
    committee_multisig,
    easy_track,
    tx_params,
):
    return TopUpAllowedRecipientsSingleToken.deploy(
        committee_multisig,
        allowed_recipients_registry,
        finance,
        governance_token,
        easy_track,
        tx_params,
    )


def add_evm_script_factories(
    easy_track,
    add_reward_program,
    top_up_lego_program,
    remove_reward_program,
    top_up_reward_programs,
    reward_programs_registry,
    increase_node_operator_staking_limit,
    lido_contracts,
    tx_params,
):
    easy_track.addEVMScriptFactory(
        increase_node_operator_staking_limit,
        create_permission(lido_contracts.node_operators_registry, "setNodeOperatorStakingLimit"),
        tx_params,
    )
    easy_track.addEVMScriptFactory(
        top_up_lego_program,
        create_permission(lido_contracts.aragon.finance, "newImmediatePayment"),
        tx_params,
    )
    add_evm_script_reward_program_factories(
        easy_track,
        add_reward_program,
        remove_reward_program,
        top_up_reward_programs,
        reward_programs_registry,
        lido_contracts,
        tx_params,
    )


def add_evm_script_reward_program_factories(
    easy_track,
    add_reward_program,
    remove_reward_program,
    top_up_reward_programs,
    reward_programs_registry,
    lido_contracts,
    tx_params,
):
    easy_track.addEVMScriptFactory(
        top_up_reward_programs,
        create_permission(lido_contracts.aragon.finance, "newImmediatePayment"),
        tx_params,
    )
    easy_track.addEVMScriptFactory(
        add_reward_program,
        create_permission(reward_programs_registry, "addRewardProgram"),
        tx_params,
    )
    easy_track.addEVMScriptFactory(
        remove_reward_program,
        create_permission(reward_programs_registry, "removeRewardProgram"),
        tx_params,
    )


def attach_evm_script_allowed_recipients_factories(
    easy_track,
    add_allowed_recipient,
    remove_allowed_recipient,
    top_up_allowed_recipients,
    allowed_recipients_registry,
    finance,
    tx_params,
):
    new_immediate_payment_permission = create_permission(finance, "newImmediatePayment")

    update_limit_permission = create_permission(allowed_recipients_registry, "updateSpentAmount")
    permissions = new_immediate_payment_permission + update_limit_permission[2:]

    easy_track.addEVMScriptFactory(
        top_up_allowed_recipients,
        permissions,
        tx_params,
    )
    easy_track.addEVMScriptFactory(
        add_allowed_recipient,
        create_permission(allowed_recipients_registry, "addRecipient"),
        tx_params,
    )
    easy_track.addEVMScriptFactory(
        remove_allowed_recipient,
        create_permission(allowed_recipients_registry, "removeRecipient"),
        tx_params,
    )


def create_permission(contract, method):
    return contract.address + getattr(contract, method).signature[2:]
