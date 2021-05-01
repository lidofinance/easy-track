# @version 0.2.8
# @author Lido <info@lido.fi>
# @licence MIT
from vyper.interfaces import ERC20

interface MiniMe:
  def balanceOfAt(_owner: address, _blockNumber: uint256) -> uint256: view

event EasyTrackVoteStart:
  ballotHash: indexed(bytes32)
  ballotId: indexed(uint256)
event Objection:
  sender: indexed(address)
  power: uint256
event EnactBallot:
  idx: indexed(uint256)

struct Ballot:
  deadline: uint256
  objections_total_weight: uint256
  ballot_maker: address
  snapshot_block: uint256

owner: public(address)
ballot_makers: public(HashMap[address, bool])
ballot_time: public(uint256)
next_ballot_index: public(uint256)
TOKEN: constant(address) = 0x5A98FcBEA516Cf06857215779Fd812CA3beF1B32
objections_threshold: public(uint256)
objections: HashMap[uint256, HashMap[address, uint256]]
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
    self.objections_threshold = _objections_threshold

@external
def transferOwnership(_new_owner: address):
    assert msg.sender == self.owner
    self.owner = _new_owner

@external
def add_ballot_maker(_param: address):
    assert msg.sender == self.owner
    self.ballot_makers[_param] = True

@external
def del_ballot_maker(_param: address):
    assert msg.sender == self.owner
    self.ballot_makers[_param] = False

@external
def make_ballot(_ballotHash: bytes32):
    assert self.ballot_makers[msg.sender] == True
    self.ballots[self.next_ballot_index] = Ballot({
        deadline: block.timestamp + self.ballot_time,
        objections_total_weight: 0,
        ballot_maker: msg.sender,
        snapshot_block: block.number - 1
    })
    self.ballots[self.next_ballot_index].snapshot_block = block.number - 1
    log EasyTrackVoteStart(_ballotHash, self.next_ballot_index)
    self.next_ballot_index = self.next_ballot_index + 1
    # vote_id = tx.events['StartVote']['voteId']
    # return vote_id

# @external
# def is_ballot_finished(_ballot_id: uint256) -> bool:
#     if ( block.timestamp > self.ballots[_ballot_id].deadline ):
#        return True
#     if ( objections_threshold > ballots[_ballot_id].objections_total_weight ):
#        return True
#     return False



@external
def sendObjection(_ballot_idx: uint256):
    assert block.timestamp < self.ballots[_ballot_idx].deadline
    assert self.ballots[_ballot_idx].objections_total_weight < self.objections_threshold
    _voting_power: uint256 = MiniMe(TOKEN).balanceOfAt(msg.sender, self.ballots[_ballot_idx].snapshot_block)
    self.objections[_ballot_idx][msg.sender] = _voting_power
    self.ballots[_ballot_idx].objections_total_weight = _voting_power + self.ballots[_ballot_idx].objections_total_weight
    log Objection(msg.sender, _voting_power)

@external
def ballotResult(_ballot_idx: uint256):
    assert block.timestamp > self.ballots[_ballot_idx].deadline
    assert self.ballots[_ballot_idx].objections_total_weight < self.objections_threshold
    log EnactBallot(_ballot_idx)
