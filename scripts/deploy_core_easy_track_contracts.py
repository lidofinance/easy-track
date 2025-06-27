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

    print("Easy Track Optional Params")
    print(f"  - Pauser address: {PAUSER_ADDRESS}")
    print(f"  - Canceller address: {CANCELLER_ADDRESS}")
    print(f"  - Easy Track Additional Admin: {ADDITIONAL_ADMIN_ADDRESS}")
    print()

    print("Proceed? [y/n]: ")

    if not prompt_bool():
        print("Aborting")
        return

    tx_params = {"priority_fee": PRIORITY_FEE, "from": deployer}

    print("🚀 Deploying EasyTrack & EVMScriptExecutor contracts\n")

    easy_track = deployment.deploy_easy_track(
        admin=deployer,  # temporary set admin to deployer and renounce roles later
        governance_token=governance_token,
        motion_duration=MOTION_DURATION,
        motions_count_limit=MOTIONS_COUNT_LIMIT,
        objections_threshold=OBJECTIONS_THRESHOLD,
        tx_params=tx_params,
    )
    evm_script_executor = deployment.deploy_evm_script_executor(
        owner=admin, easy_track=easy_track, aragon_calls_script=aragon_calls_script, tx_params=tx_params
    )

    print(f"  🟢 Deployed EasyTrack instance: {easy_track}")
    print(f"  🟢 Deployed EVMScriptExecutor instance: {evm_script_executor}\n")

    # grant permissions

    pause_role = easy_track.PAUSE_ROLE()
    cancel_role = easy_track.CANCEL_ROLE()
    default_admin_role = easy_track.DEFAULT_ADMIN_ROLE()

    easy_track.grantRole(default_admin_role, admin, tx_params)

    if ADDITIONAL_ADMIN_ADDRESS is not None:
        easy_track.grantRole(default_admin_role, ADDITIONAL_ADMIN_ADDRESS, tx_params)

    if PAUSER_ADDRESS is not None:
        easy_track.grantRole(pause_role, PAUSER_ADDRESS, tx_params)

    if CANCELLER_ADDRESS is not None:
        easy_track.grantRole(cancel_role, CANCELLER_ADDRESS, tx_params)

    print("🏁 Renouncing permissions from the deployer...\n")

    # renounce permissions from deployer

    easy_track.renounceRole(pause_role, deployer, tx_params)
    easy_track.renounceRole(cancel_role, deployer, tx_params)
    easy_track.renounceRole(default_admin_role, deployer, tx_params)

    # validate deployment
    print("🔬 Validating the deployment & permissions...\n")

    assert easy_track.motionDuration() == MOTION_DURATION
    assert easy_track.motionsCountLimit() == MOTIONS_COUNT_LIMIT
    assert easy_track.objectionsThreshold() == OBJECTIONS_THRESHOLD

    # validate permissions layout

    assert easy_track.hasRole(default_admin_role, admin)

    if ADDITIONAL_ADMIN_ADDRESS is not None:
        assert easy_track.hasRole(default_admin_role, ADDITIONAL_ADMIN_ADDRESS)

    if PAUSER_ADDRESS is not None:
        easy_track.hasRole(pause_role, PAUSER_ADDRESS)

    if CANCELLER_ADDRESS is not None:
        easy_track.hasRole(cancel_role, CANCELLER_ADDRESS)

    assert not easy_track.hasRole(pause_role, deployer)
    assert not easy_track.hasRole(cancel_role, deployer)
    assert not easy_track.hasRole(default_admin_role, deployer)

    print("✅ Contracts successfully deployed & validated!\n")
