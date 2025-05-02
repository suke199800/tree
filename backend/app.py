from flask import Flask, jsonify, send_from_directory, request, abort
from flask_cors import CORS
import json
import os
from datetime import datetime
import traceback
import math
Flask 앱 생성
app = Flask(name)
프론트엔드와 백엔드가 같은 Render Web Service에서 제공되므로 CORS 설정은 필요 없을 수 있으나,
로컬 개발 환경이나 향후 분리 배포 가능성을 고려하여 유지하는 것이 일반적입니다.
CORS(app)
중요: 학교 데이터와 칭찬 글은 메모리에 저장됩니다.
Render의 무료 플랜 사용 시 일정 시간 후 서버가 절전 모드에 들어가며 메모리 내용이 초기화됩니다.
유료 플랜에서도 배포 업데이트 등으로 인해 서버가 재시작되면 데이터는 초기화됩니다.
영구적인 데이터 저장이 필요하다면 별도의 데이터베이스(예: Render의 PostgreSQL 등)를 사용해야 합니다.
def load_school_data_from_json():
backend_dir = os.path.dirname(os.path.abspath(file))
project_root = os.path.join(backend_dir, '..')
file_path = os.path.join(project_root, 'schools.json')
print(f"Attempting to load school data from: {file_path}")
loaded_schools = []
try:
if not os.path.exists(file_path):
print(f"ERROR: schools.json not found at {file_path}. Make sure it exists in the project root folder ({project_root}). Returning empty list.")
return []
if not os.access(file_path, os.R_OK):
print(f"ERROR: Cannot read schools.json at {file_path}. Check file permissions. Returning empty list.")
return []
with open(file_path, 'r', encoding='utf-8') as f:
content = f.read().strip()
if not content:
print(f"WARNING: schools.json at {file_path} is empty. Returning empty list.")
return []
f.seek(0)
data = json.load(f)
if not isinstance(data, list):
print(f"ERROR: Data in {file_path} is not a JSON list. Top-level element should be an array []. Returning empty list.")
return []
if not data:
print(f"WARNING: schools.json at {file_path} contains an empty list []. Returning empty list.")
return []
print(f"Successfully read JSON data from {file_path}. Processing {len(data)} potential entries.")
for school in data:
if not isinstance(school, dict):
print(f"WARNING: Invalid school data format (not a dict) encountered. Skipping entry: {school}")
continue
school_name_for_log = school.get('학교명', 'Unknown School')
raw_lat = school.get('latitude')
raw_lon = school.get('longitude')
processed_lat = None
processed_lon = None
if raw_lat is not None and raw_lon is not None:
try:
lat_val = float(raw_lat)
lon_val = float(raw_lon)
if math.isfinite(lat_val) and math.isfinite(lon_val):
processed_lat = lat_val
processed_lon = lon_val
else:
print(f"WARNING: Original coordinates are not finite numbers for school '{school_name_for_log}': ({raw_lat}, {raw_lon}). Treating as invalid original coords.")
except (ValueError, TypeError) as e:
print(f"ERROR: Converting original coordinates format for school '{school_name_for_log}': ({raw_lat}, {raw_lon}) - {e}. Treating as invalid original coords.")
except Exception as e:
print(f"An unexpected error occurred while processing original coordinates for school '{school_name_for_log}': {e}. Treating as invalid original coords.")
school['latitude'] = processed_lat
school['longitude'] = processed_lon
raw_approx_lat = school.get('approx_latitude')
raw_approx_lon = school.get('approx_longitude')
processed_approx_lat = None
processed_approx_lon = None
if raw_approx_lat is not None and raw_approx_lon is not None:
try:
approx_lat_val = float(raw_approx_lat)
approx_lon_val = float(raw_approx_lon)
if math.isfinite(approx_lat_val) and math.isfinite(approx_lon_val):
processed_approx_lat = approx_lat_val
processed_approx_lon = approx_lon_val
else:
print(f"WARNING: Approx coordinates are not finite numbers for school '{school_name_for_log}': ({raw_approx_lat}, {raw_approx_lon}). Treating as invalid approx coords.")
except (ValueError, TypeError) as e:
print(f"ERROR: Invalid approx_coordinates format for school '{school_name_for_log}': ({raw_approx_lat}, {raw_approx_lon}) - {e}. Treating as invalid approx coords.")
except Exception as e:
print(f"An unexpected error occurred while processing approx_coordinates for school '{school_name_for_log}': {e}. Treating as invalid approx coords.")
school['approx_latitude'] = processed_approx_lat
school['approx_longitude'] = processed_approx_lon
try:
school['praise_points'] = int(school.get('praise_points', 0))
except (ValueError, TypeError):
print(f"WARNING: Invalid praise_points format for school '{school_name_for_log}': {school.get('praise_points')}. Setting points to 0.")
school['praise_points'] = 0
try:
school['tree_growth_stage'] = int(school.get('tree_growth_stage', 1))
except (ValueError, TypeError):
print(f"WARNING: Invalid tree_growth_stage format for school '{school_name_for_log}': {school.get('tree_growth_stage')}. Setting stage to 1.")
school['tree_growth_stage'] = 1
school['tree_growth_stage'] = max(1, min(7, school['tree_growth_stage']))
school_id = school.get('id')
is_valid_id = False
if school_id is not None and school_id != "":
try:
int_id = int(school_id)
if not any(s.get('id') == int_id for s in loaded_schools if isinstance(s, dict) and s.get('id') is not None):
school['id'] = int_id
is_valid_id = True
else:
print(f"WARNING: Duplicate ID '{school_id}' found for school '{school_name_for_log}'. Will assign a new ID.")
except (ValueError, TypeError):
print(f"WARNING: Invalid ID format '{school_id}' for school '{school_name_for_log}'. Will assign new ID.")
if not is_valid_id:
new_generated_id = len(loaded_schools) + 1
existing_ids = {s.get('id') for s in loaded_schools if isinstance(s, dict) and s.get('id') is not None}
while new_generated_id in existing_ids:
new_generated_id += 1
school['id'] = new_generated_id
loaded_schools.append(school)
except FileNotFoundError:
print(f"ERROR: File not found during processing after initial check? This shouldn't happen. Check path logic. Returning empty list.")
return []
except json.JSONDecodeError as e:
print(f"ERROR: Could not decode JSON from {file_path}. Check JSON format carefully (e.g., missing commas, extra commas, mismatched brackets, incorrect encoding). Details: {e}")
print(traceback.format_exc())
return []
except Exception as e:
print(f"AN UNEXPECTED ERROR occurred while loading or processing schools.json: {e}")
print(traceback.format_exc())
return []
if loaded_schools:
print(f"SUCCESS: Successfully loaded and processed {len(loaded_schools)} schools from JSON.")
else:
print(f"WARNING: Finished processing schools.json, but no valid school entries were loaded. Returning empty list.")
try:
with open(file_path, 'r', encoding='utf-8') as f:
raw_content = f.read().strip()
if raw_content:
raw_data = json.loads(raw_content)
if isinstance(raw_data, list):
print(f"DEBUG: schools.json contained {len(raw_data)} raw entries, but none were successfully processed.")
else:
print("DEBUG: schools.json was empty or contained only whitespace.")
except Exception:
pass
return loaded_schools
schools_data = []
try:
print("INFO: Starting initial school data load during server startup...")
schools_data = load_school_data_from_json()
if not schools_data:
print("WARNING: Initial school data load resulted in an empty list.")
except Exception as e:
print(f"CRITICAL ERROR: Failed to load school data during server startup: {e}")
print(traceback.format_exc())
schools_data = []
praise_posts_data = {}
next_praise_post_id = 1
stage_thresholds = {
1: 20,
2: 50,
3: 100,
4: 200,
5: 350,
6: 500
}
MAX_STAGE = 7
프로젝트 루트 폴더 경로 계산 (app.py가 backend 폴더 안에 있다고 가정)
backend/app.py -> ../ -> your_project_root
PROJECT_ROOT = os.path.join(os.path.dirname(os.path.abspath(file)), '..')
your_project_root/ -> frontend
FRONTEND_FOLDER_PATH = os.path.join(PROJECT_ROOT, 'frontend')
print(f"Calculated Project Root for static serving: {PROJECT_ROOT}")
print(f"Calculated Frontend folder path for static serving: {FRONTEND_FOLDER_PATH}")
--- Static File Serving Routes ---
이 라우트들이 index.html, styles.css, images 등을 서빙합니다.
@app.route('/')
def serve_index():
"""루트 경로 요청에 index.html 파일 제공"""
# 디버깅: serve_index 함수가 호출되었는지 확인
print("DEBUG: serve_index route called.")
# 디버깅: index.html을 찾을 예상 경로 출력
print(f"DEBUG: Attempting to serve index.html from directory: {FRONTEND_FOLDER_PATH}, filename: index.html")
try:
# index.html 파일은 FRONTEND_FOLDER_PATH 바로 아래에 있다고 가정
# send_from_directory가 FileNotFoundError를 발생시키면 except 블록으로 이동합니다.
# index.html의 MIME 타입은 보통 자동으로 text/html로 잘 감지됩니다.
return send_from_directory(FRONTEND_FOLDER_PATH, 'index.html')
except FileNotFoundError:
# 디버깅: FileNotFoundError가 발생했음을 알림
print(f"ERROR: FileNotFoundError: index.html not found in {FRONTEND_FOLDER_PATH}")
abort(404) # 파일 없으면 404
except Exception as e:
print(f"ERROR: An unexpected error occurred while serving index.html: {e}")
traceback.print_exc()
return "Internal server error serving index.html", 500
@app.route('/path:filename')
def serve_static_files(filename):
"""루트 외 모든 정적 파일 요청 처리 (CSS, JS, Images 등)"""
# 파일명에 '../' 같은 상위 디렉토리 이동 시도가 있는지 체크 (보안)
if '..' in filename or filename.startswith('/'):
print(f"Security alert: Attempted access to suspicious filename: {filename}")
abort(400)
try:
    # send_from_directory 사용: FRONTEND_FOLDER_PATH 디렉토리에서 filename을 찾아서 응답
    # 특정 파일 타입에 대해 MIME 타입을 명시적으로 지정합니다.
    if filename.endswith('.css'):
        print(f"Serving CSS file: {filename} with mimetype text/css")
        return send_from_directory(FRONTEND_FOLDER_PATH, filename, mimetype='text/css')
    elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
         # 이미지 파일에 대해 MIME 타입 명시
         mimetype = 'image/png' if filename.lower().endswith('.png') else \
                    'image/jpeg' if filename.lower().endswith(('.jpg', '.jpeg')) else \
                    'image/gif' if filename.lower().endswith('.gif') else \
                    'image/svg+xml' if filename.lower().endswith('.svg') else 'application/octet-stream' # fallback
         print(f"Serving Image file: {filename} with mimetype {mimetype}")
         return send_from_directory(FRONTEND_FOLDER_PATH, filename, mimetype=mimetype)
    # 그 외 파일들은 send_from_directory의 자동 감지에 맡깁니다.
    else:
        print(f"Serving static file (auto mimetype): {filename}")
        return send_from_directory(FRONTEND_FOLDER_PATH, filename)

except FileNotFoundError:
    print(f"Static file not found: {filename} in {FRONTEND_FOLDER_PATH}")
    abort(404) # 파일 없으면 404
except Exception as e:
    print(f"Error serving static file {filename}: {e}")
    traceback.print_exc()
    return "Internal server error serving static file", 500
Favicon 요청 처리
@app.route('/favicon.ico')
def serve_favicon():
try:
print(f"Serving favicon.ico from {FRONTEND_FOLDER_PATH}")
# Favicon에 대해 MIME 타입 명시
return send_from_directory(FRONTEND_FOLDER_PATH, 'favicon.ico', mimetype='image/x-icon')
except FileNotFoundError:
print(f"favicon.ico not found in {FRONTEND_FOLDER_PATH}")
abort(404)
except Exception as e:
print(f"Error serving favicon.ico: {e}")
traceback.print_exc()
return "Internal server error serving favicon.ico", 500
--- API Routes ---
API 라우트들은 그대로 유지됩니다.
@app.route('/api/schools', methods=['GET'])
def get_schools():
"""모든 학교 데이터를 반환합니다."""
if not schools_data:
print("API: schools_data is empty. Check schools.json loading logs during startup.")
return jsonify([]), 200
print(f"API: Serving {len(schools_data)} schools data.")
return jsonify(schools_data), 200
@app.route('/api/schools/int:school_id/posts', methods=['GET'])
def get_praise_posts(school_id):
"""특정 학교 ID에 대한 칭찬 게시글 목록을 반환합니다."""
school = next((s for s in schools_data if isinstance(s, dict) and s.get('id') == school_id), None)
if not school:
print(f"API: School ID {school_id} not found in schools_data for getting posts.")
return jsonify({"error": "School not found"}), 404
posts = list(praise_posts_data.get(school_id, []))
try:
posts.sort(key=lambda x: x.get('created_at', '0000-00-00T00:00:00Z') if isinstance(x, dict) else '0000-00-00T00:00:00Z', reverse=True)
except Exception as e:
print(f"Error sorting praise posts for school ID {school_id}: {e}")
traceback.print_exc()
print(f"API: Serving {len(posts)} praise posts for school ID {school_id}.")
return jsonify(posts), 200
@app.route('/api/schools/int:school_id/posts', methods=['POST'])
def add_praise_post(school_id):
"""특정 학교에 칭찬 게시글을 추가하고 학교의 포인트/단계를 업데이트합니다."""
global next_praise_post_id
try:
post_data = request.json
if not post_data:
print("API: POST /api/schools/.../posts received no JSON data.")
return jsonify({"error": "Invalid JSON data"}), 400
author = post_data.get('author', '').strip()
content = post_data.get('content', '').strip()
if not content:
print(f"API: POST /api/schools/{school_id}/posts missing content.")
return jsonify({"error": "Content is required"}), 400
school = next((s for s in schools_data if isinstance(s, dict) and s.get('id') == school_id), None)
if not school:
print(f"API: School ID {school_id} not found in schools_data for adding post.")
return jsonify({"error": "School not found"}), 404
points_to_award = 10
new_post = {
"id": next_praise_post_id,
"institution_id": school_id,
"author_info": author if author else "익명",
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
new_stage = current_stage
for stage_check in range(current_stage + 1, MAX_STAGE + 1):
threshold_to_reach_this_stage = stage_thresholds.get(stage_check - 1)
if threshold_to_reach_this_stage is not None and new_points >= threshold_to_reach_this_stage:
new_stage = stage_check
else:
break
school['praise_points'] = new_points
school['tree_growth_stage'] = new_stage
print(f"API: Praise post added for school ID {school_id}. New points: {new_points}, New stage: {new_stage}")
return jsonify({
"message": "Praise post added and points updated in memory",
"post_id": new_post['id'],
"new_points": new_points,
"new_stage": new_stage,
"updated_school": school
}), 201
except Exception as e:
print(f"API: Error adding praise post for school {school_id}: {e}")
traceback.print_exc()
return jsonify({"error": "Failed to add praise post", "details": str(e)}), 500
--- 로컬 개발 서버 실행 (Render 배포 시 Gunicorn 사용으로 이 블록은 실행되지 않음) ---
if name == 'main':
print("Starting Flask local development server...")
port = int(os.environ.get('PORT', 5000))
# Project Root 및 Frontend 폴더 경로는 위에 Static Serving Routes를 위해 계산되어 있습니다.
if not os.path.isdir(FRONTEND_FOLDER_PATH):
     print(f"CRITICAL ERROR: Frontend folder not found at {FRONTEND_FOLDER_PATH}. Check your project structure and ensure it's in the parent directory of the backend folder.")
print(f"Serving static files from absolute path: {FRONTEND_FOLDER_PATH}")
print(f"App running on http://0.0.0.0:{port}")
if not schools_data and 'CRITICAL ERROR' not in globals():
     print("\nWARNING: School data was not loaded successfully (or is empty). API routes might return empty data or errors.")
     print("Please check the schools.json file path and content, and review the logs above this warning for loading details.")
try:
    # Render 배포 시에는 Gunicorn이 app 객체를 실행하며 이 부분은 무시됩니다.
    # 로컬에서 'python app.py'로 실행할 때만 사용됩니다.
    app.run(debug=True, host='0.0.0.0', port=port)
except Exception as e:
    print(f"Flask app.run failed unexpectedly: {e}")
    traceback.print_exc()
