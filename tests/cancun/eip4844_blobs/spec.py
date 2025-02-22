"""
Defines EIP-4844 specification constants and functions.
"""
from dataclasses import dataclass
from hashlib import sha256
from typing import Optional


@dataclass(frozen=True)
class ReferenceSpec:
    """
    Defines the reference spec version and git path.
    """

    git_path: str
    version: str


ref_spec_4844 = ReferenceSpec("EIPS/eip-4844.md", "f0eb6a364aaf5ccb43516fa2c269a54fb881ecfd")


@dataclass(frozen=True)
class BlockHeaderDataGasFields:
    """
    A helper class for the data gas fields in a block header.
    """

    excess_data_gas: int
    data_gas_used: int


# Constants
@dataclass(frozen=True)
class Spec:
    """
    Parameters from the EIP-4844 specifications as defined at
    https://eips.ethereum.org/EIPS/eip-4844#parameters

    If the parameter is not currently used within the tests, it is commented
    out.
    """

    BLOB_TX_TYPE = 0x03
    FIELD_ELEMENTS_PER_BLOB = 4096
    BLS_MODULUS = 0x73EDA753299D7D483339D80809A1D80553BDA402FFFE5BFEFFFFFFFF00000001
    BLOB_COMMITMENT_VERSION_KZG = 1
    POINT_EVALUATION_PRECOMPILE_ADDRESS = 10
    POINT_EVALUATION_PRECOMPILE_GAS = 50_000
    MAX_DATA_GAS_PER_BLOCK = 786432
    TARGET_DATA_GAS_PER_BLOCK = 393216
    MIN_DATA_GASPRICE = 1
    DATA_GASPRICE_UPDATE_FRACTION = 3338477
    # MAX_VERSIONED_HASHES_LIST_SIZE = 2**24
    # MAX_CALLDATA_SIZE = 2**24
    # MAX_ACCESS_LIST_SIZE = 2**24
    # MAX_ACCESS_LIST_STORAGE_KEYS = 2**24
    # MAX_TX_WRAP_COMMITMENTS = 2**12
    # LIMIT_BLOBS_PER_TX = 2**12
    DATA_GAS_PER_BLOB = 2**17
    HASH_OPCODE_BYTE = 0x49
    HASH_GAS_COST = 3

    @classmethod
    def kzg_to_versioned_hash(
        cls,
        kzg_commitment: bytes | int,  # 48 bytes
        blob_commitment_version_kzg: Optional[bytes | int] = None,
    ) -> bytes:
        """
        Calculates the versioned hash for a given KZG commitment.
        """
        if blob_commitment_version_kzg is None:
            blob_commitment_version_kzg = cls.BLOB_COMMITMENT_VERSION_KZG
        if isinstance(kzg_commitment, int):
            kzg_commitment = kzg_commitment.to_bytes(48, "big")
        if isinstance(blob_commitment_version_kzg, int):
            blob_commitment_version_kzg = blob_commitment_version_kzg.to_bytes(1, "big")
        return blob_commitment_version_kzg + sha256(kzg_commitment).digest()[1:]

    @classmethod
    def fake_exponential(cls, factor: int, numerator: int, denominator: int) -> int:
        """
        Used to calculate the data gas cost.
        """
        i = 1
        output = 0
        numerator_accumulator = factor * denominator
        while numerator_accumulator > 0:
            output += numerator_accumulator
            numerator_accumulator = (numerator_accumulator * numerator) // (denominator * i)
            i += 1
        return output // denominator

    @classmethod
    def calc_excess_data_gas(cls, parent: BlockHeaderDataGasFields) -> int:
        """
        Calculate the excess data gas for a block given the excess data gas
        and data gas used from the parent block header.
        """
        if parent.excess_data_gas + parent.data_gas_used < cls.TARGET_DATA_GAS_PER_BLOCK:
            return 0
        else:
            return parent.excess_data_gas + parent.data_gas_used - cls.TARGET_DATA_GAS_PER_BLOCK

    # Note: Currently unused.
    # @classmethod
    # def get_total_data_gas(cls, tx: Transaction) -> int:
    #     """
    #     Calculate the total data gas for a transaction.
    #     """
    #     if tx.blob_versioned_hashes is None:
    #         return 0
    #     return cls.DATA_GAS_PER_BLOB * len(tx.blob_versioned_hashes)

    @classmethod
    def get_data_gasprice(cls, *, excess_data_gas: int) -> int:
        """
        Calculate the data gas price from the excess.
        """
        return cls.fake_exponential(
            cls.MIN_DATA_GASPRICE,
            excess_data_gas,
            cls.DATA_GASPRICE_UPDATE_FRACTION,
        )


@dataclass(frozen=True)
class SpecHelpers:
    """
    Define parameters and helper functions that are tightly coupled to the 4844
    spec but not strictly part of it.
    """

    BYTES_PER_FIELD_ELEMENT = 32

    @classmethod
    def max_blobs_per_block(cls) -> int:  # MAX_BLOBS_PER_BLOCK =
        """
        Returns the maximum number of blobs per block.
        """
        return Spec.MAX_DATA_GAS_PER_BLOCK // Spec.DATA_GAS_PER_BLOB

    @classmethod
    def target_blobs_per_block(cls) -> int:
        """
        Returns the target number of blobs per block.
        """
        return Spec.TARGET_DATA_GAS_PER_BLOCK // Spec.DATA_GAS_PER_BLOB

    @classmethod
    def calc_excess_data_gas_from_blob_count(
        cls, parent_excess_data_gas: int, parent_blob_count: int
    ) -> int:
        """
        Calculate the excess data gas for a block given the parent excess data gas
        and the number of blobs in the block.
        """
        parent_consumed_data_gas = parent_blob_count * Spec.DATA_GAS_PER_BLOB
        return Spec.calc_excess_data_gas(
            BlockHeaderDataGasFields(parent_excess_data_gas, parent_consumed_data_gas)
        )

    @classmethod
    def get_min_excess_data_gas_for_data_gas_price(cls, data_gas_price: int) -> int:
        """
        Gets the minimum required excess data gas value to get a given data gas cost in a block
        """
        current_excess_data_gas = 0
        current_data_gas_price = 1
        while current_data_gas_price < data_gas_price:
            current_excess_data_gas += Spec.DATA_GAS_PER_BLOB
            current_data_gas_price = Spec.get_data_gasprice(
                excess_data_gas=current_excess_data_gas
            )
        return current_excess_data_gas

    @classmethod
    def get_min_excess_data_blobs_for_data_gas_price(cls, data_gas_price: int) -> int:
        """
        Gets the minimum required excess data blobs to get a given data gas cost in a block
        """
        return (
            cls.get_min_excess_data_gas_for_data_gas_price(data_gas_price)
            // Spec.DATA_GAS_PER_BLOB
        )
