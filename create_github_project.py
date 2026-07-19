import os
import json
import subprocess
import urllib.request
import urllib.error

GRAPHQL_URL = "https://api.github.com/graphql"

def get_git_token():
    """Dynamically queries the Windows Git Credential Manager for the GitHub PAT."""
    try:
        proc = subprocess.run(
            ["git", "credential", "fill"],
            input="url=https://github.com\n",
            text=True,
            capture_output=True,
            check=True
        )
        for line in proc.stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1]
    except Exception as e:
        print(f"[ERROR] Failed to fetch credential from manager: {e}")
    return None

def run_graphql_query(query, variables, token):
    """Helper to post a GraphQL query to the GitHub API."""
    req_data = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=req_data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Aetheria-Project-Manager"
        }
    )
    try:
        with urllib.request.urlopen(req) as res:
            res_data = json.loads(res.read().decode("utf-8"))
            if "errors" in res_data:
                print(f"[GraphQL Errors]: {res_data['errors']}")
            return res_data
    except urllib.error.HTTPError as e:
        print(f"[HTTP Error] Status: {e.code}, Response: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"[Error]: {e}")
    return None

def main():
    token = get_git_token()
    if not token:
        print("[ERROR] No GitHub token found. Please ensure you are logged in to Git.")
        return
        
    print("[INFO] Authenticating and querying User Node ID...")
    
    # 1. Query Viewer User ID
    user_query = """
    query {
      viewer {
        id
        login
      }
    }
    """
    res_user = run_graphql_query(user_query, {}, token)
    if not res_user or "data" not in res_user:
        print("[ERROR] Failed to query user ID. Token might be invalid.")
        return
        
    viewer_id = res_user["data"]["viewer"]["id"]
    login = res_user["data"]["viewer"]["login"]
    print(f"[SUCCESS] Authenticated as user: {login} (ID: {viewer_id})")

    # 2. Create Project V2
    print("[INFO] Creating new Project V2 on GitHub...")
    create_project_mutation = """
    mutation($ownerId: ID!, $title: String!) {
      createProjectV2(input: {
        ownerId: $ownerId,
        title: $title
      }) {
        projectV2 {
          id
          title
          url
        }
      }
    }
    """
    proj_title = "Aetheria Medallion Data Pipeline — Release Sprint"
    res_proj = run_graphql_query(create_project_mutation, {"ownerId": viewer_id, "title": proj_title}, token)
    if not res_proj or "data" not in res_proj or not res_proj["data"]["createProjectV2"]:
        print("[ERROR] Failed to create project. Verify token permissions (project scope required).")
        return
        
    project_id = res_proj["data"]["createProjectV2"]["projectV2"]["id"]
    project_url = res_proj["data"]["createProjectV2"]["projectV2"]["url"]
    print(f"[SUCCESS] Created Project V2: {project_id}")
    print(f"[LINK] Project Board URL: {project_url}")

    # 3. Query Project Fields to locate the "Status" column field and option IDs
    print("[INFO] Fetching default status field and options...")
    fields_query = """
    query($projectId: ID!) {
      node(id: $projectId) {
        ... on ProjectV2 {
          fields(first: 20) {
            nodes {
              ... on ProjectV2FieldCommon {
                id
                name
              }
              ... on ProjectV2SingleSelectField {
                id
                name
                options {
                  id
                  name
                }
              }
            }
          }
        }
      }
    }
    """
    res_fields = run_graphql_query(fields_query, {"projectId": project_id}, token)
    if not res_fields or "data" not in res_fields:
        print("[ERROR] Failed to retrieve project fields.")
        return
        
    status_field_id = None
    options_map = {} # Option Name -> Option ID
    
    for field in res_fields["data"]["node"]["fields"]["nodes"]:
        if field.get("name") == "Status":
            status_field_id = field["id"]
            for opt in field["options"]:
                options_map[opt["name"].upper()] = opt["id"]
            break
            
    if not status_field_id:
        print("[ERROR] Status field not found in project.")
        return
        
    print(f"[INFO] Status Field ID: {status_field_id}")
    print(f"[INFO] Options found: {options_map}")

    # Define Cards to Add
    cards = [
        # Done
        {"title": "Phase 1: Automated Data Acquisition", "body": "Setup headless/headed Playwright crawlers for dynamic bet platform interfaces.", "status": "DONE"},
        {"title": "Phase 2 & 3: Medallion ETL Ingestion", "body": "Implement Bronze raw logging, Silver schema typing/cleaning, and Gold analytics aggregation (SQLite/Iceberg).", "status": "DONE"},
        {"title": "Phase 4: Machine Learning Pipelines", "body": "Fit and register Random Forest (channel classification) and K-Means (channel clustering) models.", "status": "DONE"},
        {"title": "Phase 5 & 6: RAG Semantic Search API", "body": "Index textual database records using Sentence-Transformers & FAISS, and deploy FastAPI endpoints.", "status": "DONE"},
        {"title": "Phase 7: Multi-Agent Actor Orchestrator", "body": "Orchestrate background agents (Validator, Anomaly, Reporter) using asynchronous Actor-Inbox queues.", "status": "DONE"},
        {"title": "UI: Neon Glassmorphism Dashboard", "body": "Design dashboard console with interactive ML sandbox, explainable AI diagnostics, and collateral chatbot guide.", "status": "IN PROGRESS"},
        # Todo
        {"title": "Model Boundary Auditing", "body": "Review Isolation Forest contamination rate boundaries to optimize false-positive anomaly logs.", "status": "TODO"},
        {"title": "Containerize Big Data Services", "body": "Integrate Kafka, MinIO, Nessie, and Spark inside a unified docker-compose.yml for multi-node setups.", "status": "TODO"}
    ]

    # 4. Add Draft Issues and assign to status option
    print("[INFO] Adding draft issues and assigning to Kanban columns...")
    
    add_draft_mutation = """
    mutation($projectId: ID!, $title: String!, $body: String!) {
      addProjectV2DraftIssue(input: {
        projectId: $projectId,
        title: $title,
        body: $body
      }) {
        projectItem {
          id
        }
      }
    }
    """
    
    update_field_mutation = """
    mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
      updateProjectV2ItemFieldValue(input: {
        projectId: $projectId,
        itemId: $itemId,
        fieldId: $fieldId,
        value: {
          singleSelectOptionId: $optionId
        }
      }) {
        projectV2Item {
          id
        }
      }
    }
    """
    
    for card in cards:
        print(f"  - Adding card: {card['title']}...")
        
        # Add Draft Issue
        res_draft = run_graphql_query(add_draft_mutation, {
            "projectId": project_id,
            "title": card["title"],
            "body": card["body"]
        }, token)
        
        if not res_draft or "data" not in res_draft or not res_draft["data"]["addProjectV2DraftIssue"]:
            print(f"    [WARNING] Failed to add draft issue for: {card['title']}")
            continue
            
        item_id = res_draft["data"]["addProjectV2DraftIssue"]["projectItem"]["id"]
        
        # Get target option ID
        status_key = card["status"]
        option_id = options_map.get(status_key)
        
        if option_id:
            # Set field value
            run_graphql_query(update_field_mutation, {
                "projectId": project_id,
                "itemId": item_id,
                "fieldId": status_field_id,
                "optionId": option_id
            }, token)
            print(f"    [OK] Placed in column: {status_key}")
        else:
            print(f"    [WARNING] Status mapping not found for: {status_key}")

    print("\n=======================================================")
    print("[SUCCESS] All Kanban project board tasks initialized live!")
    print(f"[LINK] View your Project Board here: {project_url}")
    print("=======================================================")

if __name__ == "__main__":
    main()
