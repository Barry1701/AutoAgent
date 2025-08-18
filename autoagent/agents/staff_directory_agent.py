# autoagent/agents/staff_directory_agent.py
import os
import re
import pandas as pd

# Optional LLM helper (not required for this agent to work)
try:
    from autoagent.utils.chatgpt import ask_openai  # noqa: F401
except Exception:
    def ask_openai(*args, **kwargs):  # fallback stub
        return None


CSV_PATH = os.path.join("autoagent", "data", "Staff Tracker.csv")


# Map natural-language aliases -> canonical column names
# You can add more aliases freely.
COLUMN_ALIASES_SINGLE = {
    # PSA
    "psa licence": "PSA Licence",
    "psa": "PSA Licence",  # will be handled specially to also include expiry
    "psa number": "PSA Licence",
    "psa no": "PSA Licence",
    "psa id": "PSA Licence",
    "psa license": "PSA Licence",

    # PSA expiry
    "psa licence expiry date": "PSA Licence exp. DD/MM/YYYY",
    "psa licence expiry": "PSA Licence exp. DD/MM/YYYY",
    "psa expiry": "PSA Licence exp. DD/MM/YYYY",
    "expiry": "PSA Licence exp. DD/MM/YYYY",
    "expiration": "PSA Licence exp. DD/MM/YYYY",
    "psa license expiry": "PSA Licence exp. DD/MM/YYYY",

    # Other examples already present in sheet
    "contact number": "Contact Number",
    "emergency contact": "Contact Number in case of Emergency",
    "first aid": "First Aid Certified",
    "first aid expiry": "Date of first Aid expire",
    "badge": "Received Access Badge",
    "radio earpiece": "Radio Earpiece Received",
    "safepass": "Safepass",
    "ert training": "Emergency Response Team (ERT) Training",
    "manual handling": "Manual Handling Training",
    "navy coat": "Navy Blue winter Coat Received 2024",
    "bgu sign off": "BGU Sign Off",
    "l-dap": "L-Dap",
    "ldap": "L-Dap",
    "pin": "Employee PIN (0****)",
    "employee pin": "Employee PIN (0****)",
}

# Aliases that imply returning MULTIPLE fields at once.
# Here "psa" => both number + expiry.
COLUMN_ALIAS_GROUPS = {
    "psa": ["PSA Licence", "PSA Licence exp. DD/MM/YYYY"],
    "psa licence": ["PSA Licence", "PSA Licence exp. DD/MM/YYYY"],
    "psa license": ["PSA Licence", "PSA Licence exp. DD/MM/YYYY"],
}


def _clean_name(name: str) -> str:
    """Normalize name by removing parentheses content and extra spaces, lowercase."""
    if not isinstance(name, str):
        return ""
    name = re.sub(r"\s*\([^)]*\)", "", name)
    return re.sub(r"\s+", " ", name).strip().lower()


class StaffDirectory:
    def __init__(self, filepath: str = CSV_PATH):
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"CSV not found at: {os.path.abspath(filepath)}")
        self.df = pd.read_csv(filepath).fillna("")
        # Normalize a helper column for matching by name
        self.df["__clean_name__"] = self.df["Name"].apply(_clean_name)

        # Build a lowercase->real column mapping for robust lookup
        self._col_lc_map = {c.strip().lower(): c for c in self.df.columns}

    # ---------- Name matching ----------

    def find_best_name_in_text(self, text: str) -> str | None:
        """
        Try to find the best matching name from the CSV inside the query text.
        Chooses the longest clean name that is a substring of the query.
        """
        t = text.lower()
        best = None
        best_len = 0
        for clean_name in self.df["__clean_name__"]:
            if not clean_name:
                continue
            if clean_name in t and len(clean_name) > best_len:
                best = clean_name
                best_len = len(clean_name)
        return best

    def get_record_by_clean_name(self, clean_name: str) -> dict | None:
        matches = self.df[self.df["__clean_name__"] == clean_name]
        if matches.empty:
            return None
        return matches.iloc[0].to_dict()

    # ---------- Field (column) matching ----------

    def _columns_present(self, wanted: list[str]) -> list[str]:
        """Return only those of 'wanted' that actually exist (case-insensitive) in the CSV."""
        present = []
        for w in wanted:
            real = self._col_lc_map.get(w.strip().lower())
            if real:
                present.append(real)
        return present

    def infer_fields_from_text(self, text: str) -> list[str]:
        """
        Parse the user query for known field aliases.
        If 'psa' appears (and no specific expiry-only request), return both number + expiry.
        """
        t = text.lower()

        # If explicit expiry words appear, prefer the expiry column
        explicit_expiry_hits = [
            k for k in COLUMN_ALIASES_SINGLE.keys()
            if "expiry" in k or "expiration" in k
        ]
        for k in explicit_expiry_hits:
            if k in t:
                return self._columns_present([COLUMN_ALIASES_SINGLE[k]])

        # If 'psa' appears (generic), return both number + expiry
        for alias_group in COLUMN_ALIAS_GROUPS.keys():
            if alias_group in t:
                wanted = COLUMN_ALIAS_GROUPS[alias_group]
                return self._columns_present(wanted)

        # Otherwise try to match any single alias in text
        hits = []
        for k, v in COLUMN_ALIASES_SINGLE.items():
            if k in t:
                hits.append(v)
        if hits:
            return self._columns_present(hits)

        # As a last resort, scan for columns with the word 'expiry'
        expiry_like = [c for c in self.df.columns if "exp" in c.lower() or "expiry" in c.lower()]
        if expiry_like:
            return self._columns_present(expiry_like[:1])  # pick one most likely

        return []

    # ---------- Value retrieval ----------

    def get_values(self, record: dict, fields: list[str]) -> list[tuple[str, str]]:
        """
        For each requested field, return (display_name, value or 'N/A').
        """
        out = []
        for f in fields:
            val = record.get(f, "")
            if isinstance(val, str):
                val = val.strip()
            out.append((f, val if val else "N/A"))
        return out


def staff_directory_agent(query: str, context: dict = {}) -> str:
    """
    Examples:
      - "psa Tomasz Greplowski"
      - "What is the PSA Licence expiry date for Bartosz Stanczuk?"
      - "Give me contact number for Adam Quirke"
    """
    directory = StaffDirectory()

    # 1) Find best matching name inside the query
    clean_name = directory.find_best_name_in_text(query)
    if not clean_name:
        return (
            "I couldn't find a matching employee name in your question. "
            "Try e.g. 'psa John Smith' or 'What is the PSA Licence expiry date for Jane Doe?'."
        )

    record = directory.get_record_by_clean_name(clean_name)
    if not record:
        return "No entry found for that employee."

    display_name = record.get("Name", clean_name.title())

    # 2) Determine which fields you want
    fields = directory.infer_fields_from_text(query)

    # If still empty but the question includes 'psa' word, return both by default
    if not fields and "psa" in query.lower():
        fields = directory._columns_present(["PSA Licence", "PSA Licence exp. DD/MM/YYYY"])

    if not fields:
        # suggest a few common fields
        suggestions = [
            "PSA Licence", "PSA Licence exp. DD/MM/YYYY",
            "Contact Number", "Contact Number in case of Emergency",
            "Date of first Aid expire"
        ]
        return (
            "ℹ️ Tell me which field you want. Examples: "
            + "; ".join(f"'{s}'" for s in suggestions)
        )

    # 3) Fetch and format
    pairs = directory.get_values(record, fields)

    # If the user asked something like only expiry, keep it one-liner
    if len(pairs) == 1:
        label, value = pairs[0]
        return f"{label} for {display_name}: {value}"

    # Otherwise give compact multiline
    lines = [f"{display_name}:"]
    for label, value in pairs:
        lines.append(f"- {label}: {value}")
    return "\n".join(lines)
