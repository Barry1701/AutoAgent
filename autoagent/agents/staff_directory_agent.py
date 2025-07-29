import pandas as pd
import re

try:
    from autoagent.utils.chatgpt import ask_openai
except ImportError:
    def ask_openai(prompt: str, model="gpt-4") -> str:
        return f"(Mock response - OpenAI not configured)\nPrompt: {prompt}"


class StaffDirectory:
    def __init__(self, filepath='autoagent/data/Staff Tracker.csv'):
        self.df = pd.read_csv(filepath).fillna('')

    def normalize_name(self, name):
        # Remove anything in parentheses and lowercase
        return re.sub(r'\s*\([^)]*\)', '', name).strip().lower()

    def find_by_name(self, name):
        name = name.lower().strip()
        self.df['Cleaned Name'] = self.df['Name'].apply(self.normalize_name)
        results = self.df[self.df['Cleaned Name'] == name]
        return results.to_dict(orient='records')[0] if not results.empty else None

    def extract_name_from_query(self, query):
        # Looks for 'for Name' at the end of the question
        match = re.search(r'for (.+?)[\?\n]*$', query, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None


def staff_directory_agent(query: str, context: dict = {}) -> str:
    directory = StaffDirectory()
    name = directory.extract_name_from_query(query)

    if not name:
        return "❌ Could not extract employee name from the query."

    record = directory.find_by_name(name)
    if not record:
        return f"No entry found for {name}."

    prompt = (
        f"You are a helpful assistant. Based on the following employee data, "
        f"answer the user's question.\n\n"
        f"Employee data:\n{record}\n\n"
        f"User's question: {query}\n\n"
        f"Answer in one sentence. If the answer cannot be found, say so clearly."
    )

    return ask_openai(prompt, model="gpt-4")
