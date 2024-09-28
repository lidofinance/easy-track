from brownie import web3, reverts

TEST_ROLE = web3.keccak(text="STAKING_MODULE_MANAGE_ROLE").hex()
from utils.permission_parameters import Op, Param


def test_aragon_acl_grant_role(acl, voting, stranger):
    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False

    acl.createPermission(stranger, voting, TEST_ROLE, voting, {"from": voting})

    assert acl.hasPermission(stranger, voting, TEST_ROLE) == True
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 0


def test_aragon_acl_role_with_permission(acl, voting, stranger):
    "Checks Aragon ACL permissions granting, overriding and show what could be checked to get current permissions state"

    permission_param = Param(0, Op.EQ, 3).to_uint256()

    # Test stranger has no roles
    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False

    # Create and grant role with params (0, 1, 3)
    acl.createPermission(voting, voting, TEST_ROLE, voting, {"from": voting})
    acl.grantPermissionP(stranger, voting, TEST_ROLE, [permission_param], {"from": voting})

    # Test role (0, 1, 3)
    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False
    assert acl.hasPermission["address,address,bytes32,uint[]"](stranger, voting, TEST_ROLE, [permission_param]) == True
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 1
    assert acl.getPermissionParam(stranger, voting, TEST_ROLE, 0) == (0, 1, 3)

    # Revoke role (0, 1, 3)
    acl.revokePermission(stranger, voting, TEST_ROLE, {"from": voting})

    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False
    assert acl.hasPermission["address,address,bytes32,uint[]"](stranger, voting, TEST_ROLE, [permission_param]) == False
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 0
    with reverts():
        acl.getPermissionParam(stranger, voting, TEST_ROLE, 0)

    # Grant role with params (0, 1, 4)
    new_permission_param = Param(0, Op.EQ, 4).to_uint256()

    acl.grantPermissionP(stranger, voting, TEST_ROLE, [new_permission_param], {"from": voting})

    # Test role (0, 1, 4)
    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False
    assert (
        acl.hasPermission["address,address,bytes32,uint[]"](stranger, voting, TEST_ROLE, [new_permission_param]) == True
    )
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 1
    assert acl.getPermissionParam(stranger, voting, TEST_ROLE, 0) == (0, 1, 4)


def test_aragon_acl_two_roles_with_different_params(acl, voting, stranger):
    "Checks how granting different parameterized permissions overrides themselves"
    # Grant role with params (0, 1, 3)
    permission = (0, 1, 3)
    permission_param = Param(0, Op.EQ, 3).to_uint256()

    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False

    acl.createPermission(voting, voting, TEST_ROLE, voting, {"from": voting})
    acl.grantPermissionP(stranger, voting, TEST_ROLE, [permission_param], {"from": voting})

    # Test role (0, 1, 3)
    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False
    assert acl.hasPermission["address,address,bytes32,uint[]"](stranger, voting, TEST_ROLE, [permission_param]) == True
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 1
    assert acl.getPermissionParam(stranger, voting, TEST_ROLE, 0) == permission

    # Grant role with params (0, 1, 4)
    new_permission = (0, 1, 4)
    new_permission_param = Param(0, Op.EQ, 4).to_uint256()

    acl.grantPermissionP(stranger, voting, TEST_ROLE, [new_permission_param], {"from": voting})

    # Test role (0, 1, 4)
    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False
    assert (
        acl.hasPermission["address,address,bytes32,uint[]"](stranger, voting, TEST_ROLE, [new_permission_param]) == True
    )
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 1
    assert acl.getPermissionParam(stranger, voting, TEST_ROLE, 0) == new_permission

    # Test role (0, 1, 3)
    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False
    assert acl.hasPermission["address,address,bytes32,uint[]"](stranger, voting, TEST_ROLE, [permission_param]) == False
