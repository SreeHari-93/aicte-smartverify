import re
import difflib
from datetime import datetime, date, timedelta
from typing import Any, Tuple, Optional
from backend.app.services.rule_engine.context import EvaluationContext


class SafePathResolver:
    """
    Safely resolves path expressions like:
      - 'application.intake_total'
      - 'institute.name'
      - 'doc.AFFIDAVIT.institute_name'
      - 'today'
    Returns (value, error_message). Never throws unhandled exceptions.
    """

    @staticmethod
    def resolve(path_str: str, context: EvaluationContext) -> Tuple[Any, Optional[str]]:
        if not path_str or not isinstance(path_str, str):
            return None, "Path string is empty or invalid."

        path = path_str.strip()

        # Special keywords
        if path.lower() == "today":
            return context.get_today().isoformat(), None

        # Constant literals or direct values
        if path.startswith("'") and path.endswith("'") and len(path) >= 2:
            return path[1:-1], None
        if path.startswith('"') and path.endswith('"') and len(path) >= 2:
            return path[1:-1], None

        tokens = path.split(".")
        root = tokens[0].lower()

        # 1. Application scope
        if root == "application":
            if len(tokens) == 1:
                return context.application, None
            sub_key = ".".join(tokens[1:])
            # Try nested or direct key lookup
            val = SafePathResolver._lookup_dict(context.application, tokens[1:])
            if val is not None:
                return val, None
            return None, f"Field '{sub_key}' not found in application data."

        # 2. Institute scope
        if root == "institute":
            if len(tokens) == 1:
                return context.institute, None
            sub_key = ".".join(tokens[1:])
            val = SafePathResolver._lookup_dict(context.institute, tokens[1:])
            if val is not None:
                return val, None
            return None, f"Field '{sub_key}' not found in institute profile."

        # 3. Courses scope
        if root == "courses":
            if len(tokens) == 1:
                return context.courses, None
            if len(tokens) == 2 and tokens[1] == "total_intake":
                total_intake = sum(c.get("intake", 0) for c in context.courses)
                return total_intake, None
            if len(tokens) == 2 and tokens[1] == "count":
                return len(context.courses), None
            val = SafePathResolver._lookup_dict(context.courses, tokens[1:])
            if val is not None:
                return val, None
            return None, f"Field '{tokens[1]}' not found in courses data."

        # 3. Document scope: doc.<DOC_TYPE>.<field>
        if root == "doc":
            if len(tokens) < 3:
                return None, f"Invalid document path syntax '{path}'. Expected 'doc.<DOC_TYPE>.<field>'."
            doc_type = tokens[1].upper()
            field_tokens = tokens[2:]

            matching_docs = context.get_documents_by_type(doc_type)
            if not matching_docs:
                return None, f"No document found for type '{doc_type}'."

            # Inspect latest document
            latest_doc = matching_docs[-1]
            extracted = latest_doc.get("extracted_data") or {}
            val = SafePathResolver._lookup_dict(extracted, field_tokens)
            if val is not None:
                return val, None

            # Fallback to top-level document metadata
            val_meta = SafePathResolver._lookup_dict(latest_doc, field_tokens)
            if val_meta is not None:
                return val_meta, None

            field_name = ".".join(field_tokens)
            return None, f"Field '{field_name}' not found in extracted data for document type '{doc_type}'."

        # Unknown root path
        return None, f"Unknown path scope '{root}'. Must start with 'application', 'institute', 'doc', or 'today'."

    @staticmethod
    def _lookup_dict(data: Any, tokens: list) -> Any:
        curr = data
        for t in tokens:
            if isinstance(curr, dict):
                if t in curr:
                    curr = curr[t]
                else:
                    return None
            elif hasattr(curr, t):
                curr = getattr(curr, t)
            else:
                return None
        return curr


class SafeComparator:
    """
    Evaluates comparison operators with type safety and error containment.
    Operators: ==, !=, >, >=, <, <=, in, not_in, exists, matches, date_before, date_after, within_days
    """

    @staticmethod
    def compare(left_val: Any, operator: str, right_val: Any) -> Tuple[bool, Optional[str]]:
        op = operator.strip().lower()

        # 'exists' operator
        if op == "exists":
            return (left_val is not None and left_val != ""), None

        if left_val is None:
            return False, "Left value is missing / None."

        try:
            if op == "==":
                if isinstance(left_val, str) and isinstance(right_val, str):
                    return left_val.strip().lower() == right_val.strip().lower(), None
                return left_val == right_val, None

            if op == "!=":
                if isinstance(left_val, str) and isinstance(right_val, str):
                    return left_val.strip().lower() != right_val.strip().lower(), None
                return left_val != right_val, None

            # Numeric comparisons
            if op in [">", ">=", "<", "<="]:
                l_num = float(left_val)
                r_num = float(right_val)
                if op == ">":
                    return l_num > r_num, None
                if op == ">=":
                    return l_num >= r_num, None
                if op == "<":
                    return l_num < r_num, None
                if op == "<=":
                    return l_num <= r_num, None

            # Membership
            if op == "in":
                if isinstance(right_val, (list, tuple, set)):
                    return left_val in right_val, None
                return str(left_val) in str(right_val), None

            if op == "not_in":
                if isinstance(right_val, (list, tuple, set)):
                    return left_val not in right_val, None
                return str(left_val) not in str(right_val), None

            # Regex matching with safety limits
            if op == "matches":
                pattern_str = str(right_val)
                if len(pattern_str) > 200:
                    return False, f"Regex pattern length ({len(pattern_str)}) exceeds maximum allowed cap of 200 characters."
                regex = re.compile(pattern_str)
                match = regex.search(str(left_val))
                return match is not None, None

            # Date comparisons
            if op in ["date_before", "date_after", "within_days"]:
                l_date = SafeComparator._parse_date(left_val)
                if not l_date:
                    return False, f"Could not parse left value '{left_val}' as date."

                if op == "within_days":
                    days_target = int(right_val)
                    today = date.today()
                    diff = (l_date - today).days
                    return diff >= days_target, None

                r_date = SafeComparator._parse_date(right_val)
                if not r_date:
                    return False, f"Could not parse right value '{right_val}' as date."

                if op == "date_before":
                    return l_date < r_date, None
                if op == "date_after":
                    return l_date > r_date, None

            return False, f"Unsupported operator '{operator}'."

        except Exception as e:
            return False, f"Comparison error: {str(e)}"

    @staticmethod
    def fuzzy_match(str1: Any, str2: Any, threshold: float = 0.9) -> Tuple[bool, float]:
        s1 = str(str1).lower().strip()
        s2 = str(str2).lower().strip()
        if not s1 or not s2:
            return False, 0.0
        ratio = difflib.SequenceMatcher(None, s1, s2).ratio()
        return ratio >= threshold, ratio

    @staticmethod
    def _parse_date(val: Any) -> Optional[date]:
        if isinstance(val, date):
            return val
        if isinstance(val, datetime):
            return val.date()
        if not isinstance(val, str):
            return None
        val_str = val.strip()
        # ISO YYYY-MM-DD
        try:
            return datetime.fromisoformat(val_str).date()
        except ValueError:
            pass
        # DD-MM-YYYY
        try:
            parts = val_str.split("-")
            if len(parts) == 3 and len(parts[0]) == 2 and len(parts[2]) == 4:
                return date(int(parts[2]), int(parts[1]), int(parts[0]))
        except Exception:
            pass
        return None
