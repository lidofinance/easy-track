from brownie import (
    EasyTrack,
    EVMScriptExecutor
)

def addresses(network="mainnet"):
    if network == "mainnet":
        return EasyTrackSetup(
            easy_track="0xF0211b7660680B49De1A7E9f25C65660F0a13Fea",
            evm_script_executor="0xFE5986E06210aC1eCC1aDCafc0cc7f8D63B3F977"
        )
    if network == "goerli":
        return EasyTrackSetup(
            easy_track="0xAf072C8D368E4DD4A9d4fF6A76693887d6ae92Af",
            evm_script_executor="0x3c9aca237b838c59612d79198685e7f20c7fe783"
        )
    raise NameError(
        f"""Unknown network "{network}". Supported networks: mainnet, goerli."""
    )

def contracts(network="mainnet"):
    network_addresses = addresses(network)
    return EasyTrackSetup(
        easy_track=EasyTrack.at(network_addresses.easy_track),
        evm_script_executor=EVMScriptExecutor.at(network_addresses.evm_script_executor)
    )

class EasyTrackSetup:
    def __init__(self, easy_track, evm_script_executor):
        self.easy_track = easy_track
        self.evm_script_executor = evm_script_executor
