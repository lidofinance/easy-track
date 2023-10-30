import os
from typing import Optional, NamedTuple, Any

import pytest
import brownie
from brownie import chain

import constants
from utils.evm_script import encode_call_script, encode_calldata
from utils.lido import contracts, external_contracts
from utils.config import get_network_name
from utils import test_helpers, deployed_date_time

brownie.web3.enable_strict_bytes_type_checking()

####################################
# Brownie Blockchain State Snapshots
####################################

# autouse, so enabled by default for all test modules in this directory


@pytest.fixture(scope="module", autouse=True)
def mod_isolation(module_isolation):
    """Snapshot ganache at start of module."""
    pass


@pytest.fixture(autouse=True)
def isolation(fn_isolation):
    """Snapshot ganache before every test function call."""
    pass


##############
# CONSTANTS
##############


@pytest.fixture(scope="module")
def holder_balance_amount(ldo):
    """Amount initially distributed to LDO holder accounts."""
    # By having this as a separate fixture, we can override it in
    # lower levels to change the amount distributed to holders
    # without having to modify the `distribute_holder_balance` fixture
    total_supply = ldo.totalSupply()
    holder_balance = total_supply / 500  # 0.2 %
    return holder_balance


##############
# ACCOUNTS
##############


@pytest.fixture(scope="session")
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def stranger(accounts):
    return accounts[5]


@pytest.fixture(scope="session")
def node_operator(accounts):
    return accounts[4]


@pytest.fixture(scope="session")
def ldo_holders(accounts):
    holders = accounts[6:9]
    return holders


@pytest.fixture(scope="session")
def lego_program(accounts):
    return accounts[3]


##############
# CONTRACTS
##############


@pytest.fixture(scope="module")
def lido_contracts():
    return contracts(network=brownie.network.show_active())


@pytest.fixture(scope="module")
def motion_settings(owner, MotionSettings):
    return owner.deploy(
        MotionSettings,
        owner,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )


@pytest.fixture(scope="module")
def evm_script_factories_registry(owner, EVMScriptFactoriesRegistry):
    return owner.deploy(EVMScriptFactoriesRegistry, owner)


@pytest.fixture(scope="module")
def easy_track(owner, ldo, voting, EasyTrack, EVMScriptExecutor, calls_script):
    contract = owner.deploy(
        EasyTrack,
        ldo,
        voting,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )
    evm_script_executor = owner.deploy(EVMScriptExecutor, calls_script, contract)
    contract.setEVMScriptExecutor(evm_script_executor, {"from": voting})
    return contract


@pytest.fixture(scope="module")
def evm_script_executor(owner, easy_track, calls_script, EVMScriptExecutor):
    return EVMScriptExecutor.at(easy_track.evmScriptExecutor())


@pytest.fixture(scope="module")
def reward_programs_registry(
    owner, voting, evm_script_executor_stub, RewardProgramsRegistry
):
    return owner.deploy(
        RewardProgramsRegistry,
        voting,
        [voting, evm_script_executor_stub],
        [voting, evm_script_executor_stub],
    )


############
# EVM SCRIPT FACTORIES
############


@pytest.fixture(scope="module")
def increase_node_operator_staking_limit(
    owner, node_operators_registry_stub, IncreaseNodeOperatorStakingLimit
):
    return owner.deploy(IncreaseNodeOperatorStakingLimit, node_operators_registry_stub)


@pytest.fixture(scope="module")
def add_reward_program(owner, reward_programs_registry, AddRewardProgram):
    return owner.deploy(AddRewardProgram, owner, reward_programs_registry)


@pytest.fixture(scope="module")
def remove_reward_program(owner, reward_programs_registry, RemoveRewardProgram):
    return owner.deploy(RemoveRewardProgram, owner, reward_programs_registry)


@pytest.fixture(scope="module")
def top_up_reward_programs(
    owner, finance, ldo, reward_programs_registry, TopUpRewardPrograms
):
    return owner.deploy(
        TopUpRewardPrograms, owner, reward_programs_registry, finance, ldo
    )


@pytest.fixture(scope="module")
def top_up_lego_program(owner, finance, lego_program, TopUpLegoProgram):
    return owner.deploy(TopUpLegoProgram, owner, finance, lego_program)


@pytest.fixture(scope="module")
def add_allowed_recipients(owner, allowed_recipients_registry, AddAllowedRecipient):
    (registry, _, _, _, _, _) = allowed_recipients_registry
    return owner.deploy(AddAllowedRecipient, owner, registry)


@pytest.fixture(scope="module")
def remove_allowed_recipients(
    owner, allowed_recipients_registry, RemoveAllowedRecipient
):
    (registry, _, _, _, _, _) = allowed_recipients_registry
    return owner.deploy(RemoveAllowedRecipient, owner, registry)


############
# MOCKS AND TEST WRAPPERS
############


@pytest.fixture(scope="module")
def evm_script_creator_wrapper(accounts, EVMScriptCreatorWrapper):
    return accounts[0].deploy(EVMScriptCreatorWrapper)


@pytest.fixture(scope="module")
def evm_script_permissions_wrapper(accounts, EVMScriptPermissionsWrapper):
    return accounts[0].deploy(EVMScriptPermissionsWrapper)


@pytest.fixture(scope="module")
def bytes_utils_wrapper(accounts, BytesUtilsWrapper):
    return accounts[0].deploy(BytesUtilsWrapper)


@pytest.fixture(scope="module")
def node_operators_registry_stub(owner, node_operator, NodeOperatorsRegistryStub):
    return owner.deploy(NodeOperatorsRegistryStub, node_operator)


@pytest.fixture(scope="module")
def evm_script_factory_stub(owner, EVMScriptFactoryStub):
    return owner.deploy(EVMScriptFactoryStub)


@pytest.fixture(scope="module")
def evm_script_executor_stub(owner, EVMScriptExecutorStub):
    return owner.deploy(EVMScriptExecutorStub)


@pytest.fixture(scope="module")
def limits_checker(owner, accounts, LimitsChecker, bokkyPooBahsDateTimeContract):
    set_parameters_role_holder = accounts[8]
    update_spent_amount_role_holder = accounts[9]
    limits_checker = owner.deploy(
        LimitsChecker,
        [set_parameters_role_holder],
        [update_spent_amount_role_holder],
        bokkyPooBahsDateTimeContract,
    )
    return (limits_checker, set_parameters_role_holder, update_spent_amount_role_holder)


@pytest.fixture(scope="module")
def limits_checker_with_private_method_exposed(
    owner, accounts, LimitsCheckerWithPrivateViewsExposed, bokkyPooBahsDateTimeContract
):
    set_parameters_role_holder = accounts[8]
    update_spent_amount_role_holder = accounts[9]
    limits_checker = owner.deploy(
        LimitsCheckerWithPrivateViewsExposed,
        [set_parameters_role_holder],
        [update_spent_amount_role_holder],
        bokkyPooBahsDateTimeContract,
    )
    return (limits_checker, set_parameters_role_holder, update_spent_amount_role_holder)


@pytest.fixture(scope="module")
def allowed_recipients_registry(
    AllowedRecipientsRegistry, bokkyPooBahsDateTimeContract, owner, accounts
):
    add_recipient_role_holder = accounts[6]
    remove_recipient_role_holder = accounts[7]
    set_limit_role_holder = accounts[8]
    update_spent_role_holder = accounts[9]

    registry = owner.deploy(
        AllowedRecipientsRegistry,
        owner,
        [add_recipient_role_holder],
        [remove_recipient_role_holder],
        [set_limit_role_holder],
        [update_spent_role_holder],
        bokkyPooBahsDateTimeContract,
    )

    return (
        registry,
        owner,
        add_recipient_role_holder,
        remove_recipient_role_holder,
        set_limit_role_holder,
        update_spent_role_holder,
    )


@pytest.fixture(scope="module")
def allowed_tokens_registry(AllowedTokensRegistry, owner, accounts):
    add_token_role_holder = accounts[6]
    remove_token_role_holder = accounts[7]

    registry = owner.deploy(
        AllowedTokensRegistry,
        owner,
        [add_token_role_holder],
        [remove_token_role_holder],
    )

    return (registry, owner, add_token_role_holder, remove_token_role_holder)


@pytest.fixture(scope="module")
def top_up_allowed_recipients(
    allowed_recipients_registry,
    allowed_tokens_registry,
    accounts,
    finance,
    easy_track,
    TopUpAllowedRecipients,
):
    (recipients_registry, owner, _, _, _, _) = allowed_recipients_registry
    (tokens_registry, _, _, _) = allowed_tokens_registry

    trusted_caller = accounts[4]

    top_up_factory = owner.deploy(
        TopUpAllowedRecipients,
        trusted_caller,
        recipients_registry,
        tokens_registry,
        finance,
        easy_track,
    )

    return top_up_factory


##########
# INTERFACES
##########


@pytest.fixture(scope="module")
def ldo(lido_contracts):
    return lido_contracts.ldo


@pytest.fixture(scope="module")
def steth(lido_contracts):
    return lido_contracts.steth


@pytest.fixture(scope="module")
def usdc():
    return external_contracts(network=brownie.network.show_active())["usdc"]

@pytest.fixture(scope="module")
def dai():
    return external_contracts(network=brownie.network.show_active())["dai"]


@pytest.fixture(scope="module")
def node_operators_registry(lido_contracts):
    return lido_contracts.node_operators_registry


@pytest.fixture(scope="module")
def voting(lido_contracts):
    return lido_contracts.aragon.voting


@pytest.fixture(scope="module")
def tokens(lido_contracts):
    return lido_contracts.aragon.token_manager


@pytest.fixture(scope="module")
def agent(lido_contracts):
    return lido_contracts.aragon.agent


@pytest.fixture(scope="module")
def finance(lido_contracts):
    return lido_contracts.aragon.finance


@pytest.fixture(scope="module")
def acl(lido_contracts):
    return lido_contracts.aragon.acl


@pytest.fixture(scope="module")
def calls_script(lido_contracts):
    return lido_contracts.aragon.calls_script


#########################
# State Changing Fixtures
#########################

# Non-deployment fixtures with side-effects
# Have them module scoped if you want the changes to persist across tests within a module
# Or function scoped for their changes to be rolled-back after test execution


@pytest.fixture(scope="function")
def distribute_holder_balance(ldo_holders, holder_balance_amount, fund_with_ldo):
    for holder in ldo_holders:
        fund_with_ldo(holder, holder_balance_amount)


############################
# Helper/Functional Fixtures
############################

# NOTE: the function returned can modify state, but the factory fixture itself shouldn't


@pytest.fixture(scope="module")
def fund_with_ldo(ldo, agent):
    # NOTE: module scope because it depends on ldo, agent
    # but the fixture doesn't change state when executed - only returns a function

    def method(account, amount):
        ldo.transfer(account, amount, {"from": agent})

    return method


class Helpers:
    @staticmethod
    def execute_vote(
        accounts, vote_id, dao_voting, ldo_vote_executors_for_tests, topup="0.1 ether"
    ):
        if dao_voting.getVote(vote_id)[0]:
            for holder_addr in ldo_vote_executors_for_tests:
                print("voting from acct:", holder_addr)
                accounts[0].transfer(holder_addr, topup)
                account = accounts.at(holder_addr, force=True)
                dao_voting.vote(vote_id, True, False, {"from": account})

        # wait for the vote to end
        chain.sleep(3 * 60 * 60 * 24)
        chain.mine()

        assert dao_voting.canExecute(vote_id)
        tx = dao_voting.executeVote(vote_id, {"from": accounts[0]})

        print(f"vote #{vote_id} executed")
        return tx


@pytest.fixture(scope="module")
def helpers():
    return Helpers


@pytest.fixture(scope="module")
def vote_id_from_env() -> Optional[int]:
    _env_name = "OMNIBUS_VOTE_ID"
    if os.getenv(_env_name):
        try:
            vote_id = int(os.getenv(_env_name))
            print(f"OMNIBUS_VOTE_ID env var is set, using existing vote #{vote_id}")
            return vote_id
        except:
            pass

    return None


@pytest.fixture(scope="module")
def bokkyPooBahsDateTimeContract():
    return deployed_date_time.date_time_contract(network=brownie.network.show_active())
