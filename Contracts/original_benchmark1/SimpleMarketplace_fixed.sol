pragma solidity ^0.5.10;

library Verification {
    function Assert  (bool b) public;
    function Assume  (bool b) public;
    function CexPrinti  (uint i) public;
}

contract SimpleMarketplace
{
    enum StateType { 
      ItemAvailable,
      OfferPlaced,
      Accepted
    }

    address InstanceOwner;
    int AskingPrice;
    StateType State;

    address InstanceBuyer;
    int OfferPrice;

    constructor(int price) public
    {
        InstanceOwner = msg.sender;
        AskingPrice = price;
        State = StateType.ItemAvailable;

       Verification.Assert(State == StateType.ItemAvailable);
    }

    function MakeOffer(int offerPrice) public
    {
        if (offerPrice == 0)
        {
            revert();
        }

        if (State != StateType.ItemAvailable)
        {
            revert();
        }
        
        if (InstanceOwner == msg.sender)
        {
            revert();
        }

       Verification.Assert(State == StateType.ItemAvailable);

        InstanceBuyer = msg.sender;
        OfferPrice = offerPrice;
        State = StateType.OfferPlaced;

       Verification.Assert(State == StateType.OfferPlaced);
    }

    function Reject() public
    {
        if ( State != StateType.OfferPlaced )
        {
            revert();
        }

        if (InstanceOwner != msg.sender)
        {
            revert();
        }

       Verification.Assert(State == StateType.OfferPlaced);

        InstanceBuyer = address(0);
        State = StateType.ItemAvailable;

       Verification.Assert(State == StateType.ItemAvailable);
    }

    function AcceptOffer() public
    {
        if ( msg.sender != InstanceOwner )
        {
            revert();
        }

        //FIX: Add precondition
        if (State == StateType.ItemAvailable || State == StateType.Accepted)
        {
            revert();
        }

       Verification.Assert(State == StateType.OfferPlaced);

        State = StateType.Accepted;

       Verification.Assert(State == StateType.Accepted);
    }
}