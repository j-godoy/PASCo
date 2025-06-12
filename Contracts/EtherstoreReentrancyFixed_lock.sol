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

    // Re-entrancy analysis
	address _last;
    struct ReentrantSender {
        address sender;
        uint value;
    }
    ReentrantSender[] senders_reentrant;
    bool lock = false;

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
        
        balances[msg.sender] += msg.value;
    }

    function withdrawFunds_Init (uint256 _weiToWithdraw) public {
        require(senders_in_mapping > 0);
        require(balances[msg.sender] >= _weiToWithdraw);
        // limit the withdrawal
        require(_weiToWithdraw <= withdrawalLimit);
        // limit the time allowed to withdraw
        require(time >= lastWithdrawTime[msg.sender] + 1 weeks);
        require (!lock);
        lock = true;
        // <yes> <report> REENTRANCY
        //require(msg.sender.call.value(_weiToWithdraw)());
        balance -= _weiToWithdraw;
        senders_reentrant.push(ReentrantSender(msg.sender, _weiToWithdraw));
    }

    function withdrawFunds_End () public {
        require (senders_reentrant.length > 0);
        address last_sender = senders_reentrant[senders_reentrant.length-1].sender;
        require(last_sender == msg.sender);
        uint256 value = senders_reentrant[senders_reentrant.length-1].value;
        senders_reentrant.length--;

        lastWithdrawTime[msg.sender] = time;
        if (balances[msg.sender] > 0) {
            balances[msg.sender] -= value;
            if (value > 0 && balances[msg.sender] == 0) {
                senders_in_mapping -= 1;
            }
        }
        lock = false;
    }

    function t(uint256 _time) public {
        require(_time > 0);
        require (senders_reentrant.length == 0);
        time = time + _time;
    }

    function query() public view returns (uint256) {
        bool pre_depositBids = true;
        bool pre_withdraFundsInit = senders_in_mapping > 0;
        bool pre_withdraFundsEnd = senders_reentrant.length > 0;
        bool pre_time = time > 0 && senders_reentrant.length == 0;
        bool pre_dummy_balanceGTZero = balance > 0;
        bool pre_dummy_balanceAGTZero = balances[A] > 0;

        bool S = pre_depositBids && pre_withdraFundsInit && !pre_withdraFundsEnd && pre_time && !pre_dummy_balanceGTZero && pre_dummy_balanceAGTZero;
        assert(!S);
    }


    function dummy_balanceGTZero() public view { require(balance > 0); }
	function dummy_balanceAGTZero() public view { require(balances[A] > 0); }

 }