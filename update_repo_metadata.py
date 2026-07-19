import json
import subprocess
import urllib.request
import urllib.error

REPO_OWNER = "957908"
REPO_NAME = "Multi-Agent-AI-Data-Lakehouse-Platform-Betting-Site-Data-Intelligence"
BASE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"

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

def send_rest_request(url, method, data, token, custom_headers=None):
    """Sends a REST API request to the GitHub API."""
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Aetheria-Project-Manager"
    }
    if custom_headers:
        headers.update(custom_headers)
        
    req_data = json.dumps(data).encode("utf-8") if data else None
    req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"[HTTP Error {e.code}]: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"[Error]: {e}")
    return None

def main():
    token = get_git_token()
    if not token:
        print("[ERROR] No GitHub token found.")
        return

    print("[INFO] Updating repository description and website metadata...")
    
    # 1. Update Description & Website Homepage URL
    meta_payload = {
        "description": "Multi-Agent AI Data Lakehouse Platform: Medallion Architecture ETL processing (Spark/SQLite), Isolation Forest anomaly detection, FAISS vector RAG querying, and asynchronous Actor orchestrators.",
        "homepage": f"https://github.com/{REPO_OWNER}/{REPO_NAME}",
        "has_issues": True,
        "has_projects": True,
        "has_wiki": True
    }
    
    res_meta = send_rest_request(BASE_URL, "PATCH", meta_payload, token)
    if res_meta:
        print("[SUCCESS] Repository metadata updated successfully.")
        print(f"  - Description: {res_meta['description']}")
    else:
        print("[WARNING] Metadata update failed.")

    # 2. Update Topics (Tags)
    print("[INFO] Updating repository topics...")
    topics_url = f"{BASE_URL}/topics"
    topics_payload = {
        "names": [
            "big-data",
            "pyspark",
            "apache-kafka",
            "lakehouse",
            "machine-learning",
            "fastapi",
            "faiss",
            "rag",
            "multi-agent-systems",
            "python",
            "computer-science",
            "cyber-security",
            "blockchain",
            "data-analytics"
        ]
    }
    # Accept header requires mercury-preview for topics API (standard REST v3)
    res_topics = send_rest_request(
        topics_url,
        "PUT",
        topics_payload,
        token,
        custom_headers={"Accept": "application/vnd.github.mercury-preview+json"}
    )
    
    if res_topics:
        print("[SUCCESS] Repository topics set successfully.")
        print(f"  - Topics: {res_topics['names']}")
    else:
        print("[WARNING] Topics update failed.")

if __name__ == "__main__":
    main()
