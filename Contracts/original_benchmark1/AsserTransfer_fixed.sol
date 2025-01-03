pragma solidity ^0.5.10;

library Verification {
    function Assert  (bool b) public;
    function Assume  (bool b) public;
    function CexPrinti  (uint i) public;
}

contract AssetTransfer
{
    enum StateType { Active, OfferPlaced, PendingInspection, Inspected, Appraised, NotionalAcceptance, BuyerAccepted, SellerAccepted, Accepted, Terminated }
    address InstanceOwner;
    uint AskingPrice;
    StateType State;

    address InstanceBuyer;
    uint OfferPrice;
    address InstanceInspector;
    address InstanceAppraiser;

    constructor(uint256 price) public
    {
        InstanceOwner = msg.sender;
        AskingPrice = price;
        State = StateType.Active;

       Verification.Assert(State == StateType.Active);
    }

    function Terminate() public
    {
        if (InstanceOwner != msg.sender)
        {
            revert();
        }

        // FIX: Add this precondition
        if (State == StateType.Terminated || State == StateType.Accepted || State == StateType.SellerAccepted)
        {
                    revert();
        }

       Verification.Assert(State != StateType.Terminated &&
                            State != StateType.Accepted &&
                            State != StateType.SellerAccepted);

        State = StateType.Terminated;

       Verification.Assert(State == StateType.Terminated);
    }

    function Modify(uint256 price) public
    {

        if (State != StateType.Active)
        {
            revert();
        }
        if (InstanceOwner != msg.sender)
        {
            revert();
        }

       Verification.Assert(State == StateType.Active);

        AskingPrice = price;

       Verification.Assert(State == StateType.Active);
    }

    function MakeOffer(address inspector, address appraiser, uint256 offerPrice) public
    {

        if (inspector == address(0) || appraiser == address(0) || offerPrice == 0)
        {
            revert();
        }
        if (State != StateType.Active)
        {
            revert();
        }
        // Cannot enforce "AllowedRoles":["Buyer"] because Role information is unavailable
        if (InstanceOwner == msg.sender) // not expressible in the current specification language
        {
            revert();
        }

       Verification.Assert(State == StateType.Active);

        InstanceBuyer = msg.sender;
        InstanceInspector = inspector;
        InstanceAppraiser = appraiser;
        OfferPrice = offerPrice;
        State = StateType.OfferPlaced;

       Verification.Assert(State == StateType.OfferPlaced);
    }

    function AcceptOffer() public
    {
        if (State != StateType.OfferPlaced)
        {
            revert();
        }
        if (InstanceOwner != msg.sender)
        {
            revert();
        }

       Verification.Assert(State == StateType.OfferPlaced);

        State = StateType.PendingInspection;

       Verification.Assert(State == StateType.PendingInspection);
    }

    function Reject() public
    {

        if (State != StateType.OfferPlaced && State != StateType.PendingInspection && State != StateType.Inspected && State != StateType.Appraised && State != StateType.NotionalAcceptance && State != StateType.BuyerAccepted)
        {
            revert();
        }
        if (InstanceOwner != msg.sender)
        {
            revert();
        }

       Verification.Assert(State != StateType.Active &&
                            State != StateType.SellerAccepted &&
                            State != StateType.Accepted &&
                            State != StateType.Terminated);

        InstanceBuyer = address(0);
        State = StateType.Active;

       Verification.Assert(State == StateType.Active);
    }

    function Accept() public
    {

        if (msg.sender != InstanceBuyer && msg.sender != InstanceOwner)
        {
            revert();
        }

        if (msg.sender == InstanceOwner &&
            State != StateType.NotionalAcceptance &&
            State != StateType.BuyerAccepted)
        {
            revert();
        }

        if (msg.sender == InstanceBuyer &&
            State != StateType.NotionalAcceptance &&
            State != StateType.SellerAccepted)
        {
            revert();
        }

       Verification.Assert(State == StateType.NotionalAcceptance ||
                            State == StateType.SellerAccepted ||
                            State == StateType.BuyerAccepted);

        if (msg.sender == InstanceBuyer)
        {
            if (State == StateType.NotionalAcceptance)
            {
                State = StateType.BuyerAccepted;
            }
            else if (State == StateType.SellerAccepted)
            {
                State = StateType.Accepted;
            }
        }
        else
        {
            if (State == StateType.NotionalAcceptance)
            {
                State = StateType.SellerAccepted;
            }
            else if (State == StateType.BuyerAccepted)
            {
                State = StateType.Accepted;
            }
        }

       Verification.Assert(State == StateType.Accepted ||
                            State == StateType.SellerAccepted ||
                            State == StateType.BuyerAccepted);
    }

    function ModifyOffer(uint256 offerPrice) public
    {
        if (State != StateType.OfferPlaced)
        {
            revert();
        }
        if (InstanceBuyer != msg.sender || offerPrice == 0)
        {
            revert();
        }

       Verification.Assert(State == StateType.OfferPlaced);

        OfferPrice = offerPrice;

       Verification.Assert(State == StateType.OfferPlaced);
    }

    function RescindOffer() public
    {

        if (State != StateType.OfferPlaced && State != StateType.PendingInspection && State != StateType.Inspected && State != StateType.Appraised && State != StateType.NotionalAcceptance && State != StateType.SellerAccepted)
        {
            revert();
        }
        if (InstanceBuyer != msg.sender)
        {
            revert();
        }

       Verification.Assert(State != StateType.Accepted &&
                            State != StateType.Terminated &&
                            State != StateType.BuyerAccepted &&
                            State != StateType.Active);

        InstanceBuyer = address(0);
        OfferPrice = 0;
        State = StateType.Active;

       Verification.Assert(State == StateType.Active);
    }

    function MarkAppraised() public
    {

        if (InstanceAppraiser != msg.sender)
        {
            revert();
        }

        if (State != StateType.PendingInspection && State != StateType.Inspected)
        {
            revert();
        }

       Verification.Assert(State == StateType.Inspected ||
                            State == StateType.PendingInspection);

        if (State == StateType.PendingInspection)
        {
            State = StateType.Appraised;
        }
        else if (State == StateType.Inspected)
        {
            State = StateType.NotionalAcceptance;
        }

       Verification.Assert(State == StateType.Appraised ||
                            State == StateType.NotionalAcceptance);
    }

    function MarkInspected() public
    {

        if (InstanceInspector != msg.sender)
        {
            revert();
        }

        if (State != StateType.PendingInspection && State != StateType.Appraised)
        {
            revert();
        }

       Verification.Assert(State == StateType.PendingInspection ||
                            State == StateType.Appraised);

        if (State == StateType.PendingInspection)
        {
            State = StateType.Inspected;
        }
        else if (State == StateType.Appraised)
        {
            State = StateType.NotionalAcceptance;
        }

       Verification.Assert(State == StateType.Inspected ||
                            State == StateType.NotionalAcceptance);
    }
}