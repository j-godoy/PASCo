/*
 * @source: https://github.com/seresistvanandras/EthBench/blob/master/Benchmark/Simple/reentrant.sol
 * @author: -
 * @vulnerable_at_lines: 21
 */

pragma solidity ^0.5.1;
contract EtherBank{
    mapping (address => uint) userBalances;
	// Re-entrancy analysis
	address _last;
	address[] senders_reentrant = new address[](0);

    uint senders_in_mapping = 0;
	uint balance = 0;
	address A;
	
	constructor(address _A) public {
        A = _A;
    }


	function getBalance(address user) public view returns(uint) {  
		return userBalances[user];
	}

	function addToBalance() public payable {  
		userBalances[msg.sender] += msg.value;
		// Re-entrancy analysis
		if (msg.value > 0) {			
			balance = balance + msg.value;
			senders_in_mapping += 1;
		}
	}

	function withdrawBalance_Init() public {
		uint amountToWithdraw = userBalances[msg.sender];
        // <yes> <report> REENTRANCY
		//bool ret = msg.sender.call.value(amountToWithdraw)();
		// if (!ret) { throw; }
		// userBalances[msg.sender] = 0;
		balance -= amountToWithdraw;
		senders_reentrant.push(msg.sender);
	}

	function withdrawBalance_End() public {
		require (senders_reentrant.length > 0);
        require (senders_reentrant[senders_reentrant.length-1] == msg.sender);
		senders_reentrant.length -= 1;

		if (userBalances[msg.sender] > 0) {
			senders_in_mapping -= 1;
			userBalances[msg.sender] = 0;
		}
	}

    function dummy_balanceGTZero() public view { require(balance > 0); }
	function dummy_balanceAGTZero() public view { require(userBalances[A] > 0); }
}