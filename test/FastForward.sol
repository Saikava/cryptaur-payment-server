// blashyrkh.maniac.coding

pragma solidity ^0.4.0;

contract Owned
{
    address public owner;

    function Owned()
    {
        owner=msg.sender;
    }

    modifier onlyOwner
    {
        require(owner==msg.sender);
        _;
    }
}

contract FastForward is Owned
{
    uint32 public gasAmount;
    address public forwardAddress;

    function FastForward() Owned()
    {
        gasAmount=1000000;
        forwardAddress=owner;
    }

    function setGasAmount(uint32 _gasAmount) public onlyOwner
    {
        gasAmount=_gasAmount;
    }

    function setForwardAddress(address _forwardAddress) public onlyOwner
    {
        forwardAddress=_forwardAddress;
    }

    function() payable
    {
        require(forwardAddress.call.gas(gasAmount).value(this.balance)());
    }
}
