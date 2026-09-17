pragma solidity ^0.5.0;

/**
 * @title CounterExampleFiltering
 * @dev Esta variante del contrato CounterExampleFiltering limita la x con un upper_bound de 12.
    Así, confirmamos que una vez que completemos los contraejemplos posibles, llegaremos a una 
 */

contract CounterExampleFiltering {
    uint8 public constant STATE_A = 0;
    uint8 public constant STATE_B = 1;
    uint8 public constant STATE_P = 2;

    int x;
    uint8 state;
    address owner;

    constructor(int x_value) public {
        state = STATE_A;
        x = x_value;
        owner = msg.sender;
    }

    function f() public {
        if (x > 10 && x < 13 && msg.sender == owner) {
            state = STATE_P;
        } else if (x > 10 && x < 13 && msg.sender != owner) {
            state = STATE_B;
        }
    }
}
