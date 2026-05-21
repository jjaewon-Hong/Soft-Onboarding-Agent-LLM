import requests
from llm_engine import categorize_files_with_gemini

def analyze_single_repository(username, token, repo_name):
    """
    레포지토리의 진짜 기본 브랜치(master/main)를 자동 감지하여 4-Way View로 분류합니다.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    categorized_files = {
        "Interface": [],
        "Functional": [],
        "Data": [],
        "Process": []
    }

    repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
    repo_info = requests.get(repo_url, headers=headers)
    
    if repo_info.status_code != 200:
        print(f"❌ API 오류: 레포지토리를 찾을 수 없습니다. (권한이나 이름을 확인하세요)")
        return categorized_files
        
    real_default_branch = repo_info.json().get('default_branch', 'main')
    
    tree_url = f"https://api.github.com/repos/{username}/{repo_name}/git/trees/{real_default_branch}?recursive=1"
    response = requests.get(tree_url, headers=headers)

    if response.status_code != 200:
        return categorized_files
        
    tree = response.json().get('tree', [])
    
    file_paths = [item['path'] for item in tree if item['type'] == 'blob']
    
    if not file_paths:
        return categorized_files

    categorized_files = categorize_files_with_gemini(file_paths)
            
    return categorized_files

def fetch_recent_commits(username, token, repo_name, limit=100):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    commits_url = f"https://api.github.com/repos/{username}/{repo_name}/commits?per_page={limit}"
    response = requests.get(commits_url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    return []

import base64

def fetch_file_contents(username, token, repo_name, file_paths, max_files=15):
    """
    분류된 파일들의 실제 내용을 GitHub API를 통해 가져옵니다.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    contents = []
    for path in file_paths[:max_files]:
        url = f"https://api.github.com/repos/{username}/{repo_name}/contents/{path}"
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            if data.get('encoding') == 'base64':
                try:
                    decoded = base64.b64decode(data['content']).decode('utf-8')
                    contents.append(f"--- FILE: {path} ---\n{decoded}\n")
                except Exception:
                    continue
    return "\n".join(contents)
