pragma solidity ^0.5.0;

contract CrowdfundingBase {
    address payable owner;
    uint max_block;
    uint goal;
    uint blockNumber;
    
    mapping ( address => uint ) backers;
    uint countBackers = 0;
    bool funded = false;
    uint balance = 0;

    constructor ( address payable _owner , uint _max_block , uint _goal, uint _blockNumber) public {
        owner = _owner;
        max_block = _max_block;
        goal = _goal;
        balance = 0;
        blockNumber = _blockNumber;
    }

    function Donate () public payable {
        require ( max_block > blockNumber);
        require ( backers [msg.sender] == 0);
        backers [msg.sender] = msg.value;
        if (msg.value > 0) {
            countBackers += 1;
            balance = balance + msg.value;
        }
    }

    function GetFunds () public {
        require (max_block < blockNumber);
        require (msg.sender == owner);
        require (goal <= balance);
        // owner.call.value(balance)("");
        funded = true;
        balance = 0;
    }

    function Claim () public {
        require (max_block < blockNumber);
        require (backers[msg.sender] > 0 && !funded);
        require (goal > balance);
        require (countBackers > 0);
        uint val = backers[msg.sender];
        // msg.sender.call.value(val)("");
        backers[msg.sender] = 0;
        countBackers -= 1;
        balance = balance - val;
    }
    
 }