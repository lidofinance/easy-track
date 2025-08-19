from utils import lido
from utils.evm_script import encode_call_script
from utils.config import get_env, get_is_live, get_deployer_account, prompt_bool


def main():
    deployer = get_deployer_account(get_is_live())
    evm_script_executor = get_env("EVM_SCRIPT_EXECUTOR")

    lido_contracts = lido.contracts(network="mainnet")
    lido_permissions = lido_contracts.permissions()
    all_lido_permissions = lido_permissions.all()
    granted_permissions = lido_permissions.filter_granted(all_lido_permissions, evm_script_executor)

    print("List of all lido permissions:")
    for permission in all_lido_permissions:
        print(permission)
    print()

    if len(granted_permissions) == 0:
        print(f"{evm_script_executor} has no granted roles. Exiting...")
        return

    if len(granted_permissions) > 0:
        print(f"Create voting to revoke next roles from {evm_script_executor}:")
        for permission in granted_permissions:
            print(f"- {permission}")

    print(f"Deployer: {deployer}")
    print(f"EVMScriptExecutor address: {evm_script_executor}")

    print("Proceed? [y/n]: ")
    if not prompt_bool():
        print("Aborting")
        return

    tx_params = {"from": deployer}
    vote_id = revoke_permissions(
        lido_contracts=lido_contracts,
        granted_permissions=granted_permissions,
        evm_script_executor=evm_script_executor,
        tx_params=tx_params,
    )
    print(f"Vote successfully started! Vote id: {vote_id}")


def revoke_permissions(lido_contracts, granted_permissions, evm_script_executor, tx_params):
    acl = lido_contracts.aragon.acl
    revoke_permissions_evmscript = encode_call_script(
        [
            (
                acl.address,
                acl.revokePermission.encode_input(evm_script_executor, permission.app, permission.role),
            )
            for permission in granted_permissions
        ]
    )

    vote_id, _ = lido_contracts.create_voting(
        evm_script=revoke_permissions_evmscript,
        description="Revoke all permissions from {evm_script_executor}",
        tx_params=tx_params,
    )

    return vote_id
