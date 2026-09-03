// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Cairn attestations
/// @notice Publishes a verdict so the record survives outside Cairn.
///
/// ERC-8004 defers verification to a Validation Registry that has no mainnet
/// deployment, so there is nothing on Base to write a grounded verdict into.
/// This is the smallest contract that fixes that: it stores nothing it does not
/// need and asserts nothing it cannot evidence.
///
/// A verdict is only meaningful with the observations behind it, so `basisHash`
/// is the keccak of the observation ids the verdict rested on, and `basisCount`
/// is how many there were. A reader who has the dossier can recompute the hash
/// and prove the published verdict is the one Cairn actually held. A reader who
/// does not can still see that a verdict with zero observations behind it is
/// worth nothing.
contract CairnAttestations {
    /// @dev Kept neutral on purpose: grounded, thin, suspect, dormant. Nothing
    /// here calls an agent fraudulent, because Cairn cannot support that claim.
    event Attested(
        address indexed attestor,
        address indexed counterparty,
        bytes32 indexed standing,
        uint16 confidenceBps,
        uint32 basisCount,
        bytes32 basisHash,
        uint64 evaluatedAt
    );

    error EmptyBasisForGroundedVerdict();
    error ConfidenceOutOfRange();

    /// @notice Publish one verdict.
    /// @param counterparty the agent the verdict is about
    /// @param standing keccak of "grounded" | "thin" | "suspect" | "dormant"
    /// @param confidenceBps confidence in basis points, 0 to 10000
    /// @param basisCount how many observations the verdict rested on
    /// @param basisHash keccak of the concatenated observation ids
    /// @param evaluatedAt unix seconds the verdict was computed
    function attest(
        address counterparty,
        bytes32 standing,
        uint16 confidenceBps,
        uint32 basisCount,
        bytes32 basisHash,
        uint64 evaluatedAt
    ) external {
        if (confidenceBps > 10000) revert ConfidenceOutOfRange();

        // The same rule the verdict engine enforces off chain, enforced again
        // here: a grounded verdict that names no observations is not publishable.
        if (standing == keccak256("grounded") && basisCount == 0) {
            revert EmptyBasisForGroundedVerdict();
        }

        emit Attested(
            msg.sender,
            counterparty,
            standing,
            confidenceBps,
            basisCount,
            basisHash,
            evaluatedAt
        );
    }
}
