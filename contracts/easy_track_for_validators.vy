validators: public(HashMap[address, bool])
admin: public(HashMap[address, bool])

@public
def __init__(_admin: address):
    self.admins[_admin] = True

@public
def add_validator(param):
    assert admins[msg.sender], "not an admin"
    self.validators[param] = True

@public
def del_validator
    assert admins[msg.sender], "not an admin"
    self.validators[param] = False

@internal
def _check_creds():
    assert validators[msg.sender], "not a validator"

# Starting vote process
@public
def start_vote():
    # Check
    _check_creds()
