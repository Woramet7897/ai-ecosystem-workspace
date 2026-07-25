import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from core.config import settings
from label_studio_sdk.client import LabelStudio

def test_label_studio():
    print("=== Connecting to Label Studio API ===")
    print(f"URL: {settings.label_studio_url}")
    print(f"API Key: {settings.label_studio_api_key[:5]}...{settings.label_studio_api_key[-5:]}")
    
    ls = LabelStudio(base_url=settings.label_studio_url, api_key=settings.label_studio_api_key)
    
    try:
        print("\n--- Step 1: Listing All Projects ---")
        projects = list(ls.projects.list())
        print(f"Found {len(projects)} projects.")
        
        # If no projects, just create one to show we can
        if len(projects) == 0:
            print("No projects found, creating one...")
            ls.projects.create(title="New Project #1")
            ls.projects.create(title="Example Sentiment")
            ls.projects.create(title="New Project #3")
            projects = list(ls.projects.list())
            print(f"Created {len(projects)} projects.")

        for p in projects:
            print(f"- [Project ID: {p.id}] Title: '{p.title}' | Tasks Count: {p.task_number}")
            
        if projects:
            # Let's pick a project
            for p in projects:
                if "Example" in p.title or "Sentiment" in p.title:
                    target_project = p
                    break
            else:
                target_project = projects[0]
                
            p_id = target_project.id
            print(f"\n--- Step 2: Listing Tasks in Project ID {p_id} ('{target_project.title}') ---")
            print(f"Fetching tasks for project ID: {p_id}...")
            
            tasks = list(ls.tasks.list(project=p_id))
            if len(tasks) == 0:
                print("No tasks found, creating mock tasks...")
                ls.tasks.create(project=p_id, data={"$undefined$": "/data/upload/3/e9a6d3b3-03_00.jpg"})
                ls.tasks.create(project=p_id, data={"$undefined$": "/data/upload/3/b5a61b59-ctto.jpg"})
                tasks = list(ls.tasks.list(project=p_id))

            print(f"Found {len(tasks)} tasks in this project.")
            for task in tasks:
                print(f"  Task #{task.id} [Task ID: {task.id}] -> Data: {task.data}")
                
    except Exception as e:
        print(f"Failed to connect or fetch data: {e}")

if __name__ == "__main__":
    test_label_studio()
