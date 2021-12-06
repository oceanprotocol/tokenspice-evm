// SPDX-License-Identifier: Unknown
pragma solidity 0.8.10;

interface IV3Factory {
        
      function newBPool( 
        address controller, 
        address datatokenAddress, 
        address basetokenAddress, 
        address publisherAddress, 
        uint256 burnInEndBlock,
        uint256[] memory ssParams) external
        returns (address bpool);
}