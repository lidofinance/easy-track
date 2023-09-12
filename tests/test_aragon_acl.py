from brownie import web3, convert, reverts

TEST_ROLE = web3.keccak(text="STAKING_MODULE_MANAGE_ROLE").hex()


def test_aragon_acl_grant_role(acl, voting, stranger):
    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False

    acl.createPermission(stranger, voting, TEST_ROLE, voting, {"from": voting})

    assert acl.hasPermission(stranger, voting, TEST_ROLE) == True
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 0


def test_aragon_acl_role_with_permission(acl, voting, stranger):
    permission = (0, 1, 3)
    permission_param = convert.to_uint(
        (permission[0] << 248) + (permission[1] << 240) + permission[2], "uint256"
    )

    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False

    acl.createPermission(voting, voting, TEST_ROLE, voting, {"from": voting})
    acl.grantPermissionP(
        stranger, voting, TEST_ROLE, [permission_param], {"from": voting}
    )

    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False
    assert (
        acl.hasPermission["address,address,bytes32,uint[]"](
            stranger, voting, TEST_ROLE, [permission_param]
        )
        == True
    )
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 1
    assert acl.getPermissionParam(stranger, voting, TEST_ROLE, 0) == permission

    acl.revokePermission(stranger, voting, TEST_ROLE, {"from": voting})

    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False
    assert (
        acl.hasPermission["address,address,bytes32,uint[]"](
            stranger, voting, TEST_ROLE, [permission_param]
        )
        == False
    )
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 0
    with reverts():
        acl.getPermissionParam(stranger, voting, TEST_ROLE, 0)

    new_permission = (1, 2, 4)
    new_permission_param = convert.to_uint(
        (new_permission[0] << 248) + (new_permission[1] << 240) + new_permission[2],
        "uint256",
    )

    acl.grantPermissionP(
        stranger, voting, TEST_ROLE, [new_permission_param], {"from": voting}
    )

    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False
    # assert False == True
    # assert (
    #     acl.hasPermission["address,address,bytes32,uint[]"](
    #         stranger, voting, TEST_ROLE, [new_permission_param]
    #     )
    #     == True
    # )
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 1
    assert acl.getPermissionParam(stranger, voting, TEST_ROLE, 0) == new_permission

def test_aragon_acl_two_roles_with_different_params(acl, voting, stranger):

    # Grant role with params (0, 1, 3)
    permission = (0, 1, 3)
    permission_param = convert.to_uint(
        (permission[0] << 248) + (permission[1] << 240) + permission[2], "uint256"
    )

    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False

    acl.createPermission(voting, voting, TEST_ROLE, voting, {"from": voting})
    acl.grantPermissionP(
        stranger, voting, TEST_ROLE, [permission_param], {"from": voting}
    )


    # Test role (0, 1, 3)
    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False
    assert (
        acl.hasPermission["address,address,bytes32,uint[]"](
            stranger, voting, TEST_ROLE, [permission_param]
        )
        == True
    )
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 1
    assert acl.getPermissionParam(stranger, voting, TEST_ROLE, 0) == permission


    # Grant role with params (1, 2, 4)
    new_permission = (1, 2, 4)
    new_permission_param = convert.to_uint(
        (new_permission[0] << 248) + (new_permission[1] << 240) + new_permission[2],
        "uint256",
    )

    acl.grantPermissionP(
        stranger, voting, TEST_ROLE, [new_permission_param], {"from": voting}
    )

    # Test role (1,2,4)
    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False
    # assert False == True
    # assert (
    #     acl.hasPermission["address,address,bytes32,uint[]"](
    #         stranger, voting, TEST_ROLE, [new_permission_param]
    #     )
    #     == True
    # )
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 1
    assert acl.getPermissionParam(stranger, voting, TEST_ROLE, 0) == new_permission


    # Test role (0, 1, 3)
    assert acl.hasPermission(stranger, voting, TEST_ROLE) == False
    # assert False == True
    # assert (
    #     acl.hasPermission["address,address,bytes32,uint[]"](
    #         stranger, voting, TEST_ROLE, [permission_param]
    #     )
    #     == True
    # )
    assert acl.getPermissionParamsLength(stranger, voting, TEST_ROLE) == 1
    # assert (1, 2, 4) == (0, 1, 3)
    # assert acl.getPermissionParam(stranger, voting, TEST_ROLE, 0) == permission