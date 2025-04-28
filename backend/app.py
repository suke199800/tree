# --- START OF FILE app.py ---

from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import json
import os
from datetime import datetime

# static_folder를 'frontend'로 지정하고, Render Root Directory를 저장소 루트('.')로 설정합니다.
app = Flask(__name__, static_folder='frontend')
CORS(app)

def load_school_data_from_json():
    # app.py 파일이 있는 'backend' 폴더 기준으로 schools.json 경로 설정
    file_path = os.path.join(os.path.dirname(__file__), 'schools.json')
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

            # 임시 ID 추가 (DB 사용 전 JSON 데이터에 ID가 없을 경우)
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

# Render Root Directory를 '.'로 설정하면,
# Render는 저장소 루트에서 명령을 실행하지만,
# app.py 파일 자체는 여전히 backend/app.py 경로에 있습니다.
# 따라서 Flask 앱을 찾기 위한 Start Command도 변경해야 합니다.
# Start Command: gunicorn backend.app:app --bind 0.0.0.0:$PORT
# 이렇게 하면 gunicorn이 backend 폴더 안의 app.py 파일에서 app 객체를 찾습니다.


@app.route('/')
def serve_frontend():
    # static_folder가 'frontend'로 설정되어 있으므로,
    # Render Root Directory가 '.'일 때 'frontend' 폴더 안에서 'index.html'을 찾습니다.
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/api/schools', methods=['GET'])
def get_schools():
    return jsonify(schools_data)

@app.route('/api/schools/<int:school_id>/posts', methods=['GET'])
def get_praise_posts(school_id):
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
            "updated_school": school
        }), 201

    except Exception as e:
        print(f"Error adding praise post for school {school_id}: {e}")
        return jsonify({"error": "Failed to add praise post"}), 500

# --- END OF FILE app.py ---
