fileName = "DigitalLocker.sol"
contractName = "DigitalLocker"
functions = [
"BeginReviewProcess();", 
"RejectApplication(rejectionReason);",
"UploadDocuments( lockerIdentifier, image);", 
"ShareWithThirdParty(thirdPartyRequestor, expirationDate, intendedPurpose);",
"AcceptSharingRequest();",
"RejectSharingRequest();",
"RequestLockerAccess(intendedPurpose);",
"ReleaseLockerAccess();",
"RevokeAccessFromThirdParty();",
"Terminate();"]

statePreconditions = ["true", 
"true",
"true",
"true",
"true",
"true",
"true",
"true",
"true",
"true"]

functionPreconditions = ["Owner != msg.sender",
"BankAgent == msg.sender",
"BankAgent == msg.sender",
"Owner == msg.sender",
"Owner == msg.sender",
"Owner == msg.sender",
"Owner != msg.sender",
"CurrentAuthorizedUser == msg.sender",
"Owner == msg.sender",
"Owner == msg.sender"]

functionVariables = "string memory rejectionReason, string memory lockerIdentifier, string memory image, address thirdPartyRequestor, string memory expirationDate, string memory intendedPurpose"
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