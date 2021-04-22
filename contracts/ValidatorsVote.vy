# @version 0.2.8
# @author Lido <info@lido.fi>
# @licence MIT
from vyper.interfaces import ERC20

interface MiniMe:
  def balanceOfAt(_owner: address, _blockNumber: uint256) -> uint256: constant

Objection: event({sender: indexed(address), power: uint256})

struct Ballot:
  deadline: uint256
  objections_total_weight: uint256
  ballot_maker: address
  snapshot_block: uint256
  objections: HashMap(address, uint256)

owner: public(address)
ballot_makers: public(HashMap[address, bool])
ballot_time: public(uint256)
next_ballot_index: public(uint256)
TOKEN: constant(address) = 0xDEADBEEF
objections_threshold: public(uint256)
ballots: public(HashMap[uint256, Ballot])

@external
def __init__(
    _ballot_time: uint256,
    _objections_threshold: uint256,
    _stub: bool
    ):
    self.owner = msg.sender
    self.ballot_time = _ballot_time
    self.next_ballot_index = 1
    self.snapshot_block = block.number - 1
    self.objections_threshold = _objections_threshold

@external
def transferOwnership(_new_owner: address):
    assert msg.sender = self.owner
    self.owner = _new_owner

@external
def add_ballot_maker(_param: address):
    assert msg.sender = self.owner
    ballot_makers[_param] = True

@external
def del_ballot_maker(_param: address):
    assert msg.sender = self.owner
    ballot_makers[_param] = False

@public
def make_ballot(_ballotHash: bytes32):
    assert ballot_makers[msg.sender] = True
    self.ballots[self.next_ballot_index] = Ballot({
        ballot_maker = msg.sender
        deadline = block.timestamp + self.ballot_time,
    })
    self.next_ballot_index = self.next_ballot_index + 1

@external
def is_ballot_finished(_ballot_id: uint256):
    if ( block.timestamp > ballots[_ballot_id].deadline ):
       return True
    if ( objections_threshold > ballots[_ballot_id].objections_total_weight ):
       return True
    return False



@public
def sendObjection(_ballot_idx: uint256):
    assert block.timestamp < self.ballots[_ballot_idx].deadline
    assert self.ballots[_ballot_idx].objections_total < self.objections_threshold
    _voting_power: uint256
    _voting_power = MiniMe(token).balanceOfAt(msg.sender, self.snapshot_block)
    self.ballots[_ballot_idx].objections[msg.sender] = _voting_power
    _total = self.ballots[_ballot_idx].objections_total_weight
    self.ballots[_ballot_idx].objections_total_weight = total + _voting_power
    log.Objection(msg.sender, power)

@external
def ballotResult():
    assert block.timestamp > self.ballots[_name].deadline
    assert self.ballots[_ballot_idx].objections_total < self.objections_threshold
    some_action_stub()
