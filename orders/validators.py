"""
PUBG Player ID Validation Utilities

Validates PUBG Mobile player IDs according to official format rules:
- Length: 1-24 characters
- Allowed: Alphanumeric (A-Z, a-z, 0-9) and hyphens (-)
- Cannot start or end with hyphen
- No consecutive hyphens
"""

import re
from django.core.exceptions import ValidationError


def validate_pubg_player_id(player_id):
    """
    Validate PUBG Mobile Player ID format.
    
    Args:
        player_id (str): The PUBG player ID to validate
        
    Raises:
        ValidationError: If player ID doesn't meet format requirements
    """
    if not player_id:
        raise ValidationError("Player ID is required.")
    
    player_id = player_id.strip()
    
    # Check length (1-24 characters)
    if len(player_id) < 1 or len(player_id) > 24:
        raise ValidationError(
            f"Player ID must be 1-24 characters long (currently {len(player_id)} chars)."
        )
    
    # Check allowed characters (alphanumeric + hyphens only)
    if not re.match(r'^[a-zA-Z0-9\-]+$', player_id):
        raise ValidationError(
            "Player ID can only contain letters, numbers, and hyphens."
        )
    
    # Cannot start or end with hyphen
    if player_id.startswith('-') or player_id.endswith('-'):
        raise ValidationError(
            "Player ID cannot start or end with a hyphen."
        )
    
    # No consecutive hyphens
    if '--' in player_id:
        raise ValidationError(
            "Player ID cannot contain consecutive hyphens."
        )
    
    return player_id


def is_valid_pubg_player_id(player_id):
    """
    Check if PUBG player ID is valid (returns boolean, no exceptions).
    
    Args:
        player_id (str): The PUBG player ID to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        validate_pubg_player_id(player_id)
        return True
    except ValidationError:
        return False


def get_player_id_error_message(player_id):
    """
    Get validation error message for PUBG player ID (returns string or None).
    
    Args:
        player_id (str): The PUBG player ID to validate
        
    Returns:
        str: Error message if invalid, None if valid
    """
    try:
        validate_pubg_player_id(player_id)
        return None
    except ValidationError as e:
        return str(e)
