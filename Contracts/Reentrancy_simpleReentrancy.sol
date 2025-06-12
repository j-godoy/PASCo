/*
 * @source: https://github.com/trailofbits/not-so-smart-contracts/blob/master/reentrancy/Reentrancy.sol
 * @author: -
 * @vulnerable_at_lines: 24
 */

 pragma solidity ^0.5.1;

 contract Reentrance {
     mapping (address => uint) userBalance;

    uint balance;
    uint senders_in_mapping = 0;
	address A;

    // Re-entrancy analysis
	address _last;
	address[] senders_reentrant = new address[](0);

    constructor(address _A) public {
        A = _A;
    }

    function getBalance(address u) public view returns(uint){
        return userBalance[u];
    }

    function addToBalance() public payable{
        if (msg.value > 0) {
            balance = balance + msg.value;
            if (userBalance[msg.sender] == 0) {
                senders_in_mapping += 1;
            }
        }
        userBalance[msg.sender] += msg.value;
    }

    function withdrawBalance_Init() public {
        require(senders_in_mapping > 0);
        // send userBalance[msg.sender] ethers to msg.sender
        // if mgs.sender is a contract, it will call its fallback function
        // <yes> <report> REENTRANCY
        // if( ! (msg.sender.call.value(userBalance[msg.sender])() ) ){
        //     throw;
        // }
        if (userBalance[msg.sender] > 0) {
            balance -= userBalance[msg.sender];
            senders_reentrant.push(msg.sender);
        }
    }

    function withdrawBalance_End() public {
        require(senders_in_mapping > 0);
        require (senders_reentrant.length > 0);
        require (senders_reentrant[senders_reentrant.length-1] == msg.sender);
        senders_reentrant.length -= 1;

        if (userBalance[msg.sender] > 0) {            
            userBalance[msg.sender] = 0;
            senders_in_mapping -= 1;
        }
    }

    function dummy_balanceGTZero() public view { require(balance > 0); }
    function dummy_balanceAGTZero() public view { require(userBalance[A] > 0); }
 }
