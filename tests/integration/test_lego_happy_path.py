import pytest
import brownie

import constants
from utils import evm_script


@pytest.mark.skip_coverage
def test_lego_easy_track_happy_path(
    EVMScriptExecutor,
    TopUpLegoProgram,
    EasyTrack,
    lido_contracts,
    lego_program,
    accounts,
    deployer,
    stranger,
):
    ldo = lido_contracts.ldo
    steth = lido_contracts.steth
    acl = lido_contracts.aragon.acl
    agent = lido_contracts.aragon.agent
    voting = lido_contracts.aragon.voting
    finance = lido_contracts.aragon.finance

    trusted_address = accounts[7]

    # deploy easy track
    easy_track = deployer.deploy(
        EasyTrack,
        lido_contracts.ldo,
        deployer,
        constants.MIN_MOTION_DURATION,
        constants.MAX_MOTIONS_LIMIT,
        constants.DEFAULT_OBJECTIONS_THRESHOLD,
    )

    # deploy evm script executor
    evm_script_executor = deployer.deploy(EVMScriptExecutor, lido_contracts.aragon.calls_script, easy_track)
    evm_script_executor.transferOwnership(voting, {"from": deployer})
    assert evm_script_executor.owner() == voting

    # set EVM script executor in easy track
    easy_track.setEVMScriptExecutor(evm_script_executor, {"from": deployer})

    # deploy TopUpLegoProgram EVM script factory
    top_up_lego_program = deployer.deploy(TopUpLegoProgram, trusted_address, finance, lego_program)

    # add TopUpLegoProgram evm script to registry
    new_immediate_payment_permission = finance.address + finance.newImmediatePayment.signature[2:]
    easy_track.addEVMScriptFactory(top_up_lego_program, new_immediate_payment_permission, {"from": deployer})
    evm_script_factories = easy_track.getEVMScriptFactories()
    assert len(evm_script_factories) == 1
    assert evm_script_factories[0] == top_up_lego_program

    # create voting to grant permissions to EVM script executor to create new payments
    add_create_payments_permissions_voting_id, _ = lido_contracts.create_voting(
        evm_script=evm_script.encode_call_script(
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
        tx_params={"from": agent},
    )

    # execute voting to add permissions to EVM script executor to create payments
    lido_contracts.execute_voting(add_create_payments_permissions_voting_id)

    # create new motion to make transfers to lego programs
    ldo_amount, steth_amount, eth_amount = 10**18, 2 * 10**18, 3 * 10**18

    tx = easy_track.createMotion(
        top_up_lego_program,
        evm_script.encode_calldata(
            ["address[]", "uint256[]"],
            [
                [ldo.address, steth.address, brownie.ZERO_ADDRESS],
                [ldo_amount, steth_amount, eth_amount],
            ],
        ),
        {"from": trusted_address},
    )

    motions = easy_track.getMotions()
    assert len(motions) == 1

    brownie.chain.sleep(48 * 60 * 60 + 100)

    # top up agent balances
    ldo.approve(agent, ldo_amount, {"from": agent})
    agent.deposit(ldo, ldo_amount, {"from": agent})

    steth.submit(brownie.ZERO_ADDRESS, {"from": deployer, "value": "2.1 ether"})
    steth.approve(agent, "2.1 ether", {"from": deployer})
    agent.deposit(steth, steth_amount, {"from": deployer})

    agent.deposit(brownie.ZERO_ADDRESS, eth_amount, {"from": deployer, "value": eth_amount})

    # validate agent app has enough tokens
    assert agent.balance(ldo) >= ldo_amount
    assert agent.balance(steth) >= steth_amount
    assert agent.balance(brownie.ZERO_ADDRESS) >= eth_amount

    assert ldo.balanceOf(lego_program) == 0
    assert steth.balanceOf(lego_program) == 0
    lego_program_balance_before = lego_program.balance()

    easy_track.enactMotion(
        motions[0][0],
        tx.events["MotionCreated"]["_evmScriptCallData"],
        {"from": stranger},
    )

    assert len(easy_track.getMotions()) == 0
    assert ldo.balanceOf(lego_program) == ldo_amount
    assert abs(steth.balanceOf(lego_program) - steth_amount) <= 10
    assert lego_program.balance() - lego_program_balance_before == eth_amount
