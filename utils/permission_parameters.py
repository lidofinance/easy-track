""" Aragon ACL permission parameters

This module contains classes and functions to create permission parameters for Aragon ACL.
It tries to recreate the original API for the sake of simplicity.
See https://hack.aragon.org/docs/aragonos-ref#parameter-interpretation for details

NB! Constants MUST be equal to ones in deployed Lido ACL contract
https://etherscan.io/address/0x9f3b9198911054b122fdb865f8a5ac516201c339#code
"""

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Union, List
from brownie import convert


# enum Op { NONE, EQ, NEQ, GT, LT, GTE, LTE, RET, NOT, AND, OR, XOR, IF_ELSE }
class Op(Enum):
    """Enum values depends on enum in ACL contract itself
    See https://etherscan.io/address/0x9f3b9198911054b122fdb865f8a5ac516201c339#code#L802 to check
    NB! It changes in future versions of the contract
    """

    NONE = 0
    EQ = 1
    NEQ = 2
    GT = 3
    LT = 4
    GTE = 5
    LTE = 6
    RET = 7
    NOT = 8
    AND = 9
    OR = 10
    XOR = 11
    IF_ELSE = 12


class SpecialArgumentID(IntEnum):
    """Special argument ids that enables different comparison modes"""

    BLOCK_NUMBER_PARAM_ID = 200
    TIMESTAMP_PARAM_ID = 201  #
    ORACLE_PARAM_ID = 203  # auth call to IACLOracle
    LOGIC_OP_PARAM_ID = 204  # logic operations
    PARAM_VALUE_PARAM_ID = 205  # just a value to use with Op.RET


ArgumentID = Union[int, SpecialArgumentID]
"""Determines how the comparison value is fetched. From 0 to 200 it refers to the argument index number passed to the
role. After 200, there are some special Argument IDs: """


class ArgumentValue(int):
    """
    Argument Value (uint240): the value to compare against, depending on the argument. It is a regular Ethereum memory
    word that loses its two most significant bytes of precision. The reason for this was to allow parameters to be saved
    in just one storage slot, saving significant gas. Even though uint240s are used, it can be used to store any integer
    up to 2^30 - 1, addresses, and bytes32. In the case of comparing hashes, losing 2 bytes of precision shouldn't be a
    dealbreaker if the hash algorithm is secure.
    """

    def __new__(cls, value: Union[int, str]):
        return super().__new__(cls, _to_uint240(value))


@dataclass
class Param:
    id: ArgumentID
    op: Op
    value: ArgumentValue

    def to_uint256(self) -> int:
        id8 = convert.to_uint(self.id, "uint8")
        op8 = convert.to_uint(self.op.value, "uint8")
        value240 = convert.to_uint(self.value, "uint240")
        return convert.to_uint((id8 << 248) + (op8 << 240) + value240, "uint256")

    def __str__(self):
        value = hex(self.value) if self.op == Op.EQ else self.value
        special_id = SpecialArgumentID(self.id).name if self.id > 200 else self.id

        value_clause = f"value={value})"
        if self.op == Op.IF_ELSE:
            if_param = value & 0xFFFFFFFF
            then_param = (value & (0xFFFFFFFF << 32)) >> 32
            else_param = (value & (0xFFFFFFFF << 64)) >> 64
            value_clause = f"if={if_param} then={then_param} else={else_param}"
        elif self.op == Op.AND or self.op == Op.OR or self.op == Op.NOT or self.op == Op.XOR:
            left = value & 0xFFFFFFFF
            right = (value & (0xFFFFFFFF << 32)) >> 32
            value_clause = f"left={left} right={right}"
        return f"Param(ArgumentID={special_id}, op={self.op}, {value_clause})"


def encode_permission_params(params: List[Param]) -> List[int]:
    return list(map(lambda p: p.to_uint256(), params))


def encode_argument_value_op(left: int, right: int) -> ArgumentValue:
    return encode_argument_value_if(left, right, 0)


def encode_argument_value_if(condition: int, success: int, failure: int) -> ArgumentValue:
    condition32 = convert.to_uint(condition, "uint32")
    success32 = convert.to_uint(success, "uint32")
    failure32 = convert.to_uint(failure, "uint32")

    value = condition32 + (success32 << 32) + (failure32 << 64)

    return ArgumentValue(convert.to_uint(value, "uint240"))


def _to_uint240(val: Union[int, str]) -> int:
    #  Possibly, not explicit enough way to handle addresses
    if isinstance(val, str) and (val[:2] == "0x"):
        val = int(val, 16)
    return ~(0xFFFF << 240) & val


def parse(val: int) -> Param:
    arg_id = (val & (0xFF << 248)) >> 248
    op = (val & (0xFF << 240)) >> 240
    val = _to_uint240(val)
    return Param(arg_id, Op(op), ArgumentValue(val))
