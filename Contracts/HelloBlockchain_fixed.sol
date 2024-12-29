pragma solidity ^0.5.10;

contract HelloBlockchain {
     //Set of States
    enum StateType { Request, Respond}

    //List of properties
    StateType State;
    address Requestor;
    address Responder;

    uint RequestMessageCode;
    uint ResponseMessageCode;

    // constructor function
    constructor(uint messageCode) public
    {
        Requestor = msg.sender;
        RequestMessageCode = messageCode;
        State = StateType.Respond;
    }

    // call this function to send a request
    function SendRequest(uint requestMessageCode) public
    {
        if (Requestor != msg.sender)
        {
            revert();
        }

        // FIX: Add precondition
        if (State != StateType.Respond)
        {
            revert();
        }

        RequestMessageCode = requestMessageCode;
        State = StateType.Request;
    }

    // call this function to send a response
    function SendResponse(uint responseMessageCode) public
    {
        // FIX: Add precondition
        if (State != StateType.Request)
        {
            revert();
        }

       //Verification.Assert(State == StateType.Request);

        Responder = msg.sender;

        // call ContractUpdated() to record this action
        ResponseMessageCode = responseMessageCode;
        State = StateType.Respond;
    }
}