from utils import log

CANCEL_ROLE = "0x9f959e00d95122f5cbd677010436cf273ef535b86b056afc172852144b9491d7"
PAUSE_ROLE = "0x139c2898040ef16910dc9f44dc697df79363da767d8bc92f2e310312b816e46d"
UNPAUSE_ROLE = "0x265b220c5a8891efdd9e1b1b7fa72f257bd5169f8d87e319cf3dad6ff52b94ae"
DEFAULT_ADMIN_ROLE = "0x0000000000000000000000000000000000000000000000000000000000000000"
SET_LIMIT_PARAMETERS_ROLE = "0x389c107d46e44659ea9e3d38a2e43f5414bdd0fd8244fa558561536ea90c2ece"
UPDATE_LIMIT_SPENDINGS_ROLE = "0x378a50d7f36729e294e6069934e2d4d58624b5cfc976a0413c001826aeb104d8"
PERMISSION_ERROR_TEMPLATE = "AccessControl: account %s is missing role %s"


def access_control_revert_message(sender, role=DEFAULT_ADMIN_ROLE):
    PERMISSION_ERROR_TEMPLATE = "AccessControl: account %s is missing role %s"
    return PERMISSION_ERROR_TEMPLATE % (sender.address.lower(), role)


def assert_equals(desc, actual, expected):
    assert actual == expected
    log.ok(desc, actual)


def assert_single_event(receipt, event_name, args: dict):
    assert len(receipt.events) == 1, f"event '{event_name}' must exist and be single"
    assert dict(receipt.events[event_name]) == args, f"incorrect event '{event_name}' arguments"


def assert_event_exists(receipt, event_name, args: dict):
    assert dict(receipt.events[event_name]) == args, f"incorrect event '{event_name}' arguments"
