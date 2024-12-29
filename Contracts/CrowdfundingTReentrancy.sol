pragma solidity ^0.5.0;
// import "./Libraries/VeriSolContracts.sol"; 

contract CrowdfundingR {
    address payable owner;
    uint max_block;
    uint goal;
    uint blockNumber;
    
    mapping ( address => uint ) backers;
    bool funded = false;
    uint balance = 0;
    // uint _cont = 0;
    address _last;
    uint countBackers = 0;
    address[] donadores_reentrada = new address[](0);


    constructor ( address payable _owner , uint _max_block , uint _goal, uint _blockNumber ) public {
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
            balance = balance + msg.value;
            countBackers += 1;
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

    function Claim_Init () public {
        require (max_block < blockNumber);
        require (backers[msg.sender] > 0 && !funded);
        require (goal > balance);
        require (countBackers > 0);
        uint val = backers[msg.sender];
        // msg.sender.call.value(val)("");
        balance = balance - val;
        donadores_reentrada.push(msg.sender);
    }

    function Claim_End () public {
        require (donadores_reentrada.length > 0);
        require (donadores_reentrada[donadores_reentrada.length-1] == msg.sender);
        donadores_reentrada.length--;
        
        if (backers[msg.sender] > 0) {
            countBackers -= 1;
            backers[msg.sender] = 0;
        }
    }

    function t() public {
        require(donadores_reentrada.length == 0);
        blockNumber = blockNumber + 1;
    }

    function dummy_balanceGTZero() public { balance > 0; }

 }