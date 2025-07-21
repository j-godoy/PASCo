/*
 * @source: https://github.com/sigp/solidity-security-blog
 * @author: Suhabe Bugrara
 * @vulnerable_at_lines: 27
 */

//added pragma version
pragma solidity ^0.5.1;

contract EtherStore {

    uint256 public withdrawalLimit = 1 ether;
    mapping(address => uint256) public lastWithdrawTime;
    mapping(address => uint256) public balances;

    uint256 public time;
	uint256 public balance = 0;
    uint256 public senders_in_mapping = 0;
	address public A;

    constructor(uint256 _time, address _A) public {
        time = _time;
        A = _A;
    }

    function depositFunds() public payable {
        // Re-entrancy analysis
        if (msg.value > 0) {
            balance = balance + msg.value;
            if (balances[msg.sender] == 0) {
                senders_in_mapping += 1;
            }
        }
        //// Re-entrancy analysis
        balances[msg.sender] += msg.value;
    }

    function withdrawFunds (uint256 _weiToWithdraw) public {
        require(senders_in_mapping > 0);
        require(balances[msg.sender] >= _weiToWithdraw);
        // limit the withdrawal
        require(_weiToWithdraw <= withdrawalLimit);
        // limit the time allowed to withdraw
        require(time >= lastWithdrawTime[msg.sender] + 1 weeks);
        
        balance -= _weiToWithdraw;
        // <yes> <report> REENTRANCY
        //require(msg.sender.call.value(_weiToWithdraw)());

        balances[msg.sender] -= _weiToWithdraw;        
        lastWithdrawTime[msg.sender] = time;
        if (_weiToWithdraw > 0 && balances[msg.sender] == 0) {
            senders_in_mapping -= 1;
        }
    }

    function t(uint256 _time) public {
        require(_time > 0);
        time = time + _time;
    }


    function dummy_balanceGTZero() public view { require(balance > 0); }
	function dummy_balanceAGTZero() public view { require(balances[A] > 0); }

 }