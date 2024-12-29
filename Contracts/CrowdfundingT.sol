pragma solidity ^0.5.0;

contract Crowdfunding {
    address payable owner;
    uint max_block;
    uint goal;
    uint blockNumber;

    mapping(address => uint) backers;
    address[] backersArray = new address[](0);
    address[] auxArray;
    uint countBackers = 0;
    bool funded = false;
    uint balance = 0;


    constructor(address payable _owner, uint _max_block, uint _goal, uint _blockNumber) public {
        owner = _owner;
        max_block = _max_block;
        goal = _goal;
        balance = 0;
        blockNumber = _blockNumber;
    }

    function Donate() public payable {
        if(max_block <= blockNumber) {
            revert();
        }
        else {
            if(backers[msg.sender] == 0) {
                backers[msg.sender] = msg.value;
                backersArray.push(msg.sender);
                balance = balance + msg.value;
                //t();
            }
            else {
                revert();
            }
        }
    }

    function GetFunds() public {
        if(max_block < blockNumber && msg.sender == owner) {
            if(goal <= balance) {
                funded = true;
                //owner.transfer(balance);
                balance = 0;
                //t();
            }
            else {
                revert();
            }
        }
        else {
            revert();
        }
    }

    function Claim() public {
        if(blockNumber <= max_block) {
            revert();
        }
        else {
            if(backers[msg.sender] == 0 || backersArray.length == 0 || funded || goal <= balance) {
                revert();
            }
            else {
                uint val = backers[msg.sender];
                backers[msg.sender] = 0;
                backersArray = remove(msg.sender, backersArray);
                //msg.sender.transfer(val);
                balance = balance - val;
                //t();
            }
        }
    }
    
    function remove(address _valueToFindAndRemove, address[] memory _array) public  returns(address[] memory) {

        auxArray = new address[](0); 

        for (uint i = 0; i < _array.length; i++){
            if(_array[i] != _valueToFindAndRemove)
                auxArray.push(_array[i]);
        }

        return auxArray;
    }

    function t() public {
        blockNumber = blockNumber + 1;
    }
}