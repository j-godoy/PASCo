pragma solidity ^0.5.10;

library Verification {
    function Assert  (bool b) public;
    function Assume  (bool b) public;
    function CexPrinti  (uint i) public;
}


contract BasicProvenance
{

    //Set of States
    enum StateType { Created, InTransit, Completed}
    
    //List of properties
    StateType State;
    address InitiatingCounterparty;
    address Counterparty;
    address PreviousCounterparty;
    address SupplyChainOwner;
    address SupplyChainObserver;
    
    constructor(address supplyChainOwner, address supplyChainObserver) public
    {
        InitiatingCounterparty = msg.sender;
        Counterparty = InitiatingCounterparty;
        SupplyChainOwner = supplyChainOwner;
        SupplyChainObserver = supplyChainObserver;
        State = StateType.Created;

       Verification.Assert(State == StateType.Created);
    }

    function TransferResponsibility(address newCounterparty) public
    {

        if (Counterparty != msg.sender || State == StateType.Completed)
        {
            revert();
        }

       Verification.Assert(State == StateType.Created ||
                            State == StateType.InTransit);

        if (State == StateType.Created)
        {
            State = StateType.InTransit;
        }

        PreviousCounterparty = Counterparty;
        Counterparty = newCounterparty;

       Verification.Assert(State == StateType.InTransit);
    }

    function Complete() public
    {
        if (SupplyChainOwner != msg.sender || State == StateType.Completed)
        {
            revert();
        }

        //FIX: Add precondition
        if (State == StateType.Created)
        {
            revert();
        }

       Verification.Assert(State == StateType.InTransit);

        State = StateType.Completed;
        PreviousCounterparty = Counterparty;
        Counterparty = address(0);

       Verification.Assert(State == StateType.Completed);
    }
}