/*
 * @source: https://github.com/ConsenSys/evm-analyzer-benchmark-suite
 * @author: Suhabe Bugrara
 * @vulnerable_at_lines: 18
 */

pragma solidity ^0.5.1;

contract ReentrancyDAO {
    mapping (address => uint) credit;
    uint balance;

    uint senders_in_mapping = 0;
	address A;

    // Re-entrancy analysis
	address _last;
	address[] senders_reentrant = new address[](0);

    constructor(address _A) public {
        A = _A;
    }

    function withdrawAll_Init() public {
        require(senders_in_mapping > 0);
        uint oCredit = credit[msg.sender];
        if (oCredit > 0) {
            credit[msg.sender] = 0;
            balance -= oCredit;
            if (credit[msg.sender] == 0) {
                senders_in_mapping -= 1;
            }
            senders_reentrant.push(msg.sender);
            // <yes> <report> REENTRANCY
            // bool callResult = msg.sender.call.value(oCredit)();
            // require (callResult);
        }
    }

    function withdrawAll_End() public {
        require (senders_reentrant.length > 0);
        require (senders_reentrant[senders_reentrant.length-1] == msg.sender);
		senders_reentrant.length -= 1;
    }

    function deposit() public payable {
        if (msg.value > 0) {
            if (credit[msg.sender] == 0) {
                senders_in_mapping += 1;
            }
        }
        credit[msg.sender] += msg.value;
        balance += msg.value;
    }

    function dummy_balanceGTZero() public view { require(balance > 0); }
    function dummy_balanceAGTZero() public view { require(credit[A] > 0); }
}
