pragma solidity ^0.5.10;

library Verification {
    function Assert  (bool b) public;
    function Assume  (bool b) public;
    function CexPrinti  (uint i) public;
}

contract RefrigeratedTransportation
{
    //Set of States
    enum StateType { Created, InTransit, Completed, OutOfCompliance}
    enum SensorType { None, Humidity, Temperature }

    //List of properties
    StateType State;
    address Owner;
    address InitiatingCounterparty;
    address Counterparty;
    address PreviousCounterparty;
    address Device;
    address SupplyChainOwner;
    address SupplyChainObserver;
    int MinHumidity;
    int MaxHumidity;
    int MinTemperature;
    int MaxTemperature;
    SensorType ComplianceSensorType;
    int ComplianceSensorReading;
    bool ComplianceStatus;
    enum ComplianceDetailEnum {NA, HumidityOutOfRange, TemperatureOutOfRange}
    ComplianceDetailEnum ComplianceDetail;
    int LastSensorUpdateTimestamp;

    constructor(address device, address supplyChainOwner, address supplyChainObserver, int minHumidity, int maxHumidity, int minTemperature, int maxTemperature) public
    {
        ComplianceStatus = true;
        ComplianceSensorReading = -1;
        InitiatingCounterparty = msg.sender;
        Owner = InitiatingCounterparty;
        Counterparty = InitiatingCounterparty;
        Device = device;
        SupplyChainOwner = supplyChainOwner;
        SupplyChainObserver = supplyChainObserver;
        MinHumidity = minHumidity;
        MaxHumidity = maxHumidity;
        MinTemperature = minTemperature;
        MaxTemperature = maxTemperature;
        State = StateType.Created;
        ComplianceDetail = ComplianceDetailEnum.NA;

       Verification.Assert(State == StateType.Created);
    }

    function IngestTelemetry(int humidity, int temperature, int timestamp) public
    {
        // Separately check for states and sender 
        // to avoid not checking for state when the sender is the device
        // because of the logical OR
        if ( State == StateType.Completed )
        {
            revert();
        }

        if ( State == StateType.OutOfCompliance )
        {
            revert();
        }

        if (Device != msg.sender)
        {
            revert();
        }

       Verification.Assert(State == StateType.Created ||
                            State == StateType.InTransit);

        LastSensorUpdateTimestamp = timestamp;

        if (humidity > MaxHumidity || humidity < MinHumidity)
        {
            ComplianceSensorType = SensorType.Humidity;
            ComplianceSensorReading = humidity;
            ComplianceDetail = ComplianceDetailEnum.HumidityOutOfRange;
            ComplianceStatus = false;
        }
        else if (temperature > MaxTemperature || temperature < MinTemperature)
        {
            ComplianceSensorType = SensorType.Temperature;
            ComplianceSensorReading = temperature;
            ComplianceDetail = ComplianceDetailEnum.TemperatureOutOfRange;
            ComplianceStatus = false;
        }

        if (ComplianceStatus == false)
        {
            State = StateType.OutOfCompliance;
        }

       Verification.Assert(State == StateType.OutOfCompliance ||
                            State == StateType.InTransit ||
                            State == StateType.Created);
    }

    function TransferResponsibility(address newCounterparty) public
    {
        // keep the state checking, message sender, and device checks separate
        // to not get cloberred by the order of evaluation for logical OR
        if ( State == StateType.Completed )
        {
            revert();
        }

        if ( State == StateType.OutOfCompliance )
        {
            revert();
        }

        if ( InitiatingCounterparty != msg.sender && Counterparty != msg.sender )
        {
            revert();
        }

        if ( newCounterparty == Device )
        {
            revert();
        }

       Verification.Assert(State == StateType.InTransit ||
                            State == StateType.Created);

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
        // keep the state checking, message sender, and device checks separate
        // to not get cloberred by the order of evaluation for logical OR
        if ( State == StateType.Completed )
        {
            revert();
        }

        if ( State == StateType.OutOfCompliance )
        {
            revert();
        }

        if (Owner != msg.sender && SupplyChainOwner != msg.sender)
        {
            revert();
        }

        //Fix: Add precondition
        if ( State == StateType.Created )
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