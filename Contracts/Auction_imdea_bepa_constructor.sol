pragma solidity ^0.5.0;

// bugs:
// 1. Auction can never end
// 2. highest bidder can never be refunded their highest bid

contract Auction {
    uint auctionStart;
    uint biddingTime;
    address payable beneficiary;

    bool ended = false;
    address payable highestBidder = address(0x0);
    uint highestBid = 0;
    mapping(address => uint) pendingReturns;
    uint pendingReturnsCount = 0;
    uint256 blockNumber;
    bool initialized = false;
    uint256 lastBidBlock;

    constructor(uint256 _blockNumber) public {
        blockNumber = _blockNumber;
    }

    function constructor_f(uint _auctionStart, uint _biddingTime, address payable _beneficiary) public {
        require(!initialized);
        initialized = true;
        auctionStart = _auctionStart;
        biddingTime = _biddingTime;
        beneficiary = _beneficiary;
    }


    function Bid() public payable {
        require(initialized);
        uint end = auctionStart + biddingTime;
        if(end < blockNumber || ended) {
            revert();
        }
        else {
            if(msg.value <= highestBid) {
                revert();
            }
            else {
                if (highestBidder != address(0x0) && pendingReturns[highestBidder] == 0) {
                    pendingReturnsCount += 1;
                }
                pendingReturns[highestBidder] += highestBid;
                highestBidder = msg.sender;
                highestBid = msg.value;
            }
        }
    }

    function pre_withdraw() internal returns(bool) {
        require(initialized);
        require(auctionStart + biddingTime < blockNumber);
        require(blockNumber > lastBidBlock);
        require(pendingReturnsCount > 0);
        return true;
    }

    function pre_params_Withdraw() internal returns(bool) {
        return pendingReturns[msg.sender] != 0;
    }

    function Withdraw() public {
        require(pre_withdraw());
        require(pre_params_Withdraw());
        uint pr = pendingReturns[msg.sender];
        pendingReturns[msg.sender] = 0;
        pendingReturnsCount -= 1;
        //msg.sender.transfer(pr);        
    }

    function AuctionEnd() public {
        require(initialized);
        uint end = auctionStart + biddingTime;

        //bug fixed
        if(blockNumber <= end || ended) {
            revert();
        }
        else {
            ended = true;
            //beneficiary.transfer(highestBid);
        }
    }

    function t() public {
        require(initialized);
        blockNumber = blockNumber + 1;
    }

    function blue_query_constructor(uint _auctionStart, uint _biddingTime, address payable _beneficiary) public {
        require(!initialized);

        constructor_f(_auctionStart, _biddingTime, _beneficiary);

        bool constructor_f = !initialized;
        bool pre_Bid2 = (initialized && !ended && (auctionStart + biddingTime) >= blockNumber);
        bool pre_Withdraw2 = initialized && pendingReturnsCount > 0 && (auctionStart + biddingTime < blockNumber);
        bool pre_AuctionEnd2 = (initialized && !ended && blockNumber > (auctionStart + biddingTime));
        bool pre_t2 = initialized;

        bool Q = !constructor_f && pre_Bid2 && !pre_Withdraw2 && !pre_AuctionEnd2 && pre_t2;
        bool R = !constructor_f && !pre_Bid2 && !pre_Withdraw2 && pre_AuctionEnd2 && pre_t2;
        // require(!R);
        assert(Q);
    }
}