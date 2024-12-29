

// File: installed_contracts/openzeppelin-solidity/contracts/payment/escrow/RefundEscrow.sol

pragma solidity ^0.5.0;

library SafeMath {
    /**
     * @dev Multiplies two unsigned integers, reverts on overflow.
     */
    function mul(uint256 a, uint256 b) internal pure returns (uint256) {
        // Gas optimization: this is cheaper than requiring 'a' not being zero, but the
        // benefit is lost if 'b' is also tested.
        // See: https://github.com/OpenZeppelin/openzeppelin-solidity/pull/522
        if (a == 0) {
            return 0;
        }

        uint256 c = a * b;
        require(c / a == b);

        return c;
    }

    /**
     * @dev Integer division of two unsigned integers truncating the quotient, reverts on division by zero.
     */
    function div(uint256 a, uint256 b) internal pure returns (uint256) {
        // Solidity only automatically asserts when dividing by 0
        require(b > 0);
        uint256 c = a / b;
        // assert(a == b * c + a % b); // There is no case in which this doesn't hold

        return c;
    }

    /**
     * @dev Subtracts two unsigned integers, reverts on overflow (i.e. if subtrahend is greater than minuend).
     */
    function sub(uint256 a, uint256 b) internal pure returns (uint256) {
        require(b <= a);
        uint256 c = a - b;

        return c;
    }

    /**
     * @dev Adds two unsigned integers, reverts on overflow.
     */
    function add(uint256 a, uint256 b) internal pure returns (uint256) {
        uint256 c = a + b;
        require(c >= a);

        return c;
    }

    /**
     * @dev Divides two unsigned integers and returns the remainder (unsigned integer modulo),
     * reverts when dividing by zero.
     */
    function mod(uint256 a, uint256 b) internal pure returns (uint256) {
        require(b != 0);
        return a % b;
    }
}



/**
 * @title RefundEscrow
 * @dev Escrow that holds funds for a beneficiary, deposited from multiple
 * parties.
 * @dev Intended usage: See Escrow.sol. Same usage guidelines apply here.
 * @dev The primary account (that is, the contract that instantiates this
 * contract) may deposit, close the deposit period, and allow for either
 * withdrawal by the beneficiary, or refunds to the depositors. All interactions
 * with RefundEscrow will be made through the primary contract. See the
 * RefundableCrowdsale contract for an example of RefundEscrow’s use.
 */
contract RefundEscrow {
    using SafeMath for uint256;

    enum State { Active, Refunding, Closed }

    event RefundsClosed();
    event RefundsEnabled();

    State private _state;
    address payable private _beneficiary;
    address private _primary;

    bool hasA = false;
    address public A;

    /**
     * @dev Constructor.
     * @param beneficiary The beneficiary of the deposits.
     */
    constructor (address payable beneficiary, address _A) public {
        require(beneficiary != address(0));
        _beneficiary = beneficiary;
        _state = State.Active;
        A = _A;
        _primary = msg.sender;
    }

    /**
     * @dev Reverts if called from any account other than the primary.
     */
    modifier onlyPrimary() {
        require(msg.sender == _primary);
        _;
    }

    /**
     * @return the address of the primary.
     */
    function primary() public view returns (address) {
        return _primary;
    }

    /**
     * @dev Transfers contract to a new primary.
     * @param recipient The address of new primary.
     */
    function transferPrimary(address recipient) public onlyPrimary {
        require(recipient != address(0));
        _primary = recipient;
        // emit PrimaryTransferred(_primary);
    }

    /**
     * @return the current state of the escrow.
     */
    function state() public view returns (State) {
        return _state;
    }

    /**
     * @return the beneficiary of the escrow.
     */
    function beneficiary() public view returns (address) {
        return _beneficiary;
    }

    /**
     * @dev Stores funds that may later be refunded.
     * @param refundee The address funds will be sent to if a refund occurs.
     */
    function deposit(address refundee) public payable onlyPrimary {
        require(_state == State.Active);
        depositInternal(refundee);
    }

    /**
     * @dev Allows for the beneficiary to withdraw their funds, rejecting
     * further deposits.
     */
    function close() public onlyPrimary  {
        require(_state == State.Active);
        _state = State.Closed;
        //emit RefundsClosed();
    }

    /**
     * @dev Allows for refunds to take place, rejecting further deposits.
     */
    function enableRefunds() public  onlyPrimary{
        require(_state == State.Active);
        _state = State.Refunding;
        //emit RefundsEnabled();
    }

    /**
     * @dev Withdraws the beneficiary's funds.
     */
    function beneficiaryWithdraw() public {
        require(_state == State.Closed);
        require(address(this).balance > 0);
        _beneficiary.transfer(address(this).balance);
    }

    /**
     * @dev Returns whether refundees can withdraw their deposits (be refunded). The overridden function receives a
     * 'payee' argument, but we ignore it here since the condition is global, not per-payee.
     */
    function withdrawalAllowed(address) internal view returns (bool) {
        return _state == State.Refunding;
    }

    uint depositsCount = 0;

    event Deposited(address indexed payee, uint256 weiAmount);
    event Withdrawn(address indexed payee, uint256 weiAmount);

    mapping(address => uint256) private _deposits;

    function depositsOf(address payee) internal view returns (uint256) {
        return _deposits[payee];
    }

    /**
     * @dev Stores the sent amount as credit to be withdrawn.
     * @param payee The destination address of the funds.
     */
    function depositInternal(address payee) internal {
        uint256 amount = msg.value;
        if (_deposits[payee] == 0) {
            depositsCount += 1;
        }
        _deposits[payee] = _deposits[payee].add(amount);
        if (payee == A) {
            hasA = true;
        }

        //emit Deposited(payee, amount);
    }

    /**
     * @dev Withdraw accumulated balance for a payee.
     * @param payee The address whose funds will be withdrawn and transferred to.
     */
    function withdrawInternal(address payable payee) internal  {
        uint256 payment = _deposits[payee];

        _deposits[payee] = 0;

        payee.transfer(payment);

        depositsCount -= 1;

       // emit Withdrawn(payee, payment);
    }

    // function length() public returns(uint) {
    //     return depositsArray.length; 
    // }


    function withdrawA(address payable payee) public onlyPrimary {
        require(withdrawalAllowed(payee));
        require(hasA && A == payee && depositsCount > 0);
        require(_deposits[payee] > 0);
        withdrawInternal(payee);
        hasA = false;
    }
    
    function withdrawOther(address payable payee) public onlyPrimary {
        require(withdrawalAllowed(payee));
        require(A != payee && depositsCount > 0 && (!hasA || depositsCount > 1));
        require(_deposits[payee] > 0);
        withdrawInternal(payee);
    }

}