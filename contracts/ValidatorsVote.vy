# @version 0.2.8
# @author Lido <info@lido.fi>
# @licence MIT
from vyper.interfaces import ERC20

struct Ballot:
  name: string[255]
  active: bool
  created: uint256
  deadline: timestamp
  result: bool
  ballots: HashMap(uint256, decimal)
  enact_addr: address, # TODO
  enact_fun: address   # TODO

owner: public(address)
ballotMakers: public(HashMap[address, bool])
ballot_time: public(timedelta)
minBallotStake: public(decimal)
ballots: public(HashMap[string[255], Ballot])

@external
def __init__():
    self.owner = msg.sender

@external
def transferOwnership(_newOwner: address):
    assert msg.sender = self.owner
    self.owner = _newOwner

@external
def addBallotMaker(_param: address):
    assert msg.sender = self.owner
    ballotMakers[_param] = True

@external
def delBallotMaker(_param: address):
    assert msg.sender = self.owner
    ballotMakers[_param] = False

@external
def make_ballot(_name: string[255]):
    assert ballotMakers[msg.sender] = True
    assert msg.value >= self.minBallotStake
    self.ballots[_name] = Ballot({
        name = _name,
        active = True,
        created = block.timestamp,
        deadline = block.timestamp + ballot_time,
        result = True
    })
