import os
from brownie import interface, ZERO_ADDRESS, network

from utils.lido import contracts, all_permissions, create_voting, execute_voting
from utils.config import (
    get_env,
    get_is_live,
    get_deployer_account,
    prompt_bool,
)
from utils.evm_script import encode_call_script


def main():
    vote_id = revoke_all_permissions()
    os.environ["VOTING_ID"] = str(vote_id)
    check_permissions_revoked()

def revoke_all_permissions():
    deployer = get_deployer_account(get_is_live())
    evm_script_executor = get_env("EVM_SCRIPT_EXECUTOR")

    all_lido_permissions = all_permissions()
    acl = contracts()["dao"]["acl"]

    granted_permissions = [
        permission
        for permission in all_lido_permissions
        if acl.hasPermission(evm_script_executor, permission.app, permission.role)
    ]

    if len(granted_permissions) == 0:
        print(f"{evm_script_executor} has no granted roles. Exiting...")

    if len(granted_permissions) > 0:
        print(f"Create voting to revoke next roles from {evm_script_executor}:")
        for permission in granted_permissions:
            print(f"- {permission}")

    print("Proceed? [y/n]: ")
    if not prompt_bool():
        print("Aborting")
        return

    revoke_permissions_evmscript = encode_call_script(
        [
            (
                acl.address,
                acl.revokePermission.encode_input(
                    evm_script_executor, permission.app, permission.role
                ),
            )
            for permission in granted_permissions
        ]
    )

    vote_id, _ = create_voting(
        evm_script=revoke_permissions_evmscript,
        description="Revoke all permissions from {evm_script_executor}",
        tx_params={"from": deployer},
    )

    print(f"Vote successfully started! Vote id: {vote_id}")
    return vote_id

def check_permissions_revoked():
    voting_id = get_env("VOTING_ID")
    evm_script_executor = get_env("EVM_SCRIPT_EXECUTOR")
    
    acl = contracts()["dao"]["acl"]
    all_lido_permissions = all_permissions()

    execute_voting(voting_id)

    print(
        f"Validate that {evm_script_executor} has no granted permissions after voting is passed"
    )

    for permission in all_lido_permissions:
        assert not acl.hasPermission(evm_script_executor, permission.app, permission.role)
    print("Validation Passed!")
