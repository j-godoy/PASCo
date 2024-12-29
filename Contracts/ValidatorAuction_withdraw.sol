/**
 *Submitted for verification at Etherscan.io on 2019-10-02
*/


pragma solidity ^0.5.0;


contract Ownable {
    address public owner;

    constructor() public {
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(
            msg.sender == owner,
            "The function can only be called by the owner"
        );
        _;
    }

    function transferOwnership(address newOwner) public onlyOwner {
        if (newOwner != address(0x0)) {
            owner = newOwner;
        }
    }
}

contract DepositLockerInterface {
    function slash(address _depositorToBeSlashed) public;

}

contract DepositLocker is DepositLockerInterface, Ownable {
    bool public initialized = false;
    bool public deposited = false;

    /* We maintain two special addresses:
       - the slasher, that is allowed to call the slash function
       - the depositorsProxy that registers depositors and deposits a value for
         all of the registered depositors with the deposit function. In our case
         this will be the auction contract.
    */

    address public slasher;
    address public depositorsProxy;
    uint public releaseTimestamp;

    mapping(address => uint) public canWithdraw;
    uint numberOfDepositors = 0;
    uint valuePerDepositor;
    uint time;

    event DepositorRegistered(
        address depositorAddress,
        uint numberOfDepositors
    );
    event Deposit(
        uint totalValue,
        uint valuePerDepositor,
        uint numberOfDepositors
    );
    event Withdraw(address withdrawer, uint value);
    event Slash(address slashedDepositor, uint slashedValue);

    modifier isInitialised() {
        require(initialized, "The contract was not initialized.");
        _;
    }

    modifier isDeposited() {
        require(deposited, "no deposits yet");
        _;
    }

    modifier isNotDeposited() {
        require(!deposited, "already deposited");
        _;
    }

    modifier onlyDepositorsProxy() {
        require(
            msg.sender == depositorsProxy,
            "Only the depositorsProxy can call this function."
        );
        _;
    }

    function() external {}

    function init(
        uint _releaseTimestamp,
        address _slasher,
        address _depositorsProxy,
        uint _time
    ) external onlyOwner {
        time = _time;
        require(!initialized, "The contract is already initialised.");
        require(
            _releaseTimestamp > time,
            "The release timestamp must be in the future"
        );

        releaseTimestamp = _releaseTimestamp;
        slasher = _slasher;
        depositorsProxy = _depositorsProxy;
        initialized = true;
        owner = address(0x0);
    }

    function registerDepositor(address _depositor)
        public
        isInitialised
        isNotDeposited
        onlyDepositorsProxy
    {
        require(
            canWithdraw[_depositor] == 0,
            "can only register Depositor once"
        );
        canWithdraw[_depositor] = 1;
        numberOfDepositors += 1;
        time = time + 1;
        // emit DepositorRegistered(_depositor, numberOfDepositors);
    }

    function deposit(uint _valuePerDepositor)
        public
        payable
        isInitialised
        isNotDeposited
        onlyDepositorsProxy
    {
        require(numberOfDepositors > 0, "no depositors");
        require(_valuePerDepositor > 0, "_valuePerDepositor must be positive");

        uint depositAmount = numberOfDepositors * _valuePerDepositor;
        require(
            _valuePerDepositor == depositAmount / 1,
            "Overflow in depositAmount calculation"
        );
        require(
            msg.value == depositAmount,
            "the deposit does not match the required value"
        );

        valuePerDepositor = _valuePerDepositor;
        deposited = true;
        //emit Deposit(msg.value, valuePerDepositor, numberOfDepositors);
    }

    function withdraw() public isInitialised isDeposited {
        require(
            time >= releaseTimestamp,
            "The deposit cannot be withdrawn yet."
        );
        require(canWithdraw[msg.sender] == 1, "cannot withdraw from sender");

        canWithdraw[msg.sender] = 0;
        time = time + 1;
        //msg.sender.transfer(valuePerDepositor);
        //emit Withdraw(msg.sender, valuePerDepositor);
    }

    function slash(address _depositorToBeSlashed)
        public
        isInitialised
        isDeposited
    {
        require(
            msg.sender == slasher,
            "Only the slasher can call this function."
        );
        require(canWithdraw[_depositorToBeSlashed] == 1, "cannot slash address");
        canWithdraw[_depositorToBeSlashed] = 0;
        time = time + 1;
        //address(0x0).transfer(valuePerDepositor);
        //emit Slash(_depositorToBeSlashed, valuePerDepositor);
    }
}

contract ValidatorAuction_withdraw is Ownable {
    // auction constants set on deployment
    uint public auctionDurationInDays;
    uint public startPrice;
    uint public minimalNumberOfParticipants;
    uint public maximalNumberOfParticipants;
    uint time;

    AuctionState public auctionState;
    DepositLocker public depositLocker;
    mapping(address => uint) public whitelist;
    uint countWhitelist = 0;
    mapping(address => uint) public bids;
    uint countBidders = 0;
    uint biddersTotal = 0;
    uint count = 0;
    address A;
    bool hasA = false;
    uint public startTime;
    uint public closeTime;
    uint public lowestSlotPrice;

    event BidSubmitted(
        address bidder,
        uint bidValue,
        uint slotPrice,
        uint timestamp
    );
    event AddressWhitelisted(address whitelistedAddress);
    event AuctionDeployed(
        uint startPrice,
        uint auctionDurationInDays,
        uint minimalNumberOfParticipants,
        uint maximalNumberOfParticipants
    );
    event AuctionStarted(uint startTime);
    event AuctionDepositPending(
        uint closeTime,
        uint lowestSlotPrice,
        uint totalParticipants
    );
    event AuctionEnded(
        uint closeTime,
        uint lowestSlotPrice,
        uint totalParticipants
    );
    event AuctionFailed(uint closeTime, uint numberOfBidders);

    enum AuctionState {
        Deployed,
        Started,
        DepositPending, /* all slots sold, someone needs to call depositBids */
        Ended,
        Failed
    }

    modifier stateIs(AuctionState state) {
        require(
            auctionState == state,
            "Auction is not in the proper state for desired action."
        );
        _;
    }

    constructor(
        uint _startPriceInWei,
        uint _auctionDurationInDays,
        uint _minimalNumberOfParticipants,
        uint _maximalNumberOfParticipants,
        DepositLocker _depositLocker,
        uint _time,
        address _A,
        uint _lowestPrice,
        uint dloker_releaseTimestamp,
        address dloker_slasher,
        address dloker_depositorsProxy,
        uint dloker_time
    ) public {
        require(
            _auctionDurationInDays >= 0,
            "Duration of auction must be greater than 0"
        );
        require(
            _auctionDurationInDays < 100 * 365,
            "Duration of auction must be less than 100 years"
        );
        require(
            _minimalNumberOfParticipants > 0,
            "Minimal number of participants must be greater than 0"
        );
        require(
            _maximalNumberOfParticipants > 0,
            "Number of participants must be greater than 0"
        );
        require(
            _minimalNumberOfParticipants <= _maximalNumberOfParticipants,
            "The minimal number of participants must be smaller than the maximal number of participants."
        );
        require(
            // To prevent overflows
            _startPriceInWei < 10000000000000000000000000000000,
            "The start price is too big."
        );

        startPrice = _startPriceInWei;
        auctionDurationInDays = _auctionDurationInDays;
        maximalNumberOfParticipants = _maximalNumberOfParticipants;
        minimalNumberOfParticipants = _minimalNumberOfParticipants;
        depositLocker = _depositLocker;

        lowestSlotPrice = _lowestPrice;

        /*emit AuctionDeployed(
            startPrice,
            auctionDurationInDays,
            _minimalNumberOfParticipants,
            _maximalNumberOfParticipants
        );*/
        auctionState = AuctionState.Deployed;
        time = _time;
        A = _A;

        //Deposit Locker init
        depositLocker.init(dloker_releaseTimestamp, dloker_slasher, dloker_depositorsProxy, dloker_time);
        t();
    }

    // function() external payable stateIs(AuctionState.Started) {
    //     bid();
    // }

    function bid() public payable stateIs(AuctionState.Started) {
        require(time > startTime, "It is too early to bid.");
        require(
            time <= startTime + auctionDurationInDays,
            "Auction has already ended."
        );
        // uint slotPrice = 1;
        uint slotPrice = currentPrice();//pasa de 400seg aprox a 800seg aprox
        require(
            msg.value >= slotPrice,
            "Not enough ether was provided for bidding."
        );
        require(whitelist[msg.sender] == 1, "The sender is not whitelisted.");
        // require(!isSenderContract(), "The sender cannot be a contract.");
        require(
            biddersTotal < maximalNumberOfParticipants,
            "The limit of participants has already been reached."
        );
        require(bids[msg.sender] == 0, "The sender has already bid.");

        bids[msg.sender] = msg.value;
        // bidders.push(msg.sender);
        biddersTotal += 1;
        // biddersArray.push(msg.sender);
        countBidders += 1;

        if (slotPrice < lowestSlotPrice) {
            lowestSlotPrice = slotPrice;
        }

        depositLocker.registerDepositor(msg.sender);
        //emit BidSubmitted(msg.sender, msg.value, slotPrice, now);

        if (biddersTotal == maximalNumberOfParticipants) {
            transitionToDepositPending();
        }
        
        if (msg.sender == A) {
            hasA = true;
        }

        t();
    }

    function startAuction() public onlyOwner stateIs(AuctionState.Deployed) {
        require(
            depositLocker.initialized(),
            "The deposit locker contract is not initialized"
        );

        auctionState = AuctionState.Started;
        startTime = time;
        t();
        //emit AuctionStarted(now);
    }

    function depositBids() public stateIs(AuctionState.DepositPending) {
        auctionState = AuctionState.Ended;
        depositLocker.deposit.value(lowestSlotPrice * biddersTotal)(
            lowestSlotPrice
        );
        t();
        //emit AuctionEnded(closeTime, lowestSlotPrice, biddersTotal);
    }

    function closeAuction() public stateIs(AuctionState.Started) {
        require(
            time > startTime + auctionDurationInDays,
            "The auction cannot be closed this early."
        );
        require(biddersTotal < maximalNumberOfParticipants);

        if (biddersTotal >= minimalNumberOfParticipants) {
            transitionToDepositPending();
        } else {
            transitionToAuctionFailed();
        }
        t();
    }

    function addToWhitelist(address[] memory addressesToWhitelist)
        public
        onlyOwner
        stateIs(AuctionState.Deployed)
    {
        for (uint32 i = 0; i < addressesToWhitelist.length; i++) {
            if (whitelist[addressesToWhitelist[i]] == 0) {
                countWhitelist += 1;
            }
            whitelist[addressesToWhitelist[i]] = 1;
            //emit AddressWhitelisted(addressesToWhitelist[i]);
        }
        //whitelist[A] = true;
        t();
    }

    function withdrawA() public {
        require(
            ((auctionState == AuctionState.Ended ||
                auctionState == AuctionState.Failed)),
            "You cannot withdraw before the auction is ended or it failed."
        );

        require(countBidders > 0 && hasA && msg.sender == A);

        if (auctionState == AuctionState.Ended) {
            withdrawAfterAuctionEnded();
        } else if (auctionState == AuctionState.Failed) {
            withdrawAfterAuctionFailed();
        } else {
            //require(false); // Should be unreachable
        }
        hasA = false;
        t();
    }

    function withdrawOther() public {
        require(
        ((auctionState == AuctionState.Ended ||
                auctionState == AuctionState.Failed) && bids[msg.sender] > 0),
            "You cannot withdraw before the auction is ended or it failed."
        );
        require(countBidders > 0 && (!hasA || countBidders > 1)  && msg.sender != A);

        if (auctionState == AuctionState.Ended) {
            withdrawAfterAuctionEnded();
        } else if (auctionState == AuctionState.Failed) {
            withdrawAfterAuctionFailed();
        } else {
            //require(false); // Should be unreachable
        }
        t();
    }

    function currentPrice()
        internal
        view
        stateIs(AuctionState.Started)
        returns (uint)
    {
        require(time >= startTime);
        uint secondsSinceStart = (time - startTime);
        return priceAtElapsedTime(secondsSinceStart);
    }

    function priceAtElapsedTime(uint secondsSinceStart)
        internal
        view
        returns (uint)
    {
        // To prevent overflows
        require(
            secondsSinceStart < 100 * 365,
            "Times longer than 100 years are not supported."
        );
        uint msSinceStart = 1000 * secondsSinceStart;
        uint relativeAuctionTime = msSinceStart / 1;
        uint256 decayDivisor = 1;
        uint decay = relativeAuctionTime * relativeAuctionTime * relativeAuctionTime / decayDivisor;
        uint256 price = startPrice *
            (1 + relativeAuctionTime) / 1;
        return price;
    }

    function withdrawAfterAuctionEnded() internal stateIs(AuctionState.Ended) {
        require(
            bids[msg.sender] > lowestSlotPrice,
            "The sender has nothing to withdraw."
        );

        uint valueToWithdraw = bids[msg.sender] - lowestSlotPrice;
        require(valueToWithdraw <= bids[msg.sender]);

        bids[msg.sender] = lowestSlotPrice;
        if (lowestSlotPrice == 0) {
           countBidders -= 1;
        }

        //msg.sender.transfer(valueToWithdraw);
    }

    function withdrawAfterAuctionFailed()
        internal
        stateIs(AuctionState.Failed)
    {
        require(bids[msg.sender] > 0, "The sender has nothing to withdraw.");

        uint valueToWithdraw = bids[msg.sender];
        bids[msg.sender] = 0;
        countBidders -= 1;
        //msg.sender.transfer(valueToWithdraw);
    }

    function transitionToDepositPending()
        internal
        stateIs(AuctionState.Started)
    {
        auctionState = AuctionState.DepositPending;
        closeTime = time;
        //emit AuctionDepositPending(closeTime, lowestSlotPrice, bidders.length);
    }

    function transitionToAuctionFailed()
        internal
        stateIs(AuctionState.Started)
    {
        auctionState = AuctionState.Failed;
        closeTime = time;
        //emit AuctionFailed(closeTime, bidders.length);
    }

    function isSenderContract() internal view returns (bool isContract) {
        uint32 size = 0;
        address sender = msg.sender;
        // solium-disable-next-line security/no-inline-assembly
        /* assembly { */
        /*     size := extcodesize(sender) */
        /* } */
        return (size > 0);
    }

    function t() public {
        time = time + 1;
    }

}