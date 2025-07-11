def date_time_contract(network: str = "mainnet") -> str:
    if network == "mainnet" or network == "mainnet-fork":
        return "0x75100bd564415731b5936a4a94d0dc29dde5db3c"
    if network == "holesky" or network == "holesky-fork":
        return "0xd6237FecDF9C1D9b023A5205C17549E3037EeEec"
    raise NameError(f"""Unknown network "{network}". Supported networks: mainnet, holesky.""")
