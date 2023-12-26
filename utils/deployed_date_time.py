def date_time_contract(network: str = "mainnet") -> str:
    if network == "mainnet" or network == "mainnet-fork":
        return "0x75100bd564415731b5936a4a94d0dc29dde5db3c"
    if network == "goerli" or network == "goerli-fork":
        return "0xb1e4de1092D0D32613e4BbFBf4D68650862f43A6"
    if network == "holesky" or network == "holesky-fork":
        return "0x8809f6174182D22983DCCA1c48e2da3b9593736c"
    raise NameError(f"""Unknown network "{network}". Supported networks: mainnet, goerli, holesky.""")
