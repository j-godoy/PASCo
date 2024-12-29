pragma solidity ^0.5.10;


contract BasicProvenance {

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
    }

    function TransferResponsibility(address newCounterparty) public
    {

        if (Counterparty != msg.sender || State == StateType.Completed)
        {
            revert();
        }

        if (State == StateType.Created)
        {
            State = StateType.InTransit;
        }

        PreviousCounterparty = Counterparty;
        Counterparty = newCounterparty;
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

        State = StateType.Completed;
        PreviousCounterparty = Counterparty;
        Counterparty = address(0);
    }
}