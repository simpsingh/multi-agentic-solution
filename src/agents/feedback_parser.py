"""
Feedback Parser Module

Parses user feedback to extract column update commands.
Supports updating any of the 22 fields for a specific column ID.
"""

import re
from typing import Dict, Optional, Any, List
from src.utils.logger import get_logger

logger = get_logger(__name__)


class FeedbackParser:
    """
    Parser for user feedback commands to update column metadata.

    Supports patterns like:
    - Update notes for column id 70 as PII
    - Change data_type for column id 45 to VARCHAR(100)
    - Set nullable to false for column id 23
    - Update description for column id 10 as "Customer name field"
    """

    # Valid field names that can be updated (all 22 fields)
    VALID_FIELDS = {
        'column_id', 'column_name', 'description', 'data_type',
        'data_length', 'precision', 'scale', 'nullable',
        'notes', 'is_header', 'is_body', 'is_trailer',
        'allowed_values', 'format_hint', 'default_value',
        'is_system_generated', 'data_classification',
        'foreign_key_table', 'foreign_key_column',
        'business_rule', 'sample_values', 'section'
    }

    # Fields that should be treated as booleans
    BOOLEAN_FIELDS = {
        'nullable', 'is_header', 'is_body', 'is_trailer',
        'is_system_generated'
    }

    # Fields that should be treated as integers
    INTEGER_FIELDS = {'column_id', 'data_length', 'precision', 'scale'}

    # Fields that can contain JSON arrays or complex values
    JSON_FIELDS = {'allowed_values', 'sample_values'}

    def __init__(self):
        """Initialize the feedback parser."""
        # Compile regex patterns for better performance
        self.patterns = [
            # Pattern 1: "Update {field} for column id {id} as {value}"
            re.compile(
                r'(?:update|change|set|modify)\s+(\w+)\s+'
                r'(?:for\s+)?column\s+(?:id\s+)?(\d+)\s+'
                r'(?:as|to|=)\s+(.+)',
                re.IGNORECASE
            ),
            # Pattern 2: "Set {field} to {value} for column id {id}"
            re.compile(
                r'(?:set|change|update|modify)\s+(\w+)\s+'
                r'(?:to|as|=)\s+(.+?)\s+'
                r'for\s+column\s+(?:id\s+)?(\d+)',
                re.IGNORECASE
            ),
            # Pattern 3: "Column id {id} {field} = {value}"
            re.compile(
                r'column\s+(?:id\s+)?(\d+)\s+'
                r'(\w+)\s*[=:]\s*(.+)',
                re.IGNORECASE
            ),
            # Pattern 4: "For column {id}, {field} should be {value}"
            re.compile(
                r'(?:for\s+)?column\s+(?:id\s+)?(\d+),?\s+'
                r'(\w+)\s+(?:should\s+be|is|=)\s+(.+)',
                re.IGNORECASE
            ),
            # Pattern 5: "Update column_id {id} for {field}: {value}" (NEW - matches your format)
            re.compile(
                r'(?:update|change|set|modify)\s+column[_\s]?id\s+(\d+)\s+'
                r'(?:for\s+)?(\w+)\s*[:=]\s*(.+)',
                re.IGNORECASE
            ),
            # Pattern 6: "Update {field} for column_id {id}: {value}" (NEW - alternate format)
            re.compile(
                r'(?:update|change|set|modify)\s+(\w+)\s+'
                r'(?:for\s+)?column[_\s]?id\s+(\d+)\s*[:=]\s*(.+)',
                re.IGNORECASE
            )
        ]

    def parse(self, feedback: str) -> Optional[Dict[str, Any]]:
        """
        Parse feedback text to extract update command.

        Args:
            feedback: User feedback text

        Returns:
            Dict with parsed command or None if parsing fails
            Format: {
                'action': 'update',
                'column_id': int,
                'field': str,
                'value': Any,
                'original_feedback': str
            }
        """
        if not feedback or not feedback.strip():
            return None

        feedback = feedback.strip()
        logger.info(f"Parsing feedback: {feedback}")

        # Try each pattern
        for pattern_idx, pattern in enumerate(self.patterns):
            match = pattern.search(feedback)
            if match:
                groups = match.groups()

                # Extract based on pattern structure
                if pattern_idx == 0:  # Pattern 1
                    field, column_id, value = groups
                elif pattern_idx == 1:  # Pattern 2
                    field, value, column_id = groups
                elif pattern_idx == 2:  # Pattern 3
                    column_id, field, value = groups
                elif pattern_idx == 3:  # Pattern 4
                    column_id, field, value = groups
                elif pattern_idx == 4:  # Pattern 5 - "Update column_id {id} for {field}: {value}"
                    column_id, field, value = groups
                elif pattern_idx == 5:  # Pattern 6 - "Update {field} for column_id {id}: {value}"
                    field, column_id, value = groups

                # Normalize field name
                field = field.lower().strip()

                # Validate field name
                if field not in self.VALID_FIELDS:
                    logger.warning(f"Invalid field name: {field}")
                    # Try to find closest match
                    field = self._find_closest_field(field)
                    if not field:
                        continue

                # Parse column ID
                try:
                    column_id = int(column_id)
                except ValueError:
                    logger.error(f"Invalid column ID: {column_id}")
                    continue

                # Process value based on field type
                value = self._process_value(field, value.strip())

                result = {
                    'action': 'update',
                    'column_id': column_id,
                    'field': field,
                    'value': value,
                    'original_feedback': feedback
                }

                logger.info(f"Successfully parsed feedback: {result}")
                return result

        logger.warning(f"Could not parse feedback: {feedback}")
        return None

    def _find_closest_field(self, field: str) -> Optional[str]:
        """
        Find the closest matching valid field name.

        Args:
            field: Input field name

        Returns:
            Closest valid field name or None
        """
        field_lower = field.lower()

        # Common aliases
        aliases = {
            'type': 'data_type',
            'length': 'data_length',
            'null': 'nullable',
            'desc': 'description',
            'classification': 'data_classification',
            'fk_table': 'foreign_key_table',
            'fk_column': 'foreign_key_column',
            'rule': 'business_rule',
            'format': 'format_hint',
            'default': 'default_value',
            'values': 'allowed_values',
            'samples': 'sample_values',
            'generated': 'is_system_generated'
        }

        if field_lower in aliases:
            return aliases[field_lower]

        # Check for partial matches
        for valid_field in self.VALID_FIELDS:
            if field_lower in valid_field or valid_field in field_lower:
                return valid_field

        return None

    def _process_value(self, field: str, value: str) -> Any:
        """
        Process value based on field type.

        Args:
            field: Field name
            value: Raw value string

        Returns:
            Processed value in appropriate type
        """
        # Remove quotes if present
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1]

        # Handle boolean fields
        if field in self.BOOLEAN_FIELDS:
            value_lower = value.lower()
            if value_lower in ('true', 'yes', '1', 'y', 't'):
                return True
            elif value_lower in ('false', 'no', '0', 'n', 'f'):
                return False
            else:
                logger.warning(f"Invalid boolean value: {value}, defaulting to False")
                return False

        # Handle integer fields
        if field in self.INTEGER_FIELDS:
            try:
                return int(value)
            except ValueError:
                logger.warning(f"Invalid integer value for {field}: {value}")
                return None

        # Handle JSON array fields
        if field in self.JSON_FIELDS:
            # Check if it looks like a JSON array
            if value.startswith('[') and value.endswith(']'):
                import json
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON array: {value}")
                    # Try to parse as comma-separated list
                    return [v.strip() for v in value[1:-1].split(',')]
            # Handle comma-separated values
            elif ',' in value:
                return [v.strip() for v in value.split(',')]
            else:
                # Single value, wrap in array
                return [value]

        # Handle NULL values
        if value.upper() in ('NULL', 'NONE', 'N/A'):
            return None

        # Default: return as string
        return value

    def parse_multiple(self, feedback: str) -> List[Dict[str, Any]]:
        """
        Parse feedback that may contain multiple update commands.

        Args:
            feedback: User feedback text

        Returns:
            List of parsed commands
        """
        commands = []

        # Split by common separators
        parts = re.split(r'[;,\n]|and\s+', feedback, flags=re.IGNORECASE)

        for part in parts:
            parsed = self.parse(part)
            if parsed:
                commands.append(parsed)

        return commands


# Singleton instance
feedback_parser = FeedbackParser()