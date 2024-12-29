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

  function withdraw(uint _amount) public {
    require(senders_in_mapping > 0);
    if(balances[msg.sender] >= _amount) {
      // <yes> <report> REENTRANCY
      // if(msg.sender.call.value(_amount)()) {
      //   _amount;
      // }
      balance -= _amount;
      balances[msg.sender] -= _amount;
      if (_amount>0 && balances[msg.sender] == 0) {
        senders_in_mapping -= 1;
      }
    }
  }

  function() external payable {}

  function dummy_balanceGTZero() public view { require(balance > 0); }
  function dummy_balanceAGTZero() public view { require(balances[A] > 0); }
}
