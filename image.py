from flask import Flask, render_template, request, send_file, session, redirect, url_for
from PIL import Image
import os
import io
import base64
import uuid
import tempfile
import zipfile

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# 임시 저장소 생성
TEMP_DIR = tempfile.mkdtemp()

def split_image(image, rows, cols):
    width, height = image.size
    tile_width = width // cols
    tile_height = height // rows
    tiles = []
    
    for i in range(rows):
        for j in range(cols):
            left = j * tile_width
            upper = i * tile_height
            right = left + tile_width
            lower = upper + tile_height
            
            tile = image.crop((left, upper, right, lower))
            tiles.append(tile)
    
    return tiles

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'image' not in request.files:
            return '이미지를 선택해주세요'
        
        file = request.files['image']
        rows = int(request.form.get('rows', 2))
        cols = int(request.form.get('cols', 2))
        
        # 이미지 열기 및 RGB 모드로 변환
        image = Image.open(file).convert('RGB')
        tiles = split_image(image, rows, cols)
        
        # 세션 ID 생성
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
        
        # 임시 디렉토리 생성
        session_dir = os.path.join(TEMP_DIR, session_id)
        os.makedirs(session_dir, exist_ok=True)
        
        preview_urls = []
        file_paths = []
        
        for i, tile in enumerate(tiles):
            # 이미지를 파일로 저장
            file_path = os.path.join(session_dir, f'tile_{i}.png')
            tile.save(file_path, format='PNG', quality=95)
            file_paths.append(file_path)
            
            # 미리보기용 base64 URL 생성
            with open(file_path, 'rb') as f:
                img_data = f.read()
                img_base64 = base64.b64encode(img_data).decode()
                preview_urls.append(f'data:image/png;base64,{img_base64}')
        
        session['file_paths'] = file_paths
        return render_template('result.html', total_tiles=len(tiles), preview_urls=preview_urls)
    
    return render_template('index.html')

@app.route('/download/<int:tile_index>')
def download_tile(tile_index):
    file_paths = session.get('file_paths', [])
    if 0 <= tile_index < len(file_paths):
        return send_file(
            file_paths[tile_index],
            mimetype='image/png',
            as_attachment=True,
            download_name=f'tile_{tile_index}.png'
        )
    return '잘못된 요청입니다'

@app.route('/download_all')
def download_all():
    file_paths = session.get('file_paths', [])
    if not file_paths:
        return '다운로드할 파일이 없습니다'
    
    # 임시 ZIP 파일 생성
    zip_path = os.path.join(TEMP_DIR, f"{session['session_id']}_all.zip")
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for i, file_path in enumerate(file_paths):
            zipf.write(file_path, f'tile_{i}.png')
    
    return send_file(
        zip_path,
        mimetype='application/zip',
        as_attachment=True,
        download_name='all_tiles.zip'
    )

# 세션이 끝날 때 임시 파일 정리
@app.route('/cleanup')
def cleanup_temp_files():
    session_id = session.get('session_id')
    if session_id:
        session_dir = os.path.join(TEMP_DIR, session_id)
        if os.path.exists(session_dir):
            for file in os.listdir(session_dir):
                os.remove(os.path.join(session_dir, file))
            os.rmdir(session_dir)
        session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
