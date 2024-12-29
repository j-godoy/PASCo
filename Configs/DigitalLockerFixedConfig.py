fileName = "DigitalLocker_fixed.sol"
contractName = "DigitalLocker"
functions = [
"BeginReviewProcess();", 
"RejectApplication(rejectionReason);",
"UploadDocuments( lockerIdentifier, image);", 
"ShareWithThirdParty(thirdPartyRequestor, expirationDate);",
"AcceptSharingRequest();",
"RejectSharingRequest();",
"RequestLockerAccess();",
"ReleaseLockerAccess();",
"RevokeAccessFromThirdParty();",
"Terminate();"
]

statePreconditions = [
"State == StateType.Requested", 
"true",
"State == StateType.DocumentReview",
"State == StateType.AvailableToShare",
"State == StateType.SharingRequestPending",
"State == StateType.SharingRequestPending",
"State == StateType.AvailableToShare",
"State == StateType.SharingWithThirdParty",
"State == StateType.SharingWithThirdParty",
"State != StateType.Requested && State != StateType.DocumentReview &&State != StateType.Terminated"
]

functionPreconditions = [
"Owner != msg.sender",
"BankAgent == msg.sender",
"BankAgent == msg.sender",
"Owner == msg.sender",
"Owner == msg.sender",
"Owner == msg.sender",
"Owner != msg.sender",
"CurrentAuthorizedUser == msg.sender",
"Owner == msg.sender",
"Owner == msg.sender"]

functionVariables = "uint rejectionReason, uint lockerIdentifier, uint image, address thirdPartyRequestor, uint expirationDate"
tool_output = "Found a counterexample"

statesModeState = [[1,0,0,0,0,0], [0,2,0,0,0,0], [0,0,3,0,0,0], [0,0,0,4,0,0], [0,0,0,0,5,0], [0,0,0,0,0,6]]
statesNamesModeState = ["Requested", "DocumentReview", "AvailableToShare", "SharingRequestPending", "SharingWithThirdParty", "Terminated"]
statePreconditionsModeState = ["State == StateType.Requested", 
"State == StateType.DocumentReview", 
"State == StateType.AvailableToShare", 
"State == StateType.SharingRequestPending",
"State == StateType.SharingWithThirdParty",
"State == StateType.Terminated"]
txBound = 8