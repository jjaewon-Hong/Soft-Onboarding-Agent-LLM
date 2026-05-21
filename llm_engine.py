import os
from pathlib import Path
# pyrefly: ignore [missing-import]
from dotenv import load_dotenv

# 🚀 [안정성 강화] llm_engine만 단독으로 임포트되더라도 API Key 에러가 나지 않도록 로컬 .env 로드를 추가합니다.
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)

# pyrefly: ignore [missing-import]
from google import genai
# pyrefly: ignore [missing-import]
from google.genai import types

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

def generate_onboarding_guide(repo_name, categorized_files, simulated_rag_context=""):
    """
    이 함수는 이제 기존 레포지토리 분석 결과를 무시하고, 
    재원님의 프롬프트에 따라 Soft On-boarding Agent의 React 및 Spring Boot 뼈대 코드를 생성합니다.
    """
    
    # 1. 시스템 프롬프트: 프론트엔드와 백엔드 역할을 동시에 부여
    system_prompt = """
    너는 B2B SaaS 전문 프론트엔드 개발자이자, Spring Boot 기반의 데이터 파이프라인을 구축하는 백엔드 아키텍트야.
    현재 'Soft On-boarding Agent'의 프론트엔드(React/Vite)와 백엔드(Spring Boot) 핵심 로직을 구현해야 해.
    """

    # 2. 유저 프롬프트: 재원님이 작성하신 프롬프트 원본 + 약간의 디테일(버전, DB 등) 추가 적용
    user_prompt = """
    [Frontend 구현 요구사항]
    현재 'Soft On-boarding Agent'의 [로그인 및 팀 스페이스 온보딩] 플로우를 React(Vite)와 Tailwind CSS를 사용해 구현하려고 해.
    페이지 이동을 위해 `react-router-dom` v6를 사용하고, 아이콘은 `lucide-react`를 적용해 줘.
    디자인은 Linear, Notion처럼 화이트/그레이 톤에 모던하고 여백이 많은 스타일로 깔끔하게 구성해 줘.

    - 로그인 페이지 (LoginPage.tsx): 화면 중앙에 심플한 로고 텍스트와 함께 [Continue with GitHub] 버튼 하나만 크게 배치해 줘. (GitHub 아이콘 포함)
    - 온보딩 라우팅 페이지 (OnboardingPage.tsx): 로그인 후 팀이 없는 유저가 보는 화면이야. 화면 중앙에 예쁜 카드 UI를 배치해 줘.
      * 기본 상태 (팀 참여): '초대받은 팀 코드를 입력하세요'라는 문구와 함께 텍스트 Input, 그리고 [Join Space] 버튼을 만들어 줘.
      * 하단 토글: 그 아래에 연한 글씨로 "새로운 팀 스페이스를 구축하고 싶으신가요? [팀 생성하기]" 버튼을 만들어 줘.
    - 팀 생성 모달 또는 뷰 전환 (CreateTeamView): 위에서 [팀 생성하기]를 누르면 부드럽게 화면이 전환되며 입력창이 바뀌도록 해 줘. '분석할 GitHub 레포지토리 URL을 입력하세요' 문구와 Input, 그리고 [생성 및 분석 시작] 버튼을 만들어 줘.
    - 분석 로딩 컴포넌트 (AnalyzingLoader.tsx): [생성 및 분석 시작] 버튼을 누르면 AI가 코드를 분석한다는 느낌을 주는 세련된 로딩 화면(스피너 또는 프로그레스 바)을 띄워 줘. "AI가 레포지토리 구조와 최근 커밋 히스토리를 분석하여 4-Way View를 구축하고 있습니다..." 라는 텍스트를 포함해 줘.

    모든 상태 관리(팀 참여, 생성 전환 등)를 포함하여 작동 가능한 코드 뼈대로 작성해 줘.

    ===SPLIT===

    [Backend 구현 요구사항]
    현재 'Soft On-boarding Agent'의 [GitHub OAuth 로그인 및 팀 스페이스 분석 생성] 핵심 비즈니스 로직을 구현해야 해.
    Java 17 환경을 사용하고, 데이터베이스는 PostgreSQL 기준으로 Entity를 매핑해 줘.

    - GitHub OAuth 2.0 로그인: spring-boot-starter-oauth2-client를 활용해 GitHub 로그인을 구현하고, 성공 시 발급받은 Access Token을 DB에 유저 정보와 함께 저장해 줘. (이 토큰으로 프라이빗 레포지토리 API를 호출해야 함).
    - 팀 스페이스 참여 API (Join): 프론트에서 전달받은 teamCode를 검증하여 해당 팀에 유저를 매핑하는 엔드포인트를 만들어 줘.
    - 팀 스페이스 생성 API (Create) - ⭐️ 핵심 ⭐️: 프론트에서 GitHub Repo URL을 받으면 다음 2가지 로직을 비동기(또는 효율적으로) 처리하는 서비스 레이어를 짜 줘.
      * [로직 A: 뼈대 구축]: GitHub Git Trees API(recursive)를 호출해 파일 경로 목록을 가져온 뒤, LLM API(Google Gemini API 사용 기준)를 통해 이 파일들을 4가지 'Functional', 'Data', 'Interface', 'Process'로 분류해서 각각 테이블에 repo_name, file_path, space_id, created_at에 저장해 줘. 특히 space_id는 team code 문자열이 아닌 space id를 넣어줘야 해. LLM API 호출 부분은 서비스 레이어 뼈대만 작성해.
      * [로직 B: 히스토리 매핑]: GitHub Commits API를 호출해 해당 레포의 '최근 100개' 커밋 내역과 Diff를 가져와. 그리고 이 커밋들이 수정/생성한 파일 경로를 바탕으로, [로직 A]에서 만든 컴포넌트 노드들과 매핑하여 CommitHistory 테이블에 저장해 줘. (프론트에서 특정 노드 클릭 시 이 히스토리가 조회되어야 함).

    코드 구조는 Controller, Service, Repository(JPA) 패턴으로 깔끔하게 나누고, 외부 API(GitHub) 통신 부분은 WebClient 또는 RestTemplate을 사용하는 뼈대 코드로 작성해 줘.
    
    [중요 규칙]
    반드시 Frontend 가이드 작성이 끝난 직후, Backend 가이드를 시작하기 전에 정확히 '===SPLIT===' 이라는 텍스트를 출력해서 두 파트를 완벽하게 구분해 줘. (이 기호를 기준으로 파이썬 시스템이 파일을 쪼갤 예정이야)
    """

    print("[LLM] 재원님의 커스텀 프롬프트를 바탕으로 React 및 Spring Boot 코드를 생성 중입니다...")
    
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
        )
    )
    
    return response.text

import json

def categorize_files_with_gemini(file_paths):
    """
    파일 경로 리스트를 받아 4-Way View 카테고리로 분류합니다.
    """
    categorized = {
        "Interface": [],
        "Functional": [],
        "Data": [],
        "Process": []
    }
    
    for path in file_paths:
        lower_path = path.lower()
        if any(ignore in lower_path for ignore in ['.git/', 'node_modules/', 'venv/', '__pycache__', '.jpg', '.png', '.ico', '.svg', 'package-lock.json', 'yarn.lock']):
            continue
            
        if any(kw in lower_path for kw in ['components', 'pages', 'views', 'ui', 'styles', 'css', 'tailwind', '.jsx', '.tsx', 'router']):
            categorized["Interface"].append(path)
        elif any(kw in lower_path for kw in ['entity', 'schema', 'prisma', 'sql', 'ddl', 'models', 'migrations']):
            categorized["Data"].append(path)
        elif any(kw in lower_path for kw in ['.github', 'workflows', 'docker', 'build.gradle', 'pom.xml', 'package.json', 'Makefile', 'ci', 'cd']):
            categorized["Process"].append(path)
        elif any(kw in lower_path for kw in ['service', 'utils', 'handler', 'controller', 'api', 'logic', '.py', '.java', '.go', '.ts', '.js']):
            categorized["Functional"].append(path)
            
    return categorized

def analyze_functional_view(repo_name, files_content_str):
    system_prompt = """
    너는 시니어 백엔드 아키텍트야. 제공된 소스코드 파일들을 분석해서 비즈니스 로직과 서비스 계층이 어떻게 구성되어 있는지 분석해줘.
    FOREST (도메인 분류), TREE (클래스/파일 단위), RING (핵심 메서드/API) 계층 구조로 나누어 JSON으로 응답해.
    반드시 다음 JSON 배열 형태로만 응답해.
    [
      {
        "name": "User Domain (Forest 예시)",
        "element_type": "FOREST",
        "description": "유저 관련 비즈니스 도메인",
        "children": [
          {
            "name": "UserService.java",
            "element_type": "TREE",
            "description": "유저 비즈니스 로직 클래스",
            "file_path": "src/main/java/.../UserService.java",
            "children": [
              {
                "name": "login()",
                "element_type": "RING",
                "description": "유저 로그인 처리 메서드",
                "api_method": "POST",
                "api_url": "/api/v1/login"
              }
            ]
          }
        ]
      }
    ]
    """
    
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=f"레포지토리: {repo_name}\n\n파일 내용들:\n{files_content_str}",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
            response_mime_type="application/json"
        )
    )
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return []

def analyze_interface_view(repo_name, files_content_str):
    system_prompt = """
    너는 시니어 프론트엔드 개발자야. 제공된 프론트엔드/UI 파일들을 분석하여 라우팅 트리, 디자인 토큰, UI 컴포넌트 목록을 분석해줘.
    반드시 다음 JSON 객체 형태로만 응답해.
    {
      "routing": [ {"path": "/", "component": "Home"} ],
      "design_tokens": { "colors": ["#fff"], "fonts": ["Inter"] },
      "components": [ {"name": "Button", "description": "공통 버튼 컴포넌트"} ]
    }
    """
    
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=f"레포지토리: {repo_name}\n\n파일 내용들:\n{files_content_str}",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
            response_mime_type="application/json"
        )
    )
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return {}

def analyze_data_view(repo_name, files_content_str):
    system_prompt = """
    너는 데이터베이스 아키텍트야. 제공된 Entity/Schema 파일들을 분석해서 ERD 데이터를 뽑아줘.
    테이블 이름, 컬럼 정보, 연관 관계를 분석해서 JSON 형태로 응답해.
    반드시 다음 JSON 객체 형태로만 응답해.
    {
      "nodes": [
        {
          "id": "User",
          "description": "사용자 테이블",
          "columns": [
            { "name": "id", "type": "Long", "is_pk": true, "is_fk": false }
          ]
        }
      ],
      "edges": [
        { "source": "User", "target": "Order", "relation": "1:N" }
      ]
    }
    """
    
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=f"레포지토리: {repo_name}\n\n파일 내용들:\n{files_content_str}",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
            response_mime_type="application/json"
        )
    )
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return {"nodes": [], "edges": []}

def analyze_process_view(repo_name, files_content_str):
    system_prompt = """
    너는 DevOps 엔지려야. CI/CD 파이프라인, Docker, 인프라 설정 파일들을 분석하여 파이프라인 흐름도를 그려줘.
    빌드/테스트/배포 단계, 사용 기술 스택, 환경 변수를 추출해서 JSON으로 응답해.
    반드시 다음 JSON 배열 형태로 응답해.
    [
      {
        "step": "Build",
        "description": "Gradle을 사용한 애플리케이션 빌드",
        "tech_stack": ["Gradle", "Java 17"],
        "env_vars": []
      },
      {
        "step": "Deploy",
        "description": "AWS EC2 배포",
        "tech_stack": ["AWS", "Docker"],
        "env_vars": ["AWS_ACCESS_KEY"]
      }
    ]
    """
    
    response = client.models.generate_content(
        model='gemini-3.1-flash-lite',
        contents=f"레포지토리: {repo_name}\n\n파일 내용들:\n{files_content_str}",
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.2,
            response_mime_type="application/json"
        )
    )
    try:
        return json.loads(response.text)
    except json.JSONDecodeError:
        return []
