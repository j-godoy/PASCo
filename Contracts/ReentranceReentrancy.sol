/*
 * @source: https://ethernaut.zeppelin.solutions/level/0xf70706db003e94cfe4b5e27ffd891d5c81b39488
 * @author: Alejandro Santander
 * @vulnerable_at_lines: 24
 */

pragma solidity ^0.5.1;

contract Reentrance {

  mapping(address => uint) public balances;

  uint balance = 0;
  uint senders_in_mapping = 0;
	address A;

  // Re-entrancy analysis
	address _last;
  struct ReentrantSender {
      address sender;
      uint value;
  }
  ReentrantSender[] senders_reentrant;

  constructor(address _A) public {
        A = _A;
    }

  function donate(address _to) public payable {
    if (msg.value > 0) {
      balance = balance + msg.value;
      if (balances[_to] == 0) {
        senders_in_mapping += 1;
      }
    }
    balances[_to] += msg.value;
  }

  // function balanceOf(address _who) public view returns (uint balance) {
  //   return balances[_who];
  // }

  function withdraw_Init(uint _amount) public {
    require(senders_in_mapping > 0);
    if(balances[msg.sender] >= _amount) {
      // <yes> <report> REENTRANCY
      // if(msg.sender.call.value(_amount)()) {
      //   _amount;
      // }
      balance -= _amount;
      senders_reentrant.push(ReentrantSender(msg.sender, _amount));
    }
  }

  function withdraw_End() public {
    require (senders_reentrant.length > 0);
    address last_sender = senders_reentrant[senders_reentrant.length-1].sender;
    require(last_sender == msg.sender);
		uint256 value = senders_reentrant[senders_reentrant.length-1].value;
    senders_reentrant.length--;

    if (balances[msg.sender] > 0) {
      balances[msg.sender] -= value;
      if (value>0 && balances[msg.sender] == 0) {
        senders_in_mapping -= 1;
      }
    }
  }

  function dummy_balanceGTZero() public view { require(balance > 0); }
  function dummy_balanceAGTZero() public view { require(balances[A] > 0); }
  
}
