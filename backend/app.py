# --- START OF FILE app.py ---

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
# from pyproj import CRS, Transformer # pyproj 라이브러리는 더 이상 사용하지 않으므로 주석 처리 또는 삭제

app = Flask(__name__, static_folder='../frontend') # static_folder를 frontend 폴더로 지정
CORS(app) # CORS 설정 적용

# !!! 좌표 변환 관련 코드 모두 제거 !!!
# source_crs, target_crs, transformer 관련 정의는 모두 삭제되었습니다.

# 학교 데이터를 로드합니다.
# schools.json 파일에서 데이터를 읽어와 메모리에 저장합니다.
# 좌표 변환은 수행하지 않습니다.
def load_school_data():
    file_path = os.path.join(os.path.dirname(__file__), 'schools.json')
    loaded_schools = [] # 로드된 학교 데이터를 저장할 리스트

    # schools_data 변수에 이미 데이터가 로드되어 있다면 다시 로드하지 않음 (개발 중 편의)
    # 실제 서비스에서는 필요에 따라 캐싱/갱신 로직 구현이 필요할 수 있습니다.
    # if 'schools_data' in globals() and schools_data:
    #     return schools_data

    try:
        # schools.json 파일 읽기
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 각 학교 데이터 처리
        for school in data:
            # 데이터에 latitude와 longitude 필드가 있는지 확인하고 float으로 변환
            if 'latitude' in school and 'longitude' in school:
                try:
                    # 위도/경도 값을 float으로만 변환하고 변환 로직은 수행하지 않습니다.
                    school['latitude'] = float(school['latitude'])
                    school['longitude'] = float(school['longitude'])

                except ValueError as e:
                    # 위도/경도 값이 숫자로 변환되지 않는 경우 오류 메시지 출력
                    print(f"Error converting coordinates format for school {school.get('학교명', 'Unknown')}: {e}")
                    continue # 좌표 변환 실패 시 해당 학교 건너뛰기
                except Exception as e:
                     # 좌표 처리 중 발생하는 예상치 못한 오류
                     print(f"An unexpected error occurred while processing coordinates for school {school.get('학교명', 'Unknown')}: {e}")
                     continue

            else:
                 # latitude 또는 longitude 필드가 없는 경우 경고 출력 및 건너뛰기
                 print(f"Warning: Missing latitude/longitude for school {school.get('학교명', 'Unknown')}")
                 continue # 좌표 없는 학교는 건너뛰기


            # 기본 단계와 포인트 필드 추가 (DB 사용 시에는 DB에서 로드)
            # schools.json 데이터에 이 필드들이 없을 경우 초기값을 설정합니다.
            if 'tree_growth_stage' not in school:
                 school['tree_growth_stage'] = 1 # 기본 단계는 씨앗 (1단계)
            # 단계가 1~7 범위를 벗어나지 않도록 보정 (DB 사용 시 CHECK 제약 조건 활용)
            school['tree_growth_stage'] = max(1, min(7, school['tree_growth_stage']))

            if 'praise_points' not in school:
                 school['praise_points'] = 0 # 기본 포인트는 0

            # 처리된 학교 데이터를 리스트에 추가
            loaded_schools.append(school)

    except FileNotFoundError:
        # schools.json 파일을 찾을 수 없는 경우
        print(f"Error: schools.json not found at {file_path}")
        return [] # 파일이 없으면 빈 리스트 반환
    except json.JSONDecodeError:
        # schools.json 파일의 JSON 형식이 잘못된 경우
        print(f"Error: Could not decode JSON from {file_path}. Check JSON format.")
        return [] # JSON 형식이 잘못되면 빈 리스트 반환
    except Exception as e:
        # 데이터 로딩 또는 처리 중 발생하는 기타 예상치 못한 오류
        print(f"An unexpected error occurred while loading or processing data: {e}")
        return []

    # 성공적으로 로드 및 처리된 학교 수 출력
    print(f"Successfully loaded and processed {len(loaded_schools)} schools from JSON.")
    return loaded_schools # 로드된 데이터 반환

# 애플리케이션 시작 시 schools_data 변수에 데이터 로드
schools_data = load_school_data()

# 루트 경로('/')로 접속하면 frontend의 index.html 파일을 제공하는 라우트
@app.route('/')
def serve_frontend():
    # app.static_folder는 생성자에서 '../frontend'로 설정됨
    return send_from_directory(app.static_folder, 'index.html')

# 학교 데이터 API 엔드포인트 ('/api/schools' 경로에 대한 GET 요청 처리)
@app.route('/api/schools', methods=['GET'])
def get_schools():
    # schools_data 변수에 로드된 학교 데이터를 JSON 형태로 반환
    # 프론트엔드에서 이 API를 호출하여 학교 데이터 (위치, 이름, 단계 등)를 가져갑니다.
    return jsonify(schools_data)

# TODO: 칭찬 게시판 관련 API (특정 학교 칭찬 글 조회, 특정 학교에 칭찬 글 작성 등)는 추후 이 아래에 추가 구현합니다.
# 예:
# @app.route('/api/schools/<school_identifier>/posts', methods=['GET'])
# def get_praise_posts(school_identifier):
#     # school_identifier에 해당하는 학교의 칭찬 글 목록을 DB에서 조회하여 반환하는 로직
#     pass
#
# @app.route('/api/schools/<school_identifier>/posts', methods=['POST'])
# def add_praise_post(school_identifier):
#     # 요청 본문에서 칭찬 글 내용을 받아 DB에 저장하고,
#     # 해당 학교의 칭찬 포인트 및 나무 단계를 업데이트하는 로직
#     pass


# if __name__ == '__main__':
#     # __name__ == '__main__' 일 때 실행되는 코드 블록입니다.
#     # 개발 서버를 실행하는 방식은 'set FLASK_APP=app.py' 환경 변수 설정 후 'flask run --debug' 명령어를 사용하는 것을 권장합니다.
#     # 이 방식은 개발 환경에서 Flask의 디버깅 기능을 더 잘 활용할 수 있게 해줍니다.
#     # 따라서 아래 app.run(...) 코드는 주석 처리하거나 삭제하는 것이 일반적입니다.
#     # app.run(debug=True) # 직접 실행 시 개발 서버 시작 (주석 처리됨)
#     pass # 이 블록에 다른 코드가 없다면 pass를 두거나 블록 전체를 주석 처리/삭제할 수 있습니다.

# --- END OF FILE app.py ---
