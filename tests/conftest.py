import os
from typing import Optional

import pytest
import brownie
from brownie import chain, EasyTrack, EVMScriptExecutor

import constants
from utils.evm_script import encode_call_script, encode_calldata
from utils.lido import contracts, create_voting, execute_voting
from utils.config import get_network_name
from utils import test_helpers

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
    # Have this as a fixture to cache the result.
    return contracts()


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
def easy_track(owner, ldo, voting, evm_script_executor_stub, EasyTrack):
    contract = owner.deploy(
        EasyTrack,
        ldo,
        voting,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )
    contract.setEVMScriptExecutor(evm_script_executor_stub, {"from": voting})
    return contract


@pytest.fixture(scope="module")
def evm_script_executor(owner, easy_track, calls_script, EVMScriptExecutor):
    return owner.deploy(EVMScriptExecutor, calls_script, easy_track)


@pytest.fixture(scope="module")
def reward_programs_registry(owner, voting, evm_script_executor_stub, RewardProgramsRegistry):
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
def top_up_reward_programs(owner, finance, ldo, reward_programs_registry, TopUpRewardPrograms):
    return owner.deploy(TopUpRewardPrograms, owner, reward_programs_registry, finance, ldo)


@pytest.fixture(scope="module")
def top_up_lego_program(owner, finance, lego_program, TopUpLegoProgram):
    return owner.deploy(TopUpLegoProgram, owner, finance, lego_program)


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
    set_limits_role_holder = accounts[8]
    update_spent_amount_role_holder = accounts[9]
    limits_checker = owner.deploy(
        LimitsChecker,
        [set_limits_role_holder],
        [update_spent_amount_role_holder],
        bokkyPooBahsDateTimeContract,
    )
    return (limits_checker, set_limits_role_holder, update_spent_amount_role_holder)


@pytest.fixture(scope="module")
def limits_checker_with_private_method_exposed(
    owner, accounts, LimitsCheckerWrapper, bokkyPooBahsDateTimeContract
):
    set_limits_role_holder = accounts[8]
    update_spent_amount_role_holder = accounts[9]
    limits_checker = owner.deploy(
        LimitsCheckerWrapper,
        [set_limits_role_holder],
        [update_spent_amount_role_holder],
        bokkyPooBahsDateTimeContract,
    )
    return (limits_checker, set_limits_role_holder, update_spent_amount_role_holder)


@pytest.fixture(scope="module")
def entire_allowed_recipients_setup(
    accounts,
    owner,
    ldo,
    voting,
    calls_script,
    finance,
    agent,
    acl,
    bokkyPooBahsDateTimeContract,
    AllowedRecipientsRegistry,
    TopUpAllowedRecipients,
    AddAllowedRecipient,
    RemoveAllowedRecipient,
):
    deployer = owner
    trusted_factories_caller = accounts[7]

    def create_permission(contract, method):
        return contract.address + getattr(contract, method).signature[2:]

    # deploy easy track
    easy_track = deployer.deploy(
        EasyTrack,
        ldo,
        deployer,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )

    # deploy evm script executor
    evm_script_executor = deployer.deploy(EVMScriptExecutor, calls_script, easy_track)
    evm_script_executor.transferOwnership(voting, {"from": deployer})
    assert evm_script_executor.owner() == voting

    # set EVM script executor in easy track
    easy_track.setEVMScriptExecutor(evm_script_executor, {"from": deployer})

    # deploy AllowedRecipientsRegistry
    allowed_recipients_registry = deployer.deploy(
        AllowedRecipientsRegistry,
        voting,
        [voting, evm_script_executor],
        [voting, evm_script_executor],
        [voting, evm_script_executor],
        [voting, evm_script_executor],
        bokkyPooBahsDateTimeContract,
    )

    # deploy TopUpAllowedRecipients EVM script factory
    top_up_allowed_recipients = deployer.deploy(
        TopUpAllowedRecipients,
        trusted_factories_caller,
        allowed_recipients_registry,
        finance,
        ldo,
        easy_track,
    )

    # add TopUpAllowedRecipients EVM script factory to easy track
    new_immediate_payment_permission = create_permission(finance, "newImmediatePayment")

    update_limit_permission = create_permission(allowed_recipients_registry, "updateSpentAmount")

    permissions = new_immediate_payment_permission + update_limit_permission[2:]

    easy_track.addEVMScriptFactory(top_up_allowed_recipients, permissions, {"from": deployer})

    # deploy AddAllowedRecipient EVM script factory
    add_allowed_recipient = deployer.deploy(
        AddAllowedRecipient, trusted_factories_caller, allowed_recipients_registry
    )

    # add AddAllowedRecipient EVM script factory to easy track
    add_allowed_recipient_permission = create_permission(
        allowed_recipients_registry, "addRecipient"
    )

    easy_track.addEVMScriptFactory(
        add_allowed_recipient, add_allowed_recipient_permission, {"from": deployer}
    )

    # deploy RemoveAllowedRecipient EVM script factory
    remove_allowed_recipient = deployer.deploy(
        RemoveAllowedRecipient, trusted_factories_caller, allowed_recipients_registry
    )

    # add RemoveAllowedRecipient EVM script factory to easy track
    remove_allowed_recipient_permission = create_permission(
        allowed_recipients_registry, "removeRecipient"
    )
    easy_track.addEVMScriptFactory(
        remove_allowed_recipient, remove_allowed_recipient_permission, {"from": deployer}
    )

    # create voting to grant permissions to EVM script executor to create new payments
    network_name = get_network_name()

    add_create_payments_permissions_voting_id, _ = create_voting(
        evm_script=encode_call_script(
            [
                (
                    acl.address,
                    acl.grantPermission.encode_input(
                        evm_script_executor,
                        finance,
                        finance.CREATE_PAYMENTS_ROLE(),
                    ),
                ),
            ]
        ),
        description="Grant permissions to EVMScriptExecutor to make payments",
        network=network_name,
        tx_params={"from": agent},
    )

    # execute voting to add permissions to EVM script executor to create payments
    execute_voting(add_create_payments_permissions_voting_id, network_name)

    return (
        easy_track,
        evm_script_executor,
        allowed_recipients_registry,
        top_up_allowed_recipients,
        add_allowed_recipient,
        remove_allowed_recipient,
    )


@pytest.fixture(scope="module")
def entire_allowed_recipients_setup_with_two_recipients(
    entire_allowed_recipients_setup, accounts, stranger
):
    (
        easy_track,
        evm_script_executor,
        allowed_recipients_registry,
        top_up_allowed_recipients,
        add_allowed_recipient,
        remove_allowed_recipient,
    ) = entire_allowed_recipients_setup

    recipient1 = accounts[8]
    recipient1_title = "Recipient 1"
    recipient2 = accounts[9]
    recipient2_title = "Recipient 2"

    tx = easy_track.createMotion(
        add_allowed_recipient,
        encode_calldata("(address,string)", [recipient1.address, recipient1_title]),
        {"from": add_allowed_recipient.trustedCaller()},
    )
    motion1_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    tx = easy_track.createMotion(
        add_allowed_recipient,
        encode_calldata("(address,string)", [recipient2.address, recipient2_title]),
        {"from": add_allowed_recipient.trustedCaller()},
    )
    motion2_calldata = tx.events["MotionCreated"]["_evmScriptCallData"]

    chain.sleep(constants.MIN_MOTION_DURATION + 100)

    easy_track.enactMotion(
        easy_track.getMotions()[0][0],
        motion1_calldata,
        {"from": stranger},
    )
    easy_track.enactMotion(
        easy_track.getMotions()[0][0],
        motion2_calldata,
        {"from": stranger},
    )
    assert allowed_recipients_registry.getAllowedRecipients() == [recipient1, recipient2]

    return (
        easy_track,
        evm_script_executor,
        allowed_recipients_registry,
        top_up_allowed_recipients,
        add_allowed_recipient,
        remove_allowed_recipient,
        recipient1,
        recipient2,
    )


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
    return "0x23d23d8f243e57d0b924bff3a3191078af325101"
