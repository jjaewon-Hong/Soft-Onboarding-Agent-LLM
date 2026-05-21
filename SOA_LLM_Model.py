import os
import sys
from pathlib import Path
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# 🚀 [핵심 수정] 다른 커스텀 모듈(github_analyzer, llm_engine)을 import하기 전에 .env를 최상단에서 먼저 로드합니다.
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# 환경변수가 로드된 후 안전하게 다른 모듈들을 불러옵니다.
# pyrefly: ignore [missing-import]
from supabase import create_client, Client
from github_analyzer import analyze_single_repository, fetch_recent_commits, fetch_file_contents
from llm_engine import analyze_functional_view, analyze_interface_view, analyze_data_view, analyze_process_view
from urllib.parse import urlparse

def parse_repo_info(repo_url):
    """GitHub URL에서 username과 repo_name을 추출합니다."""
    path = urlparse(repo_url).path.strip('/')
    parts = path.split('/')
    if len(parts) >= 2:
        return parts[0], parts[1]
    return None, None

def main():
    # 1. 인자 확인
    if len(sys.argv) < 3:
        print("❌ 사용법: python SOA_LLM_Model.py <github_url> <space_id>")
        return
    
    TARGET_URL = sys.argv[1]
    SPACE_ID = sys.argv[2]
    USERNAME, REPO_NAME = parse_repo_info(TARGET_URL)
    
    if not USERNAME or not REPO_NAME:
        print("❌ 오류: 유효한 GitHub URL이 아닙니다.")
        return

    print(f"🚀 Soft On-boarding Agent [DB 데이터 적재 파이프라인] 시작")
    print(f"👉 대상 레포지토리: {USERNAME}/{REPO_NAME}")
    print(f"👉 대상 스페이스 ID: {SPACE_ID}\n")
    
    # [수정] 이미 최상단에서 로드했으므로 중복 코드는 제거 및 정리했습니다.
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    SUPABASE_URL = os.getenv("SUPABASE_URL") 
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") 

    if not GITHUB_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ 오류: .env 파일 설정을 확인해주세요.")
        return

    # 3. Supabase 클라이언트 초기화
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 4. 분석 및 적재
    print(f"🔍 [로직 A] '{REPO_NAME}' 파일 분류 중...")
    categorized_files = analyze_single_repository(USERNAME, GITHUB_TOKEN, REPO_NAME)
    
    # -- Functional View --
    print(f"🔍 Functional View 분석 중...")
    func_files = categorized_files.get("Functional", [])
    if func_files:
        func_content = fetch_file_contents(USERNAME, GITHUB_TOKEN, REPO_NAME, func_files)
        if func_content:
            func_data = analyze_functional_view(REPO_NAME, func_content)
            for forest in func_data:
                f_res = supabase.table("Functional").insert({
                    "repo_name": REPO_NAME,
                    "space_id": SPACE_ID, 
                    "name": forest.get("name", "Unknown"), 
                    "element_type": "FOREST", 
                    "description": forest.get("description", "")
                }).execute()
                
                if f_res.data:
                    forest_id = f_res.data[0]['id']
                    for tree in forest.get("children", []):
                        t_res = supabase.table("Functional").insert({
                            "repo_name": REPO_NAME,
                            "space_id": SPACE_ID, 
                            "parent_id": forest_id, 
                            "name": tree.get("name", "Unknown"),
                            "element_type": "TREE", 
                            "description": tree.get("description", ""), 
                            "file_path": tree.get("file_path", "")
                        }).execute()
                        
                        if t_res.data:
                            tree_id = t_res.data[0]['id']
                            for ring in tree.get("children", []):
                                supabase.table("Functional").insert({
                                    "repo_name": REPO_NAME,
                                    "space_id": SPACE_ID, 
                                    "parent_id": tree_id, 
                                    "name": ring.get("name", "Unknown"),
                                    "element_type": "RING", 
                                    "description": ring.get("description", ""), 
                                    "api_method": ring.get("api_method", ""), 
                                    "api_url": ring.get("api_url", "")
                                }).execute()
            print("  ✅ Functional View 적재 완료!")
        else:
            print("  ⚠️ Functional View 파일 내용을 가져오지 못했습니다.")
    else:
        print("  ⚠️ Functional View 대상 파일이 없습니다.")

    # -- Interface View --
    print(f"🔍 Interface View 분석 중...")
    iface_files = categorized_files.get("Interface", [])
    if iface_files:
        iface_content = fetch_file_contents(USERNAME, GITHUB_TOKEN, REPO_NAME, iface_files)
        if iface_content:
            iface_data = analyze_interface_view(REPO_NAME, iface_content)
            supabase.table("Interface").insert({
                "repo_name": REPO_NAME,
                "space_id": SPACE_ID,
                "interface_view_data": iface_data
            }).execute()
            print("  ✅ Interface View 적재 완료!")
        else:
            print("  ⚠️ Interface View 파일 내용을 가져오지 못했습니다.")
    else:
        print("  ⚠️ Interface View 대상 파일이 없습니다.")

    # -- Data View --
    print(f"🔍 Data View 분석 중...")
    data_files = categorized_files.get("Data", [])
    if data_files:
        data_content = fetch_file_contents(USERNAME, GITHUB_TOKEN, REPO_NAME, data_files)
        if data_content:
            schema_data = analyze_data_view(REPO_NAME, data_content)
            supabase.table("Data").insert({
                "repo_name": REPO_NAME,
                "space_id": SPACE_ID,
                "analyzed_json": schema_data
            }).execute()
            print("  ✅ Data View 적재 완료!")
        else:
            print("  ⚠️ Data View 파일 내용을 가져오지 못했습니다.")
    else:
        print("  ⚠️ Data View 대상 파일이 없습니다.")

    # -- Process View --
    print(f"🔍 Process View 분석 중...")
    proc_files = categorized_files.get("Process", [])
    if proc_files:
        proc_content = fetch_file_contents(USERNAME, GITHUB_TOKEN, REPO_NAME, proc_files)
        if proc_content:
            proc_data = analyze_process_view(REPO_NAME, proc_content)
            supabase.table("Process").insert({
                "repo_name": REPO_NAME,
                "space_id": SPACE_ID,
                "process_json": proc_data
            }).execute()
            print("  ✅ Process View 적재 완료!")
        else:
            print("  ⚠️ Process View 파일 내용을 가져오지 못했습니다.")
    else:
        print("  ⚠️ Process View 대상 파일이 없습니다.")

    print(f"\n🔍 [로직 B] '{REPO_NAME}' 커밋 분석 중...")
    recent_commits = fetch_recent_commits(USERNAME, GITHUB_TOKEN, REPO_NAME, limit=100)
    
    commits_data = []
    if recent_commits:
        for commit_data in recent_commits:
            sha = commit_data.get('sha', '')[:7]
            info = commit_data.get('commit', {})
            msg = info.get('message', '').split('\n')[0]
            date = info.get('author', {}).get('date', '')[:10]
            
            commits_data.append({
                "repo_name": REPO_NAME,
                "commit_sha": sha,
                "message": msg,
                "commit_date": date
            })

    if commits_data:
        try:
            for i in range(0, len(commits_data), 100):
                chunk = commits_data[i:i+100]
                supabase.table("CommitHistory").insert(chunk).execute()
            print(f"  ✅ [로직 B] CommitHistory 적재 완료!")
        except Exception as e:
            print(f"  ❌ [로직 B] 적재 실패: {e}")

    # ==========================================
    # 5. [필수 확인] DB 데이터 검증 로직
    # ==========================================
    print("\n🔍 [데이터 검증] Supabase에 데이터가 진짜로 들어갔는지 확인합니다...")
    check_tables = ["Functional", "Interface", "Data", "Process", "CommitHistory"]
    for table_name in check_tables:
        try:
            response = supabase.table(table_name).select("*", count='exact').limit(1).execute()
            print(f"✅ 데이터 확인 성공! 현재 {table_name} 테이블의 총 데이터 개수: {response.count if response.count is not None else '0'}개")
        except Exception as e:
            print(f"❌ 데이터 조회 실패 ({table_name}): {e}")
    print(f"💡 완료!")

if __name__ == "__main__":
    main()
