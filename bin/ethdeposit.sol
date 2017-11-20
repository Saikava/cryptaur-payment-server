// blashyrkh.maniac.coding

pragma solidity ^0.4.0;

contract Owned
{
    address public owner;
    address public newOwner;

    function Owned()
    {
        owner=msg.sender;
    }

    modifier onlyOwner
    {
        require(owner==msg.sender);
        _;
    }

    function changeOwner(address _newOwner) public onlyOwner
    {
        require(_newOwner!=0);
        newOwner=_newOwner;
    }

    function acceptOwnership() public
    {
        require(msg.sender==newOwner);
        owner=newOwner;
        delete newOwner;
    }
}

contract AbstractDepositHost
{
    uint32 public gasAmount;
    function forwardDeposit(uint32 _userid) public payable;
}

contract DepositWallet
{
    address public host;
    uint32 public userid;

    function DepositWallet(address _host, uint32 _userid)
    {
        require(_host!=0);

        host=_host;
        userid=_userid;
    }

    function() payable
    {
        uint32 gasAmount=AbstractDepositHost(host).gasAmount();
        AbstractDepositHost(host).forwardDeposit.value(this.balance).gas(gasAmount)(userid);
    }
}

contract DepositHost is Owned, AbstractDepositHost
{
    address public forwardAddress;
    address public depositMaster;
    mapping (uint32 => address) public depositAddresses;

    event Deposit(uint32 userid, uint amountWei);
    event NewDepositAddress(uint32 userid, address depositAddress);

    modifier onlyDepositMaster
    {
        require(owner==msg.sender || depositMaster==msg.sender);
        _;
    }

    function DepositHost() Owned()
    {
        depositMaster=owner;
        gasAmount=3000000;
    }

    function setForwardAddress(address _forwardAddress) public onlyOwner
    {
        forwardAddress=_forwardAddress;
    }

    function setDepositMaster(address _depositMaster) public onlyOwner
    {
        depositMaster=_depositMaster;
    }

    function setGasAmount(uint32 _newGasAmount) public onlyDepositMaster
    {
        gasAmount=_newGasAmount;
    }

    function forwardDeposit(uint32 _userid) public payable
    {
        require(forwardAddress.call.gas(gasAmount).value(this.balance)());
        Deposit(_userid, msg.value);
    }

    function getExistingDepositAddress(uint32 _userid) public constant returns(address)
    {
        return depositAddresses[_userid];
    }

    function generateDepositAddress(uint32 _userid) public onlyDepositMaster
    {
        if(depositAddresses[_userid]==0)
        {
            depositAddresses[_userid]=new DepositWallet(this, _userid);
        }
        NewDepositAddress(_userid, depositAddresses[_userid]);
    }
}
