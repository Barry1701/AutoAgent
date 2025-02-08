from pandas import read_csv
import json
from rich import print

df = read_csv("tool_docs.csv")

rapidapi_tools = df[df['Platform'] == 'RapidAPI']['Tool_Name'].unique()
print("[bold blue]Current RapidAPI tools:[/bold blue]")
print(json.dumps(rapidapi_tools.tolist(), indent=4))
print("[bold red][IMPORTANT][/bold red] [bold yellow]If you want to use these tools, you should go to RapidAPI and subscribe to them. More convenient tool platforms such as Composio are under development.[/bold yellow]")

your_api_key = input("Please input your RapidAPI API key:")

for column in df.columns:
    if df[column].dtype == 'object':
        df[column] = df[column].str.replace('YOUR_RAPID_API_KEY', your_api_key)

df.to_csv('tool_docs.csv', index=False)

print("[bold green]Done![/bold green]")