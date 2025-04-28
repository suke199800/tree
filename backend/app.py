# --- START OF FILE app.py ---

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import json
import os
# pyproj는 더 이상 사용하지 않음

app = Flask(__name__, static_folder='../frontend')
CORS(app)

# 데이터베이스 연결 정보는 사용하지 않음
# DB_CONFIG = { ... }
# def get_db_connection(): ...

# 학교 데이터를 schools.json 파일에서 로드합니다.
# 이 데이터는 서버 재시작 시 초기화됩니다.
def load_school_data_from_json():
    # 현재 파일(app.py)이 있는 디렉토리 기준으로 schools.json 경로 설정
    file_path = os.path.join(os.path.dirname(__file__), 'schools.json')
    loaded_schools = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 각 학교 데이터 처리
        for school in data:
            if 'latitude' in school and 'longitude' in school:
                try:
                    school['latitude'] = float(school['latitude'])
                    school['longitude'] = float(school['longitude'])
                except ValueError as e:
                    print(f"Error converting coordinates format for school {school.get('학교명', 'Unknown')}: {e}")
                    continue
                except Exception as e:
                     print(f"An unexpected error occurred while processing coordinates for school {school.get('학교명', 'Unknown')}: {e}")
                     continue
            else:
                 print(f"Warning: Missing latitude/longitude for school {school.get('학교명', 'Unknown')}")
                 continue

            # 기본 단계와 포인트 필드 추가 (JSON 파일에 없을 경우)
            # 이 값들은 서버 재시작 시 항상 초기화됩니다.
            if 'tree_growth_stage' not in school:
                 school['tree_growth_stage'] = 1
            school['tree_growth_stage'] = max(1, min(7, school['tree_growth_stage'])) # 1~7 범위 보정

            if 'praise_points' not in school:
                 school['praise_points'] = 0

            # 임시 ID 추가 (DB 사용 전 JSON 데이터에 ID가 없을 경우)
            # 실제 DB 사용 시에는 DB의 SERIAL PRIMARY KEY를 사용합니다.
            # 여기서는 인덱스를 임시 ID로 사용합니다. 실제 서비스에서는 적절하지 않습니다.
            school['id'] = len(loaded_schools) + 1 # 1부터 시작하는 임시 ID

            loaded_schools.append(school)

    except FileNotFoundError:
        print(f"Error: schools.json not found at {file_path}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {file_path}. Check JSON format.")
        return []
    except Exception as e:
        print(f"An unexpected error occurred while loading or processing data: {e}")
        return []

    print(f"Successfully loaded {len(loaded_schools)} schools from JSON.")
    return loaded_schools

# 애플리케이션 시작 시 schools_data 변수에 데이터 로드 (JSON 파일에서)
schools_data = load_school_data_from_json()

# 칭찬 글 데이터를 저장할 임시 메모리 변수 (서버 재시작 시 초기화됨)
# key: 학교 ID, value: 해당 학교의 칭찬 글 리스트
praise_posts_data = {} # 예: { 1: [{...}, {...}], 2: [{...}] }

# 루트 경로('/')
@app.route('/')
def serve_frontend():
    # static_folder는 생성자에서 '../frontend'로 설정됨
    return send_from_directory(app.static_folder, 'index.html')

# 학교 데이터 API 엔드포인트 ('/api/schools' GET)
# JSON 파일에서 로드된 학교 데이터를 반환합니다.
@app.route('/api/schools', methods=['GET'])
def get_schools():
    # load_school_data_from_json 함수는 서버 시작 시 이미 호출되었고,
    # schools_data 변수에 데이터가 저장되어 있습니다.
    return jsonify(schools_data)

# 특정 학교 칭찬 글 조회 API ('/api/schools/<school_id>/posts' GET)
# 데이터베이스 없이 메모리(praise_posts_data 변수)에서 칭찬 글을 조회합니다.
@app.route('/api/schools/<int:school_id>/posts', methods=['GET'])
def get_praise_posts(school_id):
    # schools_data에서 해당 school_id의 학교 찾기 (임시 ID 사용)
    school = next((s for s in schools_data if s['id'] == school_id), None)
    if not school:
        return jsonify({"error": "School not found"}), 404

    # 메모리 변수에서 해당 학교의 칭찬 글 목록 가져오기 (없으면 빈 리스트)
    # 메모리 변수이므로 서버 재시작 시 모든 칭찬 글이 사라집니다.
    posts = praise_posts_data.get(school_id, [])

    # 칭찬 글 목록을 최신순으로 정렬 (필요하다면)
    # posts.sort(key=lambda x: x['created_at'], reverse=True)

    print(f"Loaded {len(posts)} praise posts from memory for school ID {school_id}.")
    return jsonify(posts)

# 칭찬 글 작성 API ('/api/schools/<school_id>/posts' POST)
# 데이터베이스 없이 메모리(praise_posts_data 변수)에 칭찬 글을 저장하고,
# 메모리상의 학교 데이터(schools_data 변수)의 포인트/단계를 업데이트합니다.
@app.route('/api/schools/<int:school_id>/posts', methods=['POST'])
def add_praise_post(school_id):
    try:
        post_data = request.json
        author = post_data.get('author', '익명')
        content = post_data.get('content')

        if not content:
            return jsonify({"error": "Content is required"}), 400

        # schools_data에서 해당 school_id의 학교 찾기 (임시 ID 사용)
        school = next((s for s in schools_data if s['id'] == school_id), None)
        if not school:
            return jsonify({"error": "School not found"}), 404

        # 칭찬 글에 부여할 포인트 (예: 글 하나당 10점)
        points_to_award = 10

        # 새 칭찬 글 객체 생성 (메모리 저장을 위해)
        new_post = {
            "id": len(praise_posts_data.get(school_id, [])) + 1, # 칭찬 글 임시 ID
            "institution_id": school_id,
            "author_info": author,
            "content": content,
            "points_awarded": points_to_award,
            "created_at": datetime.utcnow().isoformat() + 'Z' # UTC 시간으로 저장 (ISO 8601)
        }

        # 메모리 변수(praise_posts_data)에 칭찬 글 추가
        if school_id not in praise_posts_data:
            praise_posts_data[school_id] = []
        praise_posts_data[school_id].append(new_post)

        # 나무 성장 로직 - 메모리상의 학교 데이터 업데이트
        current_points = school['praise_points']
        current_stage = school['tree_growth_stage']
        new_points = current_points + points_to_award

        # 단계별 필요 포인트 임계값 (예시, 7단계 기준)
        stage_thresholds = {
            1: 20, 2: 50, 3: 100, 4: 200, 5: 350, 6: 500
        }

        new_stage = current_stage
        for stage in range(current_stage, 7):
             threshold = stage_thresholds.get(stage)
             if threshold is not None and new_points >= threshold:
                 new_stage = stage + 1
             else:
                 break

        # 메모리상의 학교 데이터 업데이트
        school['praise_points'] = new_points
        school['tree_growth_stage'] = new_stage
        # school['updated_at'] = datetime.utcnow().isoformat() + 'Z' # 필요하다면 업데이트 시각 기록

        print(f"Praise post added for school ID {school_id} in memory. New points: {new_points}, New stage: {new_stage}")

        # 업데이트된 학교 정보와 함께 성공 응답 반환
        return jsonify({
            "message": "Praise post added and points updated in memory",
            "post_id": new_post['id'],
            "new_points": new_points,
            "new_stage": new_stage,
            # 클라이언트가 지도 마커를 갱신할 수 있도록 업데이트된 학교 데이터 포함
            "updated_school": school
        }), 201

    except Exception as e:
        print(f"Error adding praise post for school {school_id}: {e}")
        return jsonify({"error": "Failed to add praise post"}), 500

# Python의 datetime 모듈 임포트 (칭찬 글 작성 시각 기록용)
from datetime import datetime

# if __name__ == '__main__':
#     # Render에서는 gunicorn 사용
#     # app.run(debug=True)
#     pass

# --- END OF FILE app.py ---
