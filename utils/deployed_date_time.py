def date_time_contract(network: str = "mainnet") -> str:
    if network == "mainnet":
        return "0x23d23d8F243e57d0b924bff3A3191078Af325101"
    if network == "goerli":
        return "0xb1e4de1092D0D32613e4BbFBf4D68650862f43A6"
    raise NameError(
        f"""Unknown network "{network}". Supported networks: mainnet, goerli."""
    )
