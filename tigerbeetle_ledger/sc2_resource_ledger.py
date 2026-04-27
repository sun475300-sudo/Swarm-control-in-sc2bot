"""
Phase 443: TigerBeetle - SC2 Resource Ledger
Double-entry bookkeeping for SC2 mineral/gas economy tracking.
"""

import logging
from dataclasses import dataclass
from enum import IntEnum

import tigerbeetle as tb

logger = logging.getLogger(__name__)


# TigerBeetle account IDs
class AccountID(IntEnum):
    MINERAL_INCOME = 1
    MINERAL_SPENDING = 2
    GAS_INCOME = 3
    GAS_SPENDING = 4
    MINERAL_RESERVE = 5
    GAS_RESERVE = 6


@dataclass
class ResourceTransfer:
    transfer_id: int
    debit_account: AccountID
    credit_account: AccountID
    amount: int
    user_data: int  # game tick
    code: int  # transfer type code


TRANSFER_CODES = {
    "drone_mine": 1,
    "structure_build": 2,
    "unit_train": 3,
    "gas_harvest": 4,
    "refund": 5,
}


def create_accounts(client: tb.Client):
    """Create double-entry accounts for SC2 resource tracking."""
    accounts = [
        tb.Account(
            id=int(AccountID.MINERAL_INCOME),
            ledger=1,
            code=1,
            flags=tb.AccountFlags.CREDITS_MUST_NOT_EXCEED_DEBITS,
        ),
        tb.Account(
            id=int(AccountID.MINERAL_SPENDING),
            ledger=1,
            code=2,
            flags=tb.AccountFlags.DEBITS_MUST_NOT_EXCEED_CREDITS,
        ),
        tb.Account(
            id=int(AccountID.GAS_INCOME),
            ledger=2,
            code=3,
            flags=tb.AccountFlags.CREDITS_MUST_NOT_EXCEED_DEBITS,
        ),
        tb.Account(
            id=int(AccountID.GAS_SPENDING),
            ledger=2,
            code=4,
            flags=tb.AccountFlags.DEBITS_MUST_NOT_EXCEED_CREDITS,
        ),
    ]
    errors = client.create_accounts(accounts)
    if errors:
        logger.error(f"Account creation errors: {errors}")
    else:
        logger.info("SC2 resource accounts created.")


def record_mineral_income(client: tb.Client, amount: int, tick: int, transfer_id: int):
    """Record mineral mining income (debit income, credit reserve)."""
    transfers = [
        tb.Transfer(
            id=transfer_id,
            debit_account_id=int(AccountID.MINERAL_INCOME),
            credit_account_id=int(AccountID.MINERAL_RESERVE),
            amount=amount,
            ledger=1,
            code=TRANSFER_CODES["drone_mine"],
            user_data_64=tick,
        )
    ]
    errors = client.create_transfers(transfers)
    if errors:
        logger.error(f"Transfer error: {errors}")


def record_spending(
    client: tb.Client, resource: str, amount: int, tick: int, transfer_id: int
):
    """Record mineral or gas spending for buildings/units."""
    if resource == "mineral":
        debit_id = int(AccountID.MINERAL_RESERVE)
        credit_id = int(AccountID.MINERAL_SPENDING)
        ledger = 1
    else:
        debit_id = int(AccountID.GAS_RESERVE)
        credit_id = int(AccountID.GAS_SPENDING)
        ledger = 2

    transfers = [
        tb.Transfer(
            id=transfer_id,
            debit_account_id=debit_id,
            credit_account_id=credit_id,
            amount=amount,
            ledger=ledger,
            code=TRANSFER_CODES["unit_train"],
            user_data_64=tick,
        )
    ]
    errors = client.create_transfers(transfers)
    if errors:
        logger.error(f"Spending transfer error: {errors}")


def get_account_balance(client: tb.Client, account_id: AccountID) -> dict:
    """Query current balance of a resource account."""
    accounts = client.lookup_accounts([int(account_id)])
    if accounts:
        a = accounts[0]
        return {
            "id": account_id.name,
            "debits_posted": a.debits_posted,
            "credits_posted": a.credits_posted,
            "net": a.credits_posted - a.debits_posted,
        }
    return {}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    with tb.Client(0, ["127.0.0.1:3000"]) as client:
        create_accounts(client)
        record_mineral_income(client, amount=50, tick=100, transfer_id=1)
        record_mineral_income(client, amount=50, tick=110, transfer_id=2)
        record_spending(client, "mineral", amount=75, tick=150, transfer_id=3)
        bal = get_account_balance(client, AccountID.MINERAL_RESERVE)
        print("Mineral reserve balance:", bal)
