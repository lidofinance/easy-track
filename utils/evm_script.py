import eth_abi
from brownie.convert import to_bytes

EMPTY_CALLSCRIPT = "0x00000001"


def create_executor_id(id):
    return "0x" + str(id).zfill(8)


def strip_byte_prefix(hexstr):
    return hexstr[2:] if hexstr[0:2] == "0x" else hexstr


def encode_call_script(actions, spec_id=1):
    result = create_executor_id(spec_id)
    for to, calldata in actions:
        addr_bytes = to_bytes(to, "bytes").hex()
        calldata_bytes = strip_byte_prefix(calldata)
        length = eth_abi.encode(["uint32"], [len(calldata_bytes) // 2]).hex()
        result += addr_bytes + length[56:] + calldata_bytes
    return result


def encode_calldata(signature, values):
    return "0x" + eth_abi.encode(signature, values).hex()
