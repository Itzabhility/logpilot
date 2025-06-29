import os
from datetime import datetime
from notion_client import Client
from dotenv import load_dotenv
from openai import OpenAI
from rapidfuzz import fuzz

# Load environment variables from .env
load_dotenv()
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Get your credentials
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Set up Notion client
notion = Client(auth=NOTION_TOKEN)

#Automatically create the parent task if it doesn’t exist
def create_new_parent_task(title):
    now = datetime.now()
    new_page = notion.pages.create(
        parent={"database_id": DATABASE_ID},
        properties={
            "Name": {"title": [{"text": {"content": title}}]},
            "Status": {"select": {"name": "In progress"}},
            "Time": {"date": {"start": now.isoformat()}},
            "Description": {"rich_text": [{"text": {"content": f"Auto-created parent task: {title}"}}]},
            "Tools": {"multi_select": []},
            "Goal": {"rich_text": [{"text": {"content": "Parent task auto-created for grouping related logs."}}]},
            "Log Type": {"select": {"name": "Parent"}},
            "Category": {"select": {"name": "Work"}},
        }
    )
    return new_page["id"]

def get_page_id_by_title(title):
    results = notion.databases.query(
        database_id=DATABASE_ID,
        filter={"property": "Name", "title": {"equals": title}}
    )
    pages = results.get("results", [])
    return pages[0]["id"] if pages else None


def find_existing_task(task_name):
    for keyword, canonical_title in CANONICAL_TOPICS.items():
        if keyword.lower() in task_name.lower():
            print(f"🎯 Matched keyword '{keyword}' → Canonical task: '{canonical_title}'")
            parent_id = get_page_id_by_title(canonical_title)
            if not parent_id:
                print(f"📄 No existing page found for '{canonical_title}', creating new one.")
                parent_id = create_new_parent_task(canonical_title)
            return parent_id
    results = notion.databases.query(
        **{
            "database_id": DATABASE_ID,
            "filter": {
                "property": "Name",
                "title": {
                    "contains": task_name
                }
            }
        }
    )
    # results = notion.databases.query(database_id=DATABASE_ID)
    pages = results.get("results", [])
    best_match_id = None
    highest_score = 0

    for page in pages:
        title_property = page["properties"].get("Name", {})
        title_text = title_property.get("title", [])
        if title_text:
            existing_title = title_text[0]["text"]["content"]
            score = fuzz.ratio(task_name.lower(), existing_title.lower())
            print(f"🧪 Compared with: {existing_title} → Score: {score}")
            if score > highest_score and score >= 65:  # threshold
                highest_score = score
                best_match_id = page["id"]
    if best_match_id:
        print(f"🔗 Best match for parent task: {best_match_id} with score {highest_score}")
    else:
        print("❌ No parent task match found.")
        # If no match found, auto-create parent task
        print(f"🆕 Creating new parent task for: '{task_name}'")
        best_match_id = create_new_parent_task(task_name)
        # Dynamically store the new parent topic for improved future matching
        CANONICAL_TOPICS[task_name.lower()] = task_name
    return best_match_id


# Logging function
def log_to_notion(task, status, description, tools, goal, log_type, category="Work", parent_topic=None):
    parent_task_id = find_existing_task(parent_topic or task)
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M")

    properties = {
        "Name": {"title": [{"text": {"content": task}}]},
        "Status": {"select": {"name": status}},
        "Time": {"date": {"start": now.isoformat()}},
        "Description": {"rich_text": [{"text": {"content": description}}]},
        "Tools": {"multi_select": [{"name": t.strip()} for t in tools.split(",")]},
        "Goal": {"rich_text": [{"text": {"content": goal}}]},
        "Log Type": {"select": {"name": log_type}},
        "Category": {"select": {"name": category}},
    }

    if parent_task_id:
        properties["Parent Task"] = {"relation": [{"id": parent_task_id}]}

    notion.pages.create(
        parent={"database_id": DATABASE_ID},
        properties=properties
    )

    print("✅ Log sent to Notion.")

    os.makedirs("logs", exist_ok=True)
    with open(f"logs/{now.strftime('%Y-%m-%d')}.md", "a") as f:
        f.write(f"""
### [{timestamp}] {category} Log
- **Task**: {task}
- **Status**: {status}
- **What was done**: {description}
- **Goal**: {goal}
- **Tools used**: {tools}
- **Log type**: {log_type}
- **Category**: {category}
\n""")
    print("📝 Log saved locally.")

clarification_count = 0
def parse_and_log(raw_message):
    global clarification_count
    MAX_CLARIFICATIONS = 2
    response = openai_client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an assistant that converts casual log messages into structured task logs for Notion.\n"
                    "Return a valid **Python dictionary** with the following keys:\n"
                    "- task (str): Clear task title\n"
                    "- status (str): 'In progress', 'Completed', or 'Pending'\n"
                    "- description (str): 1–2 sentence explanation of what was done\n"
                    "- tools (str): Comma-separated tools used (or leave as an empty string if none)\n"
                    "- goal (str): Short outcome or purpose\n"
                    "- log_type (str): Type of log, e.g., 'Task log'\n"
                    "- category (str): Must be either 'Work' or 'Personal'\n"
                    "- parent_topic (str): A concise and reusable topic this task belongs to (2–4 words)\n\n"
                
                    "If the input is vague or unclear (e.g., 'fixed a few things', 'worked on stuff'), DO NOT guess.\n"
                    "Instead, return exactly this:\n"
                    "{'clarify': 'Could you briefly describe the broader project or context this task is part of?'}\n\n"
                
                    "NEVER use vague or generic parent topics like 'Task Management' or 'Improvements'.\n"
                    "If you are unsure of the context, ask for clarification — do not proceed until confident.\n"
                    "Always respond with a valid Python dictionary. Do not include explanations or markdown."
                )
            },
            {"role": "user", "content": f"Convert this log into structured JSON: {raw_message}"}
        ]
    )

    try:
        content = response.choices[0].message.content
        print("🔍 GPT Response:\n", content)

        structured = eval(content)  # use json.loads if returned as JSON string

        if "clarify" in structured:
            clarification_count += 1
            if clarification_count > MAX_CLARIFICATIONS:
                print("🚫 Too many clarification attempts. GPT is unsure.")
                return
            print("🤔 GPT requested clarification:\n", structured["clarify"])
            context_input = input("📥 Your clarification: ")
            return parse_and_log(f"{raw_message} | Context: {context_input}")

        required_keys = ["task", "status", "description", "tools", "goal", "log_type"]
        if not all(key in structured for key in required_keys):
            print("⚠️ GPT response is missing required keys. Please try rewording your input.")
            return
        parent_topic = structured.get("parent_topic", structured["task"])

        log_to_notion(
            task=structured["task"],
            status=structured["status"],
            description=structured["description"],
            tools=structured["tools"],
            goal=structured["goal"],
            log_type=structured["log_type"],
            category=structured.get("category", "Work"),
            parent_topic=parent_topic
        )
    except Exception as e:
        print("❌ Error parsing GPT response:", str(e))

# Example usage
if __name__ == "__main__":
    user_input = input("Log something casually: ")
    parse_and_log(user_input)