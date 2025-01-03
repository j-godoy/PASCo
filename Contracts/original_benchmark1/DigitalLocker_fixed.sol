pragma solidity ^0.5.10;

library Verification {
    function Assert  (bool b) public;
    function Assume  (bool b) public;
    function CexPrinti  (uint i) public;
}

contract DigitalLocker
{
    enum StateType { Requested, DocumentReview, AvailableToShare, SharingRequestPending, SharingWithThirdParty, Terminated }
    address Owner;
    address BankAgent;
    uint LockerIdentifier;
    address CurrentAuthorizedUser;
    uint ExpirationTimestamp;
    uint ImageCode;
    address ThirdPartyRequestor;
    bool HasIntendedPurpose;
    enum LockerStatusEnum {Pending, Rejected, Approved, Shared, Available}
    LockerStatusEnum LockerStatus;
    uint RejectionReasonCode;
    StateType State;

    constructor(address bankAgent) public
    {
        Owner = msg.sender;

        State = StateType.Requested;

        BankAgent = bankAgent;

       Verification.Assert(State == StateType.Requested);
    }

    function BeginReviewProcess() public
    {
        /* Need to update, likely with registry to confirm sender is agent
        Also need to add a function to re-assign the agent.
        */
        if (Owner == msg.sender)
        {
            revert();
        }

        //FIX: Add precondition
        require(State == StateType.Requested);

       Verification.Assert(State == StateType.Requested);

        BankAgent = msg.sender;

        LockerStatus = LockerStatusEnum.Pending;
        State = StateType.DocumentReview;

       Verification.Assert(State == StateType.DocumentReview);
    }

    function RejectApplication(uint rejectionReason) public
    {
        if (BankAgent != msg.sender)
        {
            revert();
        }

        RejectionReasonCode = rejectionReason;
        LockerStatus = LockerStatusEnum.Rejected;
        State = StateType.DocumentReview;
    }

    function UploadDocuments(uint lockerIdentifier, uint imageCode) public
    {
        if (BankAgent != msg.sender)
        {
            revert();
        }

        //FIX: Add precondition
        require(State == StateType.DocumentReview);

       Verification.Assert(State == StateType.DocumentReview);

        LockerStatus = LockerStatusEnum.Approved;
        ImageCode = imageCode;
        LockerIdentifier = lockerIdentifier;
        State = StateType.AvailableToShare;

       Verification.Assert(State == StateType.AvailableToShare);
    }

    function ShareWithThirdParty(address thirdPartyRequestor, uint expirationTimestamp) public
    {
        if (Owner != msg.sender)
        {
            revert();
        }

        //FIX: Add precondition
        require(State == StateType.AvailableToShare);

       Verification.Assert(State == StateType.AvailableToShare);

        ThirdPartyRequestor = thirdPartyRequestor;
        CurrentAuthorizedUser = ThirdPartyRequestor;

        LockerStatus = LockerStatusEnum.Shared;
        HasIntendedPurpose = true;
        ExpirationTimestamp = expirationTimestamp;
        State = StateType.SharingWithThirdParty;

       Verification.Assert(State == StateType.SharingWithThirdParty);
    }

    function AcceptSharingRequest() public
    {
        if (Owner != msg.sender)
        {
            revert();
        }

        //FIX: Add precondition
        require(State == StateType.SharingRequestPending);

       Verification.Assert(State == StateType.SharingRequestPending);

        CurrentAuthorizedUser = ThirdPartyRequestor;
        State = StateType.SharingWithThirdParty;

       Verification.Assert(State == StateType.SharingWithThirdParty);
    }

    function RejectSharingRequest() public
    {
        if (Owner != msg.sender)
        {
            revert();
        }

        //FIX: Add precondition
        require(State == StateType.SharingRequestPending);

       Verification.Assert(State == StateType.SharingRequestPending);

        LockerStatus = LockerStatusEnum.Available;
        CurrentAuthorizedUser = address(0);
        State = StateType.AvailableToShare;

       Verification.Assert(State == StateType.AvailableToShare);
    }

    function RequestLockerAccess() public
    {
        if (Owner == msg.sender)
        {
            revert();
        }

        //FIX: Add precondition
        require(State == StateType.AvailableToShare);

       Verification.Assert(State == StateType.AvailableToShare);

        ThirdPartyRequestor = msg.sender;
        HasIntendedPurpose = true;
        State = StateType.SharingRequestPending;

       Verification.Assert(State == StateType.SharingRequestPending);
    }

    function ReleaseLockerAccess() public
    {

        if (CurrentAuthorizedUser != msg.sender)
        {
            revert();
        }

        //FIX: Add precondition
        require(State == StateType.SharingWithThirdParty);

       Verification.Assert(State == StateType.SharingWithThirdParty);

        LockerStatus = LockerStatusEnum.Available;
        ThirdPartyRequestor = address(0);
        CurrentAuthorizedUser = address(0);
        HasIntendedPurpose = false;
        State = StateType.AvailableToShare;

       Verification.Assert(State == StateType.AvailableToShare);
    }
    
    function RevokeAccessFromThirdParty() public
    {
        if (Owner != msg.sender)
        {
            revert();
        }

        //FIX: Add precondition
        require(State == StateType.SharingWithThirdParty);

       Verification.Assert(State == StateType.SharingWithThirdParty);

        LockerStatus = LockerStatusEnum.Available;
        CurrentAuthorizedUser = address(0);
        State = StateType.AvailableToShare;

       Verification.Assert(State == StateType.AvailableToShare);
    }

    function Terminate() public
    {
        if (Owner != msg.sender)
        {
            revert();
        }

        //FIX: Add precondition
        require(State != StateType.Requested &&
                State != StateType.DocumentReview &&
                State != StateType.Terminated);

       Verification.Assert(State == StateType.SharingWithThirdParty ||
                            State == StateType.AvailableToShare ||
                            State == StateType.SharingRequestPending);

        CurrentAuthorizedUser = address(0);
        State = StateType.Terminated;

       Verification.Assert(State == StateType.Terminated);
    }
}