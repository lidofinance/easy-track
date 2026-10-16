from brownie import chain, network
from utils import deployment, constants, lido
from utils.config import get_is_live, get_deployer_account, prompt_bool

# In case when custom dev net deployment is required, fill in these variables.
# If a value is not set, default addresses from utils.lido.contracts(active_network) will be used.

ADMIN_ADDRESS = None
GOVERNANCE_TOKEN_ADDRESS = None
ARAGON_CALLS_SCRIPT_ADDRESS = None

# Easy Track Config Params

MOTION_DURATION = constants.INITIAL_MOTION_DURATION
MOTIONS_COUNT_LIMIT = constants.INITIAL_MOTIONS_COUNT_LIMIT
OBJECTIONS_THRESHOLD = constants.INITIAL_OBJECTIONS_THRESHOLD

# Optional Easy Track Params

PAUSER_ADDRESS = None
CANCELLER_ADDRESS = None
ADDITIONAL_ADMIN_ADDRESS = None

# Tx Params

PRIORITY_FEE = "4 gwei"


def main():
    active_network = network.show_active()

    if not active_network:
        print("Network is not set properly. Aborting...")
        return

    lido_contracts = lido.contracts(active_network)
    deployer = get_deployer_account(is_live=get_is_live(), network=active_network)

    admin = ADMIN_ADDRESS or lido_contracts.aragon.voting
    governance_token = GOVERNANCE_TOKEN_ADDRESS or lido_contracts.ldo
    aragon_calls_script = ARAGON_CALLS_SCRIPT_ADDRESS or lido_contracts.aragon.calls_script
    grants = easy_track_role_grants(admin, PAUSER_ADDRESS, CANCELLER_ADDRESS, ADDITIONAL_ADMIN_ADDRESS)

    print("Network Config")
    print(f"  - Current network: {active_network} (chain id: {chain.id})")
    print(f"  - Deployer: {deployer}")
    print()

    print("Easy Track Config")
    print(f"  - Motion Duration: {MOTION_DURATION} seconds")
    print(f"  - Motions Count Limit: {MOTIONS_COUNT_LIMIT}")
    print(f"  - Objections Threshold: {OBJECTIONS_THRESHOLD}")
    print()

    print("Easy Track Required Params")
    print(f"  - Easy Track Admin: {admin}")
    print(f"  - Governance Token: {governance_token}")
    print(f"  - Aragon CallsScript instance: {aragon_calls_script}")
    print()

    print("Easy Track Roles After Deployment")
    for role_name, holder in grants:
        print(f"  - {role_name}: {holder}")
    print("  - UNPAUSE_ROLE: no holder, the admin grants it on demand")
    print("  - Deployer: renounces every role")
    print()

    print("Proceed? [y/n]: ")

    if not prompt_bool():
        print("Aborting")
        return

    tx_params = {"priority_fee": PRIORITY_FEE, "from": deployer}

    print("🚀 Deploying EasyTrack & EVMScriptExecutor contracts\n")

    easy_track, evm_script_executor = deploy_core_easy_track_contracts(
        admin=admin,
        governance_token=governance_token,
        aragon_calls_script=aragon_calls_script,
        motion_duration=MOTION_DURATION,
        motions_count_limit=MOTIONS_COUNT_LIMIT,
        objections_threshold=OBJECTIONS_THRESHOLD,
        tx_params=tx_params,
        pauser=PAUSER_ADDRESS,
        canceller=CANCELLER_ADDRESS,
        additional_admin=ADDITIONAL_ADMIN_ADDRESS,
    )

    print(f"\n  🟢 Deployed EasyTrack instance: {easy_track}")
    print(f"  🟢 Deployed EVMScriptExecutor instance: {evm_script_executor}\n")

    print("✅ Contracts successfully deployed & validated!\n")


def easy_track_role_grants(admin, pauser=None, canceller=None, additional_admin=None):
    """Ordered (role_name, holder) pairs granted before the deployer renounces its own roles.

    UNPAUSE_ROLE deliberately gets no holder: unpausing is a governance action, so the admin grants it on demand."""
    grants = [("DEFAULT_ADMIN_ROLE", admin)]
    if additional_admin is not None:
        grants.append(("DEFAULT_ADMIN_ROLE", additional_admin))
    if pauser is not None:
        grants.append(("PAUSE_ROLE", pauser))
    if canceller is not None:
        grants.append(("CANCEL_ROLE", canceller))
    return grants


def deploy_core_easy_track_contracts(
    admin,
    governance_token,
    aragon_calls_script,
    motion_duration,
    motions_count_limit,
    objections_threshold,
    tx_params,
    pauser=None,
    canceller=None,
    additional_admin=None,
):
    deployer = tx_params["from"]
    # the deployer is admin only while wiring the executor; every role is handed off below
    easy_track = deployment.deploy_easy_track(
        admin=deployer,
        governance_token=governance_token,
        motion_duration=motion_duration,
        motions_count_limit=motions_count_limit,
        objections_threshold=objections_threshold,
        tx_params=tx_params,
    )
    evm_script_executor = deployment.deploy_evm_script_executor(
        owner=admin, easy_track=easy_track, aragon_calls_script=aragon_calls_script, tx_params=tx_params
    )

    grants = easy_track_role_grants(admin, pauser, canceller, additional_admin)
    receipts = deployment.handoff_easy_track_roles(
        easy_track=easy_track,
        deployer=deployer,
        grants=grants,
        tx_params=tx_params,
    )
    deployment.validate_easy_track_deployment(
        easy_track,
        evm_script_executor,
        governance_token=governance_token,
        aragon_calls_script=aragon_calls_script,
        executor_owner=admin,
        motion_duration=motion_duration,
        motions_count_limit=motions_count_limit,
        objections_threshold=objections_threshold,
        expected_role_holders=deployment.expected_role_holders_from_grants(grants),
        deployer=deployer,
        receipts=[easy_track.tx, *receipts],
    )
    return easy_track, evm_script_executor
