from utils.evm_script import encode_call_script, EMPTY_CALLSCRIPT
from utils.config import ldo_token_address


def create_vote(voting, token_manager, vote_desc, evm_script, tx_params):
    new_vote_script = encode_call_script([(
        voting.address,
        voting.newVote.encode_input(
            evm_script if evm_script is not None else EMPTY_CALLSCRIPT,
            vote_desc,
            False,
            False
        )
    )])
    tx = token_manager.forward(new_vote_script, tx_params)
    vote_id = tx.events['StartVote']['voteId']
    return (vote_id, tx)


def encode_token_transfer(token_address, recipient, amount, reference, finance):
    return (
        finance.address,
        finance.newImmediatePayment.encode_input(
            token_address,
            recipient,
            amount,
            reference
        )
    )


def encode_permission_grant(target_app, permission_name, to, acl):
    permission_id = getattr(target_app, permission_name)()
    return (acl.address, acl.grantPermission.encode_input(to, target_app, permission_id))


def propose_vesting_manager_contract(
    manager_address,
    total_ldo_amount,
    ldo_transfer_reference,
    acl,
    voting,
    finance,
    token_manager,
    tx_params
):
    evm_script = encode_call_script([
        encode_token_transfer(
            token_address=ldo_token_address,
            recipient=manager_address,
            amount=total_ldo_amount,
            reference=ldo_transfer_reference,
            finance=finance
        ),
        encode_permission_grant(
            target_app=token_manager,
            permission_name='ASSIGN_ROLE',
            to=manager_address,
            acl=acl
        )
    ])
    return create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=f'Make {manager_address} a vesting manager for total {total_ldo_amount} LDO',
        evm_script=evm_script,
        tx_params=tx_params
    )
