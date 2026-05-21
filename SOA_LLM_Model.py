import os
from dotenv import load_dotenv
from pathlib import Path
from supabase import create_client, Client
from github_analyzer import analyze_single_repository, fetch_recent_commits

def main():
    print("🚀 Soft On-boarding Agent [DB 데이터 적재 파이프라인] 시작\n")
    
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)
    
    USERNAME = os.getenv("GITHUB_USERNAME")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    SUPABASE_URL = os.getenv("SUPABASE_URL") 
    SUPABASE_KEY = os.getenv("SUPABASE_KEY") 
    TARGET_REPO = os.getenv("TARGET_REPO", "TOP250movie_douban") 

    if not USERNAME or not GITHUB_TOKEN:
        print("❌ 오류: .env 파일 설정을 확인해주세요.")
        return

    # Supabase 클라이언트 초기화
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print(f"🔍 [로직 A] '{TARGET_REPO}' 구조 추출 중...")
    categorized_files = analyze_single_repository(USERNAME, GITHUB_TOKEN, TARGET_REPO)
    print("✅ [로직 A 완료] 4개 카테고리 추출 완료!\n")

    print(f"🔍 [로직 B] '{TARGET_REPO}' 최신 커밋 추출 중...")
    recent_commits = fetch_recent_commits(USERNAME, GITHUB_TOKEN, TARGET_REPO, limit=100)
    print("✅ [로직 B 완료] 100개의 커밋 히스토리 로드 완료!\n") 
    
    print("☁️ Supabase 테이블(Database)에 데이터 적재를 시작합니다...\n")

    # ==========================================
    # [1] 로직 A: ComponentNodes 테이블에 적재
    # ==========================================
    components_data = []
    for cat in ["Interface", "Functional", "Data", "Process"]:
        files_list = categorized_files.get(cat, [])
        for f_path in files_list:
            components_data.append({
                "repo_name": TARGET_REPO,
                "category": cat,
                "file_path": f_path
            })
            
    if components_data:
        try:
            # Supabase Bulk Insert 실행
            supabase.table("ComponentNodes").insert(components_data).execute()
            print(f"  ✅ [로직 A] ComponentNodes 테이블에 {len(components_data)}개의 데이터 적재 완료!")
        except Exception as e:
            print(f"  ❌ [로직 A] 데이터 적재 실패: {e}\n")
    else:
        print("  ⚠️ [로직 A] 적재할 컴포넌트 데이터가 없습니다.\n")

    # ==========================================
    # [2] 로직 B: CommitHistory 테이블에 적재
    # ==========================================
    commits_data = []
    if recent_commits:
        for commit_data in recent_commits:
            sha = commit_data.get('sha', '')[:7] 
            info = commit_data.get('commit', {})
            msg = info.get('message', '').split('\n')[0] 
            date = info.get('author', {}).get('date', '')[:10] 
            author = info.get('author', {}).get('name', '')
            
            commits_data.append({
                "repo_name": TARGET_REPO,
                "commit_sha": sha,
                "message": msg,
                "commit_date": date,
                "author": author
            })

    if commits_data:
        try:
            # Supabase Bulk Insert 실행
            supabase.table("CommitHistory").insert(commits_data).execute()
            print(f"  ✅ [로직 B] CommitHistory 테이블에 {len(commits_data)}개의 커밋 데이터 적재 완료!")
        except Exception as e:
            print(f"  ❌ [로직 B] 커밋 데이터 적재 실패: {e}\n")
    else:
        print("  ⚠️ [로직 B] 적재할 커밋 데이터가 없습니다.\n")

    print("\n🎉 모든 데이터의 DB 적재가 완료되었습니다!")

if __name__ == "__main__":
    main()