"""Utility functions for currency conversion"""

from decimal import Decimal


def bnb_to_wei(bnb_amount: Decimal) -> str:
    """
    Convert BNB to Wei
    
    Args:
        bnb_amount: Amount in BNB
        
    Returns:
        Amount in Wei as string
    """
    wei_per_bnb = Decimal("1000000000000000000")  # 10^18
    wei_amount = int(bnb_amount * wei_per_bnb)
    return str(wei_amount)


def wei_to_bnb(wei_amount: str) -> Decimal:
    """
    Convert Wei to BNB
    
    Args:
        wei_amount: Amount in Wei as string
        
    Returns:
        Amount in BNB as Decimal
    """
    wei_per_bnb = Decimal("1000000000000000000")  # 10^18
    return Decimal(wei_amount) / wei_per_bnb
