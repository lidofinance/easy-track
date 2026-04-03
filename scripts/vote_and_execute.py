import os
import time
from brownie import accounts, interface


def main():
    deployer = accounts.add(os.environ["DEPLOYER_PRIVATE_KEY"])
    voting_addr = os.environ.get("VOTING_ADDRESS")
    vote_id = int(os.environ.get("VOTE_ID", "2"))

    voting = interface.Voting(voting_addr)

    print(f"Deployer: {deployer.address}")
    print(f"Voting: {voting_addr}")
    print(f"Vote ID: {vote_id}")

    vote_time = voting.voteTime()
    print(f"Vote time: {vote_time}s")

    if voting.canVote(vote_id, deployer.address):
        print("Voting...")
        voting.vote(vote_id, True, False, {"from": deployer, "priority_fee": "2 gwei"})
        print("Voted!")
    else:
        print("Cannot vote (already voted or not eligible)")

    if voting.canExecute(vote_id):
        print("Executing...")
        voting.executeVote(vote_id, {"from": deployer, "priority_fee": "2 gwei"})
        print(f"Vote {vote_id} executed!")
    else:
        print(f"Waiting {vote_time}s for vote period to end...")
        time.sleep(vote_time + 10)
        if voting.canExecute(vote_id):
            print("Executing...")
            voting.executeVote(vote_id, {"from": deployer, "priority_fee": "2 gwei"})
            print(f"Vote {vote_id} executed!")
        else:
            print(f"Vote {vote_id} still cannot be executed")
