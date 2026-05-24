import os
import sys
from pathlib import Path
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# Load env variables at the very beginning
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# Safe imports after env is loaded
# pyrefly: ignore [missing-import]
from supabase import create_client, Client
from datetime import datetime, timezone
from github_analyzer import analyze_single_repository, fetch_recent_commits, fetch_file_contents, fetch_file_contents_dict
from llm_engine import analyze_functional_view, analyze_interface_view, analyze_data_view, analyze_process_view
from urllib.parse import urlparse


def parse_repo_info(repo_url):
    """GitHub URL에서 username과 repo_name을 추출합니다."""
    path = urlparse(repo_url).path.strip('/')
    parts = path.split('/')
    if len(parts) >= 2:
        repo_name = parts[1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        return parts[0], repo_name
    return None, None


def main():
    if len(sys.argv) < 3:
        print("사용법: python SOA_LLM_Model.py <github_url> <space_id>")
        return

    TARGET_URL = sys.argv[1]
    SPACE_ID = sys.argv[2]
    USERNAME, REPO_NAME = parse_repo_info(TARGET_URL)

    if not USERNAME or not REPO_NAME:
        print("오류: 유효한 GitHub URL이 아닙니다.")
        return

    print(f"Soft On-boarding Agent [DB 데이터 적재 파이프라인] 시작")
    print(f"  대상 레포지토리: {USERNAME}/{REPO_NAME}")
    print(f"  대상 스페이스 ID: {SPACE_ID}\n")

    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    if not GITHUB_TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
        print("오류: .env 파일 설정을 확인해주세요. (GITHUB_TOKEN, SUPABASE_URL, SUPABASE_KEY)")
        return

    # -------------------------------------------
    # Step 0: 테이블 자동 생성 (없으면 create)
    # -------------------------------------------
    print("[Step 0] 준비 완료. 데이터 적재를 시작합니다...")

    # -------------------------------------------
    # Supabase 클라이언트 초기화
    # -------------------------------------------
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # -------------------------------------------
    # Step 1: 파일 분류
    # -------------------------------------------
    print(f"\n[로직 A] '{REPO_NAME}' 파일 분류 중...")
    categorized_files = analyze_single_repository(USERNAME, GITHUB_TOKEN, REPO_NAME)

    # ==========================================
    # Functional View
    # ==========================================
    print("  Functional View 분석 중...")
    func_files = categorized_files.get("Functional", [])
    if func_files:
        func_content_dict = fetch_file_contents_dict(USERNAME, GITHUB_TOKEN, REPO_NAME, func_files)
        if func_content_dict:
            func_data = analyze_functional_view(REPO_NAME, func_content_dict)

            if func_data and isinstance(func_data, list):
                forest_nodes = [item for item in func_data if item.get("element_type") == "FOREST"]
                tree_nodes   = [item for item in func_data if item.get("element_type") == "TREE"]
                ring_nodes   = [item for item in func_data if item.get("element_type") == "RING"]

                temp_to_actual_id = {}

                # FOREST 삽입
                if forest_nodes:
                    payload = [
                        {
                            "space_id":     SPACE_ID,
                            "repo_name":    REPO_NAME,
                            "name":         f.get("name", "Unknown"),
                            "element_type": "FOREST",
                            "description":  f.get("description", ""),
                            "created_at":   datetime.now(timezone.utc).isoformat()
                        }
                        for f in forest_nodes
                    ]
                    try:
                        res = supabase.table("functional").insert(payload).execute()
                        if res.data:
                            for original, inserted in zip(forest_nodes, res.data):
                                temp_to_actual_id[original.get("temp_id")] = inserted.get("id")
                        print(f"    [OK] Functional FOREST {len(payload)}건 적재 완료")
                    except Exception as e:
                        print(f"    [FAIL] Functional FOREST 적재 실패: {e}")

                # TREE 삽입
                if tree_nodes:
                    payload = [
                        {
                            "space_id":     SPACE_ID,
                            "repo_name":    REPO_NAME,
                            "parent_id":    temp_to_actual_id.get(t.get("parent_temp_id")),
                            "name":         t.get("name", "Unknown"),
                            "element_type": "TREE",
                            "description":  t.get("description", ""),
                            "file_path":    t.get("file_path", ""),
                            "created_at":   datetime.now(timezone.utc).isoformat()
                        }
                        for t in tree_nodes
                    ]
                    try:
                        res = supabase.table("functional").insert(payload).execute()
                        if res.data:
                            for original, inserted in zip(tree_nodes, res.data):
                                temp_to_actual_id[original.get("temp_id")] = inserted.get("id")
                        print(f"    [OK] Functional TREE {len(payload)}건 적재 완료")
                    except Exception as e:
                        print(f"    [FAIL] Functional TREE 적재 실패: {e}")

                # RING 삽입
                if ring_nodes:
                    payload = [
                        {
                            "space_id":     SPACE_ID,
                            "repo_name":    REPO_NAME,
                            "parent_id":    temp_to_actual_id.get(r.get("parent_temp_id")),
                            "name":         r.get("name", "Unknown"),
                            "element_type": "RING",
                            "description":  r.get("description", ""),
                            "file_path":    r.get("file_path", ""),
                            "api_method":   r.get("api_method"),
                            "api_url":      r.get("api_url"),
                            "created_at":   datetime.now(timezone.utc).isoformat()
                        }
                        for r in ring_nodes
                    ]
                    try:
                        supabase.table("functional").insert(payload).execute()
                        print(f"    [OK] Functional RING {len(payload)}건 적재 완료")
                    except Exception as e:
                        print(f"    [FAIL] Functional RING 적재 실패: {e}")
            else:
                print("    [WARN] Functional View 데이터가 없거나 형식이 올바르지 않습니다.")
        else:
            print("    [WARN] Functional View 파일 내용을 가져오지 못했습니다.")
    else:
        print("    [WARN] Functional View 대상 파일이 없습니다.")

    # ==========================================
    # Interface View
    # ==========================================
    print("  Interface View 분석 중...")
    iface_files = categorized_files.get("Interface", [])
    if iface_files:
        iface_content = fetch_file_contents(USERNAME, GITHUB_TOKEN, REPO_NAME, iface_files)
        if iface_content:
            iface_data = analyze_interface_view(REPO_NAME, iface_content)

            if iface_data and isinstance(iface_data, list):
                for item in iface_data:
                    item["space_id"] = SPACE_ID
                    item.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                try:
                    supabase.table("interface").insert(iface_data).execute()
                    print(f"    [OK] Interface View {len(iface_data)}건 적재 완료")
                except Exception as e:
                    print(f"    [FAIL] Interface View 적재 실패: {e}")
            else:
                print("    [WARN] Interface View 데이터가 없거나 형식이 올바르지 않습니다.")
        else:
            print("    [WARN] Interface View 파일 내용을 가져오지 못했습니다.")
    else:
        print("    [WARN] Interface View 대상 파일이 없습니다.")

    # ==========================================
    # Data View
    # ==========================================
    print("  Data View 분석 중...")
    data_files = categorized_files.get("Data", [])
    if data_files:
        schema_data = analyze_data_view(REPO_NAME, data_files)
        if schema_data and isinstance(schema_data, list):
            for item in schema_data:
                item["space_id"] = SPACE_ID
            try:
                supabase.table("data").insert(schema_data).execute()
                print(f"    [OK] Data View {len(schema_data)}건 적재 완료")
            except Exception as e:
                print(f"    [FAIL] Data View 적재 실패: {e}")
        else:
            print("    [WARN] Data View 데이터가 없거나 형식이 올바르지 않습니다.")
    else:
        print("    [WARN] Data View 대상 파일이 없습니다.")

    # ==========================================
    # Process View
    # ==========================================
    print("  Process View 분석 중...")
    proc_files = categorized_files.get("Process", [])
    if proc_files:
        proc_content = fetch_file_contents(USERNAME, GITHUB_TOKEN, REPO_NAME, proc_files)
        if proc_content:
            proc_data = analyze_process_view(REPO_NAME, proc_content)

            if proc_data and isinstance(proc_data, list):
                for item in proc_data:
                    item["space_id"] = SPACE_ID
                    item.setdefault("created_at", datetime.now(timezone.utc).isoformat())
                try:
                    supabase.table("process").insert(proc_data).execute()
                    print(f"    [OK] Process View {len(proc_data)}건 적재 완료")
                except Exception as e:
                    print(f"    [FAIL] Process View 적재 실패: {e}")
            else:
                print("    [WARN] Process View 데이터가 없거나 형식이 올바르지 않습니다.")
        else:
            print("    [WARN] Process View 파일 내용을 가져오지 못했습니다.")
    else:
        print("    [WARN] Process View 대상 파일이 없습니다.")

    # ==========================================
    # 로직 B: CommitHistory
    # ==========================================
    print(f"\n[로직 B] '{REPO_NAME}' 커밋 분석 중...")
    recent_commits = fetch_recent_commits(USERNAME, GITHUB_TOKEN, REPO_NAME, limit=100)

    commits_data = []
    if recent_commits:
        for commit_data in recent_commits:
            sha  = commit_data.get('sha', '')[:7]
            info = commit_data.get('commit', {})
            msg  = info.get('message', '').split('\n')[0]
            date = info.get('author', {}).get('date', '')[:10]
            commits_data.append({
                "space_id":    SPACE_ID,
                "repo_name":   REPO_NAME,
                "commit_sha":  sha,
                "message":     msg,
                "commit_date": date,
                "author":      info.get('author', {}).get('name', 'Unknown')
            })

    if commits_data:
        try:
            for i in range(0, len(commits_data), 100):
                chunk = commits_data[i:i + 100]
                supabase.table("commit_history").insert(chunk).execute()
            print(f"  [OK] CommitHistory {len(commits_data)}건 적재 완료")
        except Exception as e:
            print(f"  [FAIL] CommitHistory 적재 실패: {e}")

    # ==========================================
    # 최종 검증
    # ==========================================
    print("\n[데이터 검증] Supabase 적재 결과 확인...")
    check_tables = ["functional", "interface", "data", "process", "commit_history"]
    for table_name in check_tables:
        try:
            response = supabase.table(table_name).select("*", count="exact").limit(1).execute()
            count = response.count if response.count is not None else 0
            print(f"  {table_name}: {count}건")
        except Exception as e:
            print(f"  {table_name}: 조회 실패 - {e}")

    print("\n완료!")


if __name__ == "__main__":
    main()