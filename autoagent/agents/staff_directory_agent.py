import pandas as pd

class StaffDirectory:
    def __init__(self, filepath='data/Staff Tracker.csv'):
        self.df = pd.read_csv(filepath).fillna('')

    def find_by_name(self, name):
        results = self.df[self.df['Name'].str.lower() == name.lower()]
        return results.to_dict(orient='records') if not results.empty else None

    def search(self, query):
        name = query.strip()
        result = self.find_by_name(name)
        if result:
            return result[0]
        return f"No entry found for {name}."
