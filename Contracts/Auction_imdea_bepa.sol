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
    uint256 lastBidBlock;
    bool initialized = false;

    constructor(uint _auctionStart, uint _biddingTime, address payable _beneficiary, uint256 _blockNumber, uint256 _lastBidBlock) public {
        require(!initialized);
        auctionStart = _auctionStart;
        biddingTime = _biddingTime;
        beneficiary = _beneficiary;
        blockNumber = _blockNumber;
        lastBidBlock = _lastBidBlock;
        initialized = true;
    }

    function Bid() public payable {
        require(initialized);
        uint end = auctionStart + biddingTime;
        require(blockNumber <= lastBidBlock || end >= blockNumber);
        if(ended) {
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
                lastBidBlock = blockNumber+3;
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
        require(blockNumber > lastBidBlock);
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
        blockNumber = blockNumber + 1;
    }

    // function blue_query(uint n) public {
    //     bool pre_Bid = (!ended && ((auctionStart + biddingTime) >= blockNumber || blockNumber <= lastBidBlock));
    //     bool pre_Withdraw = pendingReturnsCount > 0 && (auctionStart + biddingTime < blockNumber) && blockNumber > lastBidBlock;
    //     bool pre_AuctionEnd = (!ended && blockNumber > (auctionStart + biddingTime) && blockNumber > lastBidBlock);
    //     bool pre_t = true;
    //     // uint returnscount = pendingReturnsCount;
    //     // uint hb = highestBid;
    //     // require(n > auctionStart + biddingTime && n>blockNumber && n > lastBidBlock);
    //     require(!pre_Bid && pre_Withdraw && pre_AuctionEnd && pre_t);
    //     bool pre_w = pre_withdraw();
    //     assert(pre_w);
    //     require(pre_params_Withdraw());

    //     Withdraw();

    //     bool pre_Bid2 = (!ended && (auctionStart + biddingTime) >= blockNumber);
    //     bool pre_Withdraw2 = pendingReturnsCount > 0 && (auctionStart + biddingTime < blockNumber);
    //     bool pre_AuctionEnd2 = (!ended && blockNumber > (auctionStart + biddingTime));
    //     bool pre_t2 = true;

    //     bool Q = !pre_Bid2 && pre_Withdraw2 && pre_AuctionEnd2 && pre_t2;
    //     bool R = !pre_Bid2 && !pre_Withdraw2 && pre_AuctionEnd2 && pre_t2;

    //     // require(!R);
    //     // assert(false);
    //     assert(Q || R);
    // }

    // function blue_query_constructor(uint _auctionStart, uint _biddingTime, address payable _beneficiary) public {
    //     require(!initialized);

        
    //     constructor_f(_auctionStart, _biddingTime, _beneficiary);

    //     bool pre_Bid2 = (!ended && (auctionStart + biddingTime) >= blockNumber);
    //     bool pre_Withdraw2 = pendingReturnsCount > 0 && (auctionStart + biddingTime < blockNumber);
    //     bool pre_AuctionEnd2 = (!ended && blockNumber > (auctionStart + biddingTime));
    //     bool pre_t2 = true;
        
    //     assert((pre_Bid2 && !pre_Withdraw2 && !pre_AuctionEnd2 && pre_t2));
    // }
}