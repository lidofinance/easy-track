# @version 0.2.8
# @author Lido <info@lido.fi>
# @licence MIT
from vyper.interfaces import ERC20

struct Ballot:
  name: string[255]
  ballotMaker: address
  ballotMakerStake: wei_value
  deadline: timestamp
  objections: HashMap(address, wei_value)
  objections_total: wei_value

owner: public(address)
ballotMakers: public(HashMap[address, bool])
ballotTime: public(timedelta)
minBallotStake: public(decimal)
ballots: public(HashMap[string[255], Ballot])
objections_threshold: public(wei_value)

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

@public
@payable
def make_ballot(_name: string[255]):
    assert ballotMakers[msg.sender] = True
    assert msg.value >= self.minBallotStake
    assert self.ballots[_name] = False
    self.ballots[_name] = Ballot({
        name = _name,
        active = True,
        ballotMaker = msg.sender
        deadline = block.timestamp + self.ballotTime,
        result = True
    })
    self.ballots[_name].ballotMakerStake = msg.value

@external
def withdrawBallotStake(_name: string[255]):
    assert self.ballots[_name].active = False
    assert self.ballots[_name].ballotMakerStake > 0
    _ballotMaker = self.ballots[_name].ballotMaker
    _amount: wei_value = self.ballots[_name].ballotMakerStake
    self.ballots[_name].ballotMakerStake = 0
    send(_ballotMaker, _amount)

@public
@payable
def sendObjection(_name: string[266]):
    <<only_active>>
    <<objections_not_enough>>
    self.ballots[_name].objections[msg.sender] = msg.value
    _total = self.ballots[_name].objections_total
    self.ballots[_name].objections_total = total + msg.value

@external
def ballotResult()
    assert block.timestamp > self.ballots[_name].deadline
    assert self.ballots[_name].objections_total < self.objections_threshold
    some_action_stub()
