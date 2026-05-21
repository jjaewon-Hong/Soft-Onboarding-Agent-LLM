import requests

CATEGORY_RULES = {
    "Interface": [".jsx", ".tsx", ".html", ".css", ".vue", "controller", "view", "router", "api"],
    "Functional": [".py", ".java", ".go", "service", "util", "core", "logic", "handler"],
    "Data": [".sql", "models", "entity", "dto", "repository", "spark", "airflow", "etl", ".ipynb"],
    "Process": [".md", ".yml", ".yaml", "docker", "pom.xml", "build.gradle", "config", "docs/"]
}

def categorize_file(path):
    path_lower = path.lower()
    for category, keywords in CATEGORY_RULES.items():
        if any(kw in path_lower for kw in keywords):
            return category
    if path_lower.endswith(('.js', '.ts', '.py', '.java', '.cpp', '.c')):
        return "Functional"
    return "Process"

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

    # 🔥 [핵심 수정 포인트] 레포지토리 정보를 찔러서 진짜 기본 브랜치 이름을 먼저 알아냅니다.
    repo_url = f"https://api.github.com/repos/{username}/{repo_name}"
    repo_info = requests.get(repo_url, headers=headers)
    
    if repo_info.status_code != 200:
        print(f"❌ API 오류: 레포지토리를 찾을 수 없습니다. (권한이나 이름을 확인하세요)")
        return categorized_files
        
    # 'master'인지 'main'인지 알아냄 (실패하면 기본값 'main')
    real_default_branch = repo_info.json().get('default_branch', 'main')
    
    # 알아낸 진짜 브랜치 이름으로 Tree API를 호출합니다.
    tree_url = f"https://api.github.com/repos/{username}/{repo_name}/git/trees/{real_default_branch}?recursive=1"
    response = requests.get(tree_url, headers=headers)

    if response.status_code != 200:
        return categorized_files
        
    tree = response.json().get('tree', [])
    for item in tree:
        if item['type'] == 'blob': 
            path = item['path']
            category = categorize_file(path)
            if category in categorized_files:
                categorized_files[category].append(path)
            
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