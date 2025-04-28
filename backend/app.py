# --- START OF FILE backend/app.py (API Only) ---

from flask import Flask, jsonify, send_from_directory, request, abort
from flask_cors import CORS
import json
import os
from datetime import datetime

# Flask 앱 생성 - 정적 파일 서빙 설정 제거
# 이제 정적 파일은 Render Static Site에서 제공합니다.
app = Flask(__name__)
CORS(app) # API 엔드포인트에 대해 CORS 허용

def load_school_data_from_json():
    # app.py 파일이 있는 'backend' 폴더 기준으로 schools.json 경로 설정
    # Render Root Directory가 'backend'일 때, schools.json은 ./schools.json 경로에 있습니다.
    # os.path.dirname(os.path.abspath(__file__))는 실행 환경에 따라 경로가 복잡해질 수 있으므로,
    # 상대 경로인 './schools.json' 또는 '__file__' 기반 경로를 Render Root Directory 기준으로 해석되게 수정합니다.
    # Render Root Directory가 'backend'일 때, './schools.json'는 '/opt/render/project/src/backend/schools.json'을 가리킵니다.
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schools.json')
    # 또는 Render Root Directory를 backend로 설정한다면 그냥 'schools.json'으로 접근해 볼 수도 있습니다.
    # file_path = 'schools.json' # Simple relative path assuming correct CWD

    # Render 환경에서는 현재 작업 디렉토리(CWD)가 Root Directory입니다.
    # 따라서 app.py가 backend 폴더에 있다면 CWD는 backend입니다.
    # 그러므로 'schools.json'이라고 바로 접근하는 것이 맞습니다.
    # 하지만 안전을 위해 '__file__' 기반으로 가는 것이 더 좋습니다.
    # Render의 '/opt/render/project/src' 안에 코드가 복사되므로,
    # Root Directory가 'backend'이면 app.py 경로는 '/opt/render/project/src/backend/app.py'
    # '../frontend'는 '/opt/render/project/src/frontend'
    # './schools.json'는 '/opt/render/project/src/backend/schools.json'

    # 이전 코드가 './schools.json'을 제대로 찾았던 것으로 보아, 이 경로는 문제가 아니었습니다.
    file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schools.json')


    loaded_schools = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

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

            if 'tree_growth_stage' not in school:
                 school['tree_growth_stage'] = 1
            school['tree_growth_stage'] = max(1, min(7, school['tree_growth_stage']))

            if 'praise_points' not in school:
                 school['praise_points'] = 0

            # Assign a temporary ID if not already present
            if 'id' not in school:
                 school['id'] = len(loaded_schools) + 1

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

schools_data = load_school_data_from_json()

praise_posts_data = {}

next_praise_post_id = 1

# --- 정적 파일 서빙 라우트 모두 제거 (Static Site가 담당) ---
# @app.route('/') ... serve_index
# @app.route('/<path:filename>') ... serve_static


# --- API Routes (그대로 유지) ---

@app.route('/api/schools', methods=['GET'])
def get_schools():
    # /api/schools 요청만 처리
    return jsonify(schools_data)

@app.route('/api/schools/<int:school_id>/posts', methods=['GET'])
def get_praise_posts(school_id):
    # /api/schools/ID/posts GET 요청 처리
    school = next((s for s in schools_data if s['id'] == school_id), None)
    if not school:
        return jsonify({"error": "School not found"}), 404

    posts = list(praise_posts_data.get(school_id, []))

    try:
        posts.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    except Exception as e:
        print(f"Error sorting praise posts for school ID {school_id}: {e}")

    print(f"Loaded {len(posts)} praise posts from memory for school ID {school_id}.")
    return jsonify(posts)

@app.route('/api/schools/<int:school_id>/posts', methods=['POST'])
def add_praise_post(school_id):
    # /api/schools/ID/posts POST 요청 처리
    global next_praise_post_id

    try:
        post_data = request.json
        author = post_data.get('author', '익명')
        content = post_data.get('content')

        if not content:
            return jsonify({"error": "Content is required"}), 400

        school = next((s for s in schools_data if s['id'] == school_id), None)
        if not school:
            return jsonify({"error": "School not found"}), 404

        points_to_award = 10

        new_post = {
            "id": next_praise_post_id,
            "institution_id": school_id,
            "author_info": author,
            "content": content,
            "points_awarded": points_to_award,
            "created_at": datetime.utcnow().isoformat() + 'Z'
        }
        next_praise_post_id += 1

        if school_id not in praise_posts_data:
            praise_posts_data[school_id] = []
        praise_posts_data[school_id].append(new_post)

        current_points = school.get('praise_points', 0)
        current_stage = school.get('tree_growth_stage', 1)
        new_points = current_points + points_to_award

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

        school['praise_points'] = new_points
        school['tree_growth_stage'] = new_stage

        print(f"Praise post added for school ID {school_id} in memory. New points: {new_points}, New stage: {new_stage}")

        return jsonify({
            "message": "Praise post added and points updated in memory",
            "post_id": new_post['id'],
            "new_points": new_points,
            "new_stage": new_stage,
            "updated_school": school # 업데이트된 학교 데이터 객체 함께 반환
        }), 201

    except Exception as e:
        print(f"Error adding praise post for school {school_id}: {e}")
        return jsonify({"error": "Failed to add praise post"}), 500
