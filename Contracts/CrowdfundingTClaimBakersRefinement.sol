pragma solidity ^0.5.0;

contract CrowdfundingR {
    address payable owner;
    uint max_block;
    uint goal;
    uint blockNumber;
    
    mapping ( address => uint ) backers;
    uint countBackers = 0;
    bool funded = false;
    uint balance = 0;
    address _A;
    address _B;

    constructor ( address payable _owner , uint _max_block , uint _goal, uint _blockNumber, address payable A, address payable B) public {
        owner = _owner;
        max_block = _max_block;
        goal = _goal;
        balance = 0;
        blockNumber = _blockNumber;
        require (A != B);
        _A = A;
        _B = B;
    }

    function Donate () public payable {
        require ( max_block > blockNumber);
        require ( backers [msg.sender] == 0);
        backers [msg.sender] = msg.value;
        if (msg.value > 0) {
            countBackers += 1;
            balance = balance + msg.value;
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

    function Claim_A () public {
        require (max_block < blockNumber);
        require (backers[_A] > 0 && !funded);
        require (goal > balance);
        require (countBackers > 0);
        require ( msg.sender == _A);
        uint val = backers[msg.sender];
        // msg.sender.call.value(val)("");
        backers[msg.sender] = 0;
        countBackers -= 1;
        balance = balance - val;
    }

    function Claim_B () public {
        require (max_block < blockNumber);
        require (backers[_B] > 0 && !funded);
        require (goal > balance);
        require (countBackers > 0);
        require ( msg.sender == _B);
        uint val = backers[msg.sender];
        // msg.sender.call.value(val)("");
        backers[msg.sender] = 0;
        countBackers -= 1;
        balance = balance - val;
    }

    function dummy_balanceAGTZeroAndNotB () public {} // balanceAGTZeroAndNotB

    function dummy_balanceAGTZeroAndBGTZero () public {} // balanceAGTZeroAndBGTZero

    function dummy_balanceBGTZeroAndNotA () public {} // balanceBGTZeroAndNotA

    function dummy_balanceAAndBZero () public {} // balanceAAndBZero

    function t() public {
        blockNumber = blockNumber + 1;
    }

    // function test() public {
    //     bool pre_donate1 = (max_block > blockNumber);
    //     bool pre_getFunds1 = (max_block < blockNumber && goal <= balance);
    //     bool pre_claimA1 = (blockNumber > max_block && !funded && goal > balance && countBackers > 0 && backers[_A] > 0);
    //     bool pre_claimB1 = (blockNumber > max_block && !funded && goal > balance && countBackers > 0 && backers[_B] > 0);
    //     bool pre_dummy_balanceAGTZeroAndNotB = backers[_A] > 0 && backers[_B] == 0;
    //     bool pre_dummy_balanceAGTZeroAndBGTZero = backers[_A] > 0 && backers[_B] > 0;
    //     bool pre_dummy_balanceBGTZeroAndNotA = backers[_B] > 0 && backers[_A] == 0;
    //     bool pre_dummy_balanceAAndBZero = backers[_A] == 0 && backers[_B] == 0;

    //     require((!pre_donate1 && !pre_getFunds1 && pre_claimA1 && pre_claimB1 && !pre_dummy_balanceAGTZeroAndNotB && pre_dummy_balanceAGTZeroAndBGTZero && !pre_dummy_balanceBGTZeroAndNotA && !pre_dummy_balanceAAndBZero) );

    //     Claim_A();

    //     bool pre_donate2 = (max_block > blockNumber);
    //     bool pre_getFunds2 = (max_block < blockNumber && goal <= balance);
    //     bool pre_claimA2 = (blockNumber > max_block && !funded && goal > balance && countBackers > 0 && backers[_A] > 0);
    //     bool pre_claimB2 = (blockNumber > max_block && !funded && goal > balance && countBackers > 0 && backers[_B] > 0);
    //     bool pre_dummy_balanceAGTZeroAndNotB2 = backers[_A] > 0 && backers[_B] == 0;
    //     bool pre_dummy_balanceAGTZeroAndBGTZero2 = backers[_A] > 0 && backers[_B] > 0;
    //     bool pre_dummy_balanceBGTZeroAndNotA2 = backers[_B] > 0 && backers[_A] == 0;
    //     bool pre_dummy_balanceAAndBZero2 = backers[_A] == 0 && backers[_B] == 0;
        
    //     assert(!(!pre_donate2 && !pre_getFunds2 && !pre_claimA2 && !pre_claimB2 && !pre_dummy_balanceAGTZeroAndNotB2 && !pre_dummy_balanceAGTZeroAndBGTZero2 && !pre_dummy_balanceBGTZeroAndNotA2 && pre_dummy_balanceAAndBZero2) );
    // }
 }