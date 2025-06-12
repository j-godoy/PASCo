/*
 * @source: http://blockchain.unica.it/projects/ethereum-survey/attacks.html#simpledao
 * @author: -
 * @vulnerable_at_lines: 19
 */

pragma solidity ^0.4.2;

contract SimpleDAO {
  mapping (address => uint) public credit;
  bool lock = false;

  function donate(address to) payable {
    credit[to] += msg.value;
  }

  function withdraw(uint amount) {
    require (!lock);
    lock = true;
    if (credit[msg.sender]>= amount) {
      bool res = msg.sender.call.value(amount)();
      credit[msg.sender]-=amount;
    }
    lock = false;
  }

  function queryCredit(address to) returns (uint){
    return credit[to];
  }
}
