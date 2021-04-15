# @version 0.2.8
# @author Lido <info@lido.fi>
# @licence MIT

validators: public(HashMap[address, bool])
admins: public(HashMap[address, bool])

@external
def __init__(_admin: address):
    self.admins[_admin] = True

@external
def add_validator(_param: address):
    assert self.admins[msg.sender], "not an admin"
    self.validators[_param] = True

@external
def del_validator(_param: address):
    assert self.admins[msg.sender], "not an admin"
    self.validators[_param] = False

@internal
def _check_creds(sender: address):
    assert self.validators[sender], "not a validator"

# Starting vote process
@external
def start_vote():
    # Check
    self._check_creds(msg.sender)
