def date_time_contract(network: str = "mainnet") -> str:
    if network == "mainnet":
        return "0x23d23d8F243e57d0b924bff3A3191078Af325101"
    if network == "goerli":
        return "0x99A1372F31A455106C975beEA524350a9d1Cd3ED"
    raise NameError(
        f"""Unknown network "{network}". Supported networks: mainnet, goerli."""
    )
