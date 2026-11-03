"""Compatibility between Anvil trace memory and Brownie 1.20's Geth-style decoder."""


def normalize_trace_memory(response):
    result = response.get("result")
    if isinstance(result, dict):
        for step in result.get("structLogs", ()):
            memory = step.get("memory")
            if isinstance(memory, list):
                step["memory"] = [word.removeprefix("0x") for word in memory]
    return response
