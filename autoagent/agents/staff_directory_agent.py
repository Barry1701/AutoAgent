# autoagent/agents/staff_directory_agent.py
import os
import re
import time
from functools import lru_cache
from typing import List, Tuple, Dict, Optional

import pandas as pd

# (opcjonalne) wsparcie LLM – nie jest wymagane do działania agenta
try:
    from autoagent.utils.chatgpt import ask_openai  # noqa: F401
except Exception:
    def ask_openai(*args, **kwargs):
        return None


CSV_PATH = os.path.join("autoagent", "data", "Staff Tracker.csv")

# --- Alias mapping (przyjazne frazy -> nazwy kolumn w pliku) ---

# Pojedyncze pola
COLUMN_ALIASES_SINGLE: Dict[str, str] = {
    # PSA (nr)
    "psa licence": "PSA Licence",
    "psa license": "PSA Licence",
    "psa": "PSA Licence",            # specjalnie obsłużymy grupowo
    "psa number": "PSA Licence",
    "psa no": "PSA Licence",
    "psa id": "PSA Licence",

    # PSA expiry
    "psa licence expiry date": "PSA Licence exp. DD/MM/YYYY",
    "psa licence expiry": "PSA Licence exp. DD/MM/YYYY",
    "psa license expiry": "PSA Licence exp. DD/MM/YYYY",
    "psa expiry": "PSA Licence exp. DD/MM/YYYY",
    "expiry": "PSA Licence exp. DD/MM/YYYY",
    "expiration": "PSA Licence exp. DD/MM/YYYY",

    # Inne częste pola
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

# Alias, który sugeruje zwrot wielu pól na raz
COLUMN_ALIAS_GROUPS: Dict[str, List[str]] = {
    "psa": ["PSA Licence", "PSA Licence exp. DD/MM/YYYY"],
    "psa licence": ["PSA Licence", "PSA Licence exp. DD/MM/YYYY"],
    "psa license": ["PSA Licence", "PSA Licence exp. DD/MM/YYYY"],
}

# TTL (sekundy) dla cache odczytu CSV
CSV_TTL_SECONDS = 300


def _clean_name(name: str) -> str:
    """Usuwa zawartość w nawiasach, normalizuje spacje i robi lowercase."""
    if not isinstance(name, str):
        return ""
    name = re.sub(r"\s*\([^)]*\)", "", name)
    return re.sub(r"\s+", " ", name).strip().lower()


def _name_tokens(clean_name: str) -> List[str]:
    """Tokenizuje czyste imię i nazwisko na pojedyncze słowa."""
    return [t for t in re.split(r"[^\w]+", clean_name) if t]


# --- Mechanizm cache z TTL oparty o lru_cache + bucket czasu ---

@lru_cache(maxsize=128)
def _load_df_cached(filepath: str, time_bucket: int) -> pd.DataFrame:
    """Wczytuje CSV, wynik cache’owany przez bucket czasu (TTL)."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV not found at: {os.path.abspath(filepath)}")
    return pd.read_csv(filepath).fillna("")


def _load_df_ttl(filepath: str, ttl_seconds: int) -> pd.DataFrame:
    """Zwraca DataFrame z TTL – nowy bucket co ttl_seconds."""
    bucket = int(time.time() // ttl_seconds)
    return _load_df_cached(filepath, bucket)


class StaffDirectory:
    def __init__(self, filepath: str = CSV_PATH):
        self.filepath = filepath
        self.df = _load_df_ttl(self.filepath, CSV_TTL_SECONDS)

        if "Name" not in self.df.columns:
            raise ValueError("CSV must contain a 'Name' column.")

        # pomocnicza kolumna do dopasowania po imieniu/nazwisku
        self.df["__clean_name__"] = self.df["Name"].apply(_clean_name)

        # mapa lowercase -> oryginalna nazwa kolumny
        self._col_lc_map = {c.strip().lower(): c for c in self.df.columns}

    @staticmethod
    def clear_cache():
        """Czyści cache CSV (używane przy refresh=1)."""
        _load_df_cached.cache_clear()

    # ---------- Name matching ----------

    def find_best_name_in_text(self, text: str) -> Optional[str]:
        """
        Najpierw próbuje znaleźć pełny clean_name jako podciąg zapytania.
        Jeśli się nie uda, stosuje dopasowanie częściowe po tokenach imienia/nazwiska.
        """
        t = text.lower()
        # 1) pełny podciąg
        best = None
        best_len = 0
        for clean_name in self.df["__clean_name__"]:
            if not clean_name:
                continue
            if clean_name in t and len(clean_name) > best_len:
                best = clean_name
                best_len = len(clean_name)
        if best:
            return best

        # 2) częściowe dopasowanie po tokenach (np. samo "bartosz" albo "greplowski")
        token_hits: List[Tuple[str, int, int]] = []  # (clean_name, matched_tokens, total_tokens)
        q_tokens = set(_name_tokens(t))
        for clean_name in self.df["__clean_name__"]:
            tokens = _name_tokens(clean_name)
            if not tokens:
                continue
            matched = sum(1 for tok in tokens if tok in q_tokens)
            if matched > 0:
                token_hits.append((clean_name, matched, len(tokens)))

        if not token_hits:
            return None

        # sortuj: najwiecej trafionych tokenów, potem dłuższe nazwisko (więcej tokenów)
        token_hits.sort(key=lambda x: (x[1], x[2]), reverse=True)

        # jeżeli top jest jednoznaczny (wyraźnie wygrywa liczbą trafień), zwróć go
        top = token_hits[0]
        # sprawdź czy drugi nie ma tyle samo trafień
        if len(token_hits) == 1 or top[1] > token_hits[1][1]:
            return top[0]

        # w przeciwnym razie zwróć None (pozwolimy warstwie wyżej wyświetlić listę kandydatów)
        return None

    def list_name_candidates(self, text: str, limit: int = 5) -> List[str]:
        """
        Zwraca listę potencjalnych dopasowań po tokenach (do podpowiedzi).
        """
        t = text.lower()
        q_tokens = set(_name_tokens(t))
        scored: List[Tuple[str, int, int]] = []
        for clean_name, display in zip(self.df["__clean_name__"], self.df["Name"]):
            tokens = _name_tokens(clean_name)
            if not tokens:
                continue
            matched = sum(1 for tok in tokens if tok in q_tokens)
            if matched > 0:
                scored.append((display, matched, len(tokens)))
        scored.sort(key=lambda x: (x[1], x[2]), reverse=True)
        return [s[0] for s in scored[:limit]]

    def get_record_by_clean_name(self, clean_name: str) -> Optional[Dict]:
        matches = self.df[self.df["__clean_name__"] == clean_name]
        if matches.empty:
            return None
        return matches.iloc[0].to_dict()

    # ---------- Field (column) matching ----------

    def _columns_present(self, wanted: List[str]) -> List[str]:
        """Zwraca listę kolumn istniejących w CSV (case-insensitive)."""
        present = []
        for w in wanted:
            real = self._col_lc_map.get(w.strip().lower())
            if real:
                present.append(real)
        return present

    def infer_fields_from_text(self, text: str) -> List[str]:
        """
        Analiza pytania i dopasowanie kolumn:
        - jeśli pada słowo odpowiadające wygaśnięciu (expiry), wybierz tylko expiry
        - jeśli 'psa' (ogólnie), zwróć nr + expiry
        - w przeciwnym razie dopasuj aliasy pojedyncze
        - fallback: jakiekolwiek kolumny z 'exp'/'expiry'
        """
        t = text.lower()

        # 1) Konkretnie "expiry" / "expiration"
        explicit_expiry_hits = [
            k for k in COLUMN_ALIASES_SINGLE if ("expiry" in k or "expiration" in k)
        ]
        for k in explicit_expiry_hits:
            if k in t:
                return self._columns_present([COLUMN_ALIASES_SINGLE[k]])

        # 2) Grupa 'psa' => nr + expiry
        for alias_group in COLUMN_ALIAS_GROUPS:
            if alias_group in t:
                return self._columns_present(COLUMN_ALIAS_GROUPS[alias_group])

        # 3) Pojedyncze aliasy
        hits = []
        for k, v in COLUMN_ALIASES_SINGLE.items():
            if k in t:
                hits.append(v)
        if hits:
            return self._columns_present(hits)

        # 4) Ostatnia próba – szukaj kolumn z "exp"/"expiry"
        expiry_like = [c for c in self.df.columns if ("exp" in c.lower() or "expiry" in c.lower())]
        if expiry_like:
            return self._columns_present(expiry_like[:1])

        return []

    # ---------- Value retrieval ----------

    def get_values(self, record: Dict, fields: List[str]) -> List[Tuple[str, str]]:
        """Dla każdego pola zwraca (etykieta, wartość/N/A)."""
        out: List[Tuple[str, str]] = []
        for f in fields:
            val = record.get(f, "")
            if isinstance(val, str):
                val = val.strip()
            out.append((f, val if val else "N/A"))
        return out


def staff_directory_agent(query: str, context: dict = {}) -> str:
    """
    Przykłady:
      - "psa Bartosz"
      - "psa Tomasz Greplowski"
      - "What is the PSA Licence expiry date for Bartosz Stanczuk?"
      - "Give me contact number for Adam Quirke"
      - "emergency contact Adam Quirke"
    """
    # Obsługa refresh=1 (np. po zmianie CSV)
    if str(context.get("refresh", "0")) == "1":
        StaffDirectory.clear_cache()

    directory = StaffDirectory()

    # 1) Dopasuj pracownika po tekście (pełne lub częściowe)
    clean_name = directory.find_best_name_in_text(query)
    if not clean_name:
        # spróbuj zasugerować kandydatów
        candidates = directory.list_name_candidates(query, limit=5)
        if candidates:
            return (
                "I found multiple or partial matches. Please specify one of:\n"
                + "\n".join(f"- {c}" for c in candidates)
            )
        return (
            "I couldn't find a matching employee name in your question. "
            "Try e.g. 'psa John Smith' or 'What is the PSA Licence expiry date for Jane Doe?'."
        )

    record = directory.get_record_by_clean_name(clean_name)
    if not record:
        return "No entry found for that employee."

    display_name = record.get("Name", clean_name.title())

    # 2) Jakie pola?
    fields = directory.infer_fields_from_text(query)

    # Jeśli pusta lista, ale jest słowo 'psa' – zwróć nr + expiry
    if not fields and "psa" in query.lower():
        fields = directory._columns_present(["PSA Licence", "PSA Licence exp. DD/MM/YYYY"])

    if not fields:
        suggestions = [
            "PSA Licence", "PSA Licence exp. DD/MM/YYYY",
            "Contact Number", "Contact Number in case of Emergency",
            "Date of first Aid expire",
        ]
        return "ℹ️ Tell me which field you want. Examples: " + "; ".join(f"'{s}'" for s in suggestions)

    # 3) Pobierz i sformatuj wynik
    pairs = directory.get_values(record, fields)

    if len(pairs) == 1:
        label, value = pairs[0]
        return f"{label} for {display_name}: {value}"

    lines = [f"{display_name}:"]
    for label, value in pairs:
        lines.append(f"- {label}: {value}")
    return "\n".join(lines)
