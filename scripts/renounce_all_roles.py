from brownie import EasyTrack
from utils.config import get_is_live, get_deployer_account, prompt_bool
from utils import test_helpers

EASY_TRACK_ADDRESS = "0xF0211b7660680B49De1A7E9f25C65660F0a13Fea"


def main():
    deployer = get_deployer_account(get_is_live())
    print("DEPLOYER:", deployer)
    print(
        f"Renounce DEFAULT_ADMIN_ROLE, PAUSE_ROLE, UNPAUSE_ROLE, CANCEL_ROLE from {deployer} on EasyTrack ({EASY_TRACK_ADDRESS})"
    )
    print("Proceed? [y/n]: ")
    if not prompt_bool():
        print("Aborting")
        return

    tx_params = {"from": deployer}
    easy_track = EasyTrack.at(EASY_TRACK_ADDRESS)

    # default admin role
    if easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer):
        print(f"{deployer} has DEFAULT_ADMIN_ROLE, sending transaction to renounce it")
        easy_track.renounceRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer, tx_params)
    else:
        print(f"{deployer} has no DEFAULT_ADMIN_ROLE")

    # pause role
    if easy_track.hasRole(easy_track.PAUSE_ROLE(), deployer):
        print(f"{deployer} has PAUSE_ROLE, sending transaction to renounce it")
        easy_track.renounceRole(easy_track.PAUSE_ROLE(), deployer, tx_params)
    else:
        print(f"{deployer} has no PAUSE_ROLE")

    # unpause role
    if easy_track.hasRole(easy_track.UNPAUSE_ROLE(), deployer):
        print(f"{deployer} has UNPAUSE_ROLE, sending transaction to renounce it")
        easy_track.renounceRole(easy_track.UNPAUSE_ROLE(), deployer, tx_params)
    else:
        print(f"{deployer} has no UNPAUSE_ROLE")

    # cancel role
    if easy_track.hasRole(easy_track.CANCEL_ROLE(), deployer):
        print(f"{deployer} has CANCEL_ROLE, sending transaction to renounce it")
        easy_track.renounceRole(easy_track.CANCEL_ROLE(), deployer, tx_params)
    else:
        print(f"{deployer} has no CANCEL_ROLE")

    print("Validate that roles was renounced")
    test_helpers.assert_equals(
        f"{deployer} has no DEFAULT_ADMIN_ROLE",
        not easy_track.hasRole(easy_track.DEFAULT_ADMIN_ROLE(), deployer),
        True,
    )
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
