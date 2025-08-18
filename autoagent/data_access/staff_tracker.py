import pandas as pd
import os

# Ścieżka do pliku CSV (upewnij się, że jest poprawna w docelowym środowisku)
STAFF_TRACKER_PATH = os.path.join(os.path.dirname(__file__), '../data/Staff Tracker.csv')

class StaffTracker:
    def __init__(self, csv_path=STAFF_TRACKER_PATH):
        self.df = pd.read_csv(csv_path)
        self.df.columns = [col.strip() for col in self.df.columns]  # usuwa spacje z nagłówków

    def find_employee_by_name(self, name):
        # Wyszukuje pracownika po nazwie (dokładne dopasowanie)
        matches = self.df[self.df['Name'].str.lower() == name.lower()]
        return matches.to_dict(orient='records') if not matches.empty else None

    def get_employee_detail(self, name, field):
        employee = self.find_employee_by_name(name)
        if not employee:
            return f"Employee '{name}' not found."

        value = employee[0].get(field)
        return value if pd.notna(value) else f"'{field}' is missing for {name}."

    def list_all_employees(self):
        return self.df['Name'].dropna().unique().tolist()

    def available_fields(self):
        return self.df.columns.tolist()

# Przykład użycia (do testów lokalnych)
if __name__ == "__main__":
    tracker = StaffTracker()
    print(tracker.get_employee_detail("John Smith", "Contact Number"))
    print(tracker.list_all_employees())
    print(tracker.available_fields())


COLUMN_ALIASES = {
    "PSA Licence expiry date": "PSA Licence exp. DD/MM/YYYY",
    "PSA Licence exp": "PSA Licence exp. DD/MM/YYYY",
    "PSA Licence expiry": "PSA Licence exp. DD/MM/YYYY",
    "PSA Licence expiration": "PSA Licence exp. DD/MM/YYYY",
}
