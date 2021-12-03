from brownie import EasyTrack
from utils.config import get_is_live, get_deployer_account, prompt_bool
from utils import test_helpers

EASY_TRACK_ADDRESS = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"


def main():
    deployer = get_deployer_account(get_is_live())
    print("DEPLOYER:", deployer)
    print(
        f"Renounce PAUSE_ROLE, UNPAUSE_ROLE, CANCEL_ROL from {deployer} on EasyTrack ({EASY_TRACK_ADDRESS})"
    )
    print("Proceed? [y/n]: ")
    if not prompt_bool():
        print("Aborting")
        return

    tx_params = {"from": deployer}
    easy_track = EasyTrack.at(EASY_TRACK_ADDRESS)
    renounce_roles(easy_track, tx_params)

    print("Validate that roles was renounced")
    test_helpers.assert_equals(
        f"{deployer} has no PAUSE_ROLE",
        not easy_track.hasRole(easy_track.PAUSE_ROLE(), deployer),
        True,
    )
    test_helpers.assert_equals(
        f"{deployer} has no UNPAUSE_ROLE",
        not easy_track.hasRole(easy_track.UNPAUSE_ROLE(), deployer),
        True,
    )
    test_helpers.assert_equals(
        f"{deployer} has no CANCEL_ROLE",
        not easy_track.hasRole(easy_track.CANCEL_ROLE(), deployer),
        True,
    )


def renounce_roles(easy_track, tx_params):
    account = tx_params["from"]
    easy_track.renounceRole(easy_track.PAUSE_ROLE(), account, tx_params)
    easy_track.renounceRole(easy_track.UNPAUSE_ROLE(), account, tx_params)
    easy_track.renounceRole(easy_track.CANCEL_ROLE(), account, tx_params)
