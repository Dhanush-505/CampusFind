from flask import Flask, render_template, request, jsonify
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ITEMS'] = []  # Store items in memory

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_items')
def get_items():
    return jsonify(app.config['ITEMS'])

@app.route('/add', methods=['POST'])
def add_item():
    # Get form fields
    name = request.form.get('name')
    roll = request.form.get('roll')
    phone = request.form.get('phone')
    item_name = request.form.get('item')
    description = request.form.get('description')
    file = request.files.get('image')

    filename = None
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

    # Create new item dictionary
    new_item = {
        'id': len(app.config['ITEMS']) + 1,
        'name': name,
        'roll': roll,
        'phone': phone,
        'item': item_name,
        'description': description,
        'image': filename,
        'found': False,
        'Responses': []
    }

    app.config['ITEMS'].append(new_item)
    return jsonify({'status': 'ok'})

@app.route('/mark_found/<int:item_id>', methods=['POST'])
def mark_found(item_id):
    for item in app.config['ITEMS']:
        if item['id'] == item_id:
            item['found'] = True
            break
    return '', 200

@app.route('/add_Response/<int:item_id>', methods=['POST'])
def add_Response(item_id):
    name = request.form.get('name')
    roll = request.form.get('roll')
    phone = request.form.get('phone')
    Response = request.form.get('Response')

    for item in app.config['ITEMS']:
        if item['id'] == item_id:
            item['Responses'].append({
                'name': name,
                'roll': roll,
                'phone': phone,
                'Response': Response
            })
            break
    return '', 200

@app.route('/delete_item/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    app.config['ITEMS'] = [item for item in app.config['ITEMS'] if item['id'] != item_id]
    return '', 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
