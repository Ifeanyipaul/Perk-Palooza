import secrets
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Wallet, WalletTransaction


@transaction.atomic
def credit_verified_funding(reference, verified_amount):
    """
    Credit a wallet only after a trusted payment provider
    has confirmed that the payment was successful.
    """

    try:
        verified_amount = Decimal(str(verified_amount))
    except Exception:
        raise ValidationError("Invalid payment amount.")

    if not verified_amount.is_finite() or verified_amount <= Decimal("0.00"):
        raise ValidationError("Payment amount must be greater than zero.")

    # Lock the transaction so the same payment cannot be
    # processed concurrently more than once.
    try:
        wallet_transaction = (
            WalletTransaction.objects
            .select_for_update()
            .get(reference=reference)
        )
    except WalletTransaction.DoesNotExist:
        raise ValidationError("Funding transaction was not found.")

    if wallet_transaction.transaction_type != "FUNDING":
        raise ValidationError("This is not a wallet funding transaction.")

    if wallet_transaction.status != "PENDING":
        raise ValidationError("This transaction has already been processed.")

    if wallet_transaction.amount != verified_amount:
        raise ValidationError("Verified payment amount does not match.")

    # Lock the wallet before changing its balance.
    wallet = (
        Wallet.objects
        .select_for_update()
        .get(pk=wallet_transaction.wallet_id)
    )

    wallet.available_balance += verified_amount
    wallet.total_funded += verified_amount

    wallet.save(update_fields=[
        "available_balance",
        "total_funded",
        "updated_at",
    ])

    wallet_transaction.status = "SUCCESS"
    wallet_transaction.save(update_fields=["status"])

    return wallet


@transaction.atomic
def commit_wallet_funds(user, amount, reference, description="Gift card commitment"):
    """
    Move money from available balance to committed balance.
    This reserves funds for a gift card.
    """

    try:
        amount = Decimal(str(amount))
    except Exception:
        raise ValidationError("Invalid commitment amount.")

    if not amount.is_finite() or amount <= Decimal("0.00"):
        raise ValidationError("Amount must be greater than zero.")

    # Our current wallet supports two decimal places.
    if amount != amount.quantize(Decimal("0.01")):
        raise ValidationError("Amount cannot have more than two decimal places.")

    if user.role != "GIVER":
        raise ValidationError("Only givers can commit wallet funds.")

    if not reference or len(reference) > 100:
        raise ValidationError("A valid transaction reference is required.")

    if WalletTransaction.objects.filter(reference=reference).exists():
        raise ValidationError("This transaction reference already exists.")

    try:
        wallet = Wallet.objects.select_for_update().get(user=user)
    except Wallet.DoesNotExist:
        raise ValidationError("Wallet not found.")

    if wallet.available_balance < amount:
        raise ValidationError("Insufficient available balance.")

    wallet.available_balance -= amount
    wallet.committed_balance += amount

    wallet.save(update_fields=[
        "available_balance",
        "committed_balance",
        "updated_at",
    ])

    wallet_transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="CARD_COMMITMENT",
        amount=amount,
        status="SUCCESS",
        reference=reference,
        description=description,
    )

    return wallet_transaction


@transaction.atomic
def release_committed_funds(
    commitment_reference,
    release_reference,
    description="Gift card cancellation"
):
    """
    Return committed funds to the giver's available balance
    when an eligible gift card is cancelled before redemption.
    """

    if not release_reference or len(release_reference) > 100:
        raise ValidationError("A valid release reference is required.")

    try:
        commitment = (
            WalletTransaction.objects
            .select_for_update()
            .get(reference=commitment_reference)
        )
    except WalletTransaction.DoesNotExist:
        raise ValidationError("Original commitment not found.")

    if commitment.transaction_type != "CARD_COMMITMENT":
        raise ValidationError("Transaction is not a card commitment.")

    if commitment.status != "SUCCESS":
        raise ValidationError("Only successful commitments can be released.")

    if WalletTransaction.objects.filter(reverses=commitment).exists():
        raise ValidationError("These committed funds have already been released.")

    if WalletTransaction.objects.filter(reference=release_reference).exists():
        raise ValidationError("Release reference already exists.")

    wallet = Wallet.objects.select_for_update().get(
        pk=commitment.wallet_id
    )

    if wallet.committed_balance < commitment.amount:
        raise ValidationError("Insufficient committed balance.")

    wallet.committed_balance -= commitment.amount
    wallet.available_balance += commitment.amount

    wallet.save(update_fields=[
        "available_balance",
        "committed_balance",
        "updated_at",
    ])

    release_transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="CARD_CANCELLATION",
        amount=commitment.amount,
        status="SUCCESS",
        reference=release_reference,
        description=description,
        reverses=commitment,
    )

    return release_transaction

@transaction.atomic
def create_pending_funding(user, amount):
    """
    Create a pending wallet funding transaction.

    This does not credit the wallet.
    Wallet credit happens only after trusted payment verification.
    """

    try:
        amount = Decimal(str(amount))
    except Exception:
        raise ValidationError("Invalid funding amount.")

    if not amount.is_finite() or amount <= Decimal("0.00"):
        raise ValidationError("Funding amount must be greater than zero.")

    if amount != amount.quantize(Decimal("0.01")):
        raise ValidationError(
            "Funding amount cannot have more than two decimal places."
        )

    if not user or not user.is_authenticated or not user.is_active:
        raise ValidationError("An active authenticated user is required.")

    if user.role != "GIVER":
        raise ValidationError("Only givers can fund wallets.")

    try:
        wallet = Wallet.objects.get(user=user)
    except Wallet.DoesNotExist:
        raise ValidationError("Wallet not found.")

    reference = f"PP-FUND-{secrets.token_urlsafe(24)}"

    funding_transaction = WalletTransaction.objects.create(
        wallet=wallet,
        transaction_type="FUNDING",
        amount=amount,
        status="PENDING",
        reference=reference,
        description="Wallet funding initiated"
    )

    return funding_transaction