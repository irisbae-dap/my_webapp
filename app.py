from flask import Flask, render_template, request, jsonify

import database

app = Flask(__name__)

with app.app_context():
    database.init_db()
    database.seed_sample_data()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analytics', methods=['GET'])
def analytics():
    try:
        days = int(request.args.get('days', 30))
    except (TypeError, ValueError):
        days = 30
    return jsonify(database.get_analytics(days=days))


@app.route('/api/items', methods=['GET'])
def list_items():
    items = database.fetch_items(
        search=request.args.get('search', '').strip(),
        item_type=request.args.get('type', '').strip(),
        status=request.args.get('status', '').strip(),
        coach=request.args.get('coach', '').strip(),
        days=request.args.get('days', 30),
    )
    return jsonify(items)


@app.route('/api/items', methods=['POST'])
def create_item():
    data = request.get_json() or {}
    term = (data.get('term') or '').strip()
    if not term:
        return jsonify({'error': 'term is required'}), 400

    item_id = database.add_item(
        term=term,
        meaning=(data.get('meaning') or '').strip(),
        example=(data.get('example') or '').strip(),
        item_type=(data.get('item_type') or 'vocab').strip(),
        coach=(data.get('coach') or '').strip(),
        status=(data.get('status') or 'new').strip(),
        tags=(data.get('tags') or '').strip(),
        source_date=(data.get('source_date') or '').strip(),
    )
    return jsonify(database.get_item(item_id)), 201


@app.route('/api/items/<int:item_id>/status', methods=['PATCH'])
def update_status(item_id):
    data = request.get_json() or {}
    status = (data.get('status') or '').strip()
    if status not in database.STATUSES:
        return jsonify({'error': f'status must be one of {database.STATUSES}'}), 400

    if not database.set_status(item_id, status):
        return jsonify({'error': 'Item not found'}), 404
    return jsonify(database.get_item(item_id))


@app.route('/api/items/<int:item_id>', methods=['DELETE'])
def remove_item(item_id):
    if not database.delete_item(item_id):
        return jsonify({'error': 'Item not found'}), 404
    return jsonify({'message': 'deleted', 'id': item_id})


@app.route('/api/sessions', methods=['GET'])
def list_sessions():
    return jsonify(database.fetch_sessions(days=request.args.get('days', 30)))


@app.route('/api/import', methods=['POST'])
def import_data():
    """실제 코칭 기록을 한 번에 적재한다. 기본적으로 샘플 데이터를 먼저 비운다."""
    payload = request.get_json() or {}
    if not isinstance(payload.get('items'), list):
        return jsonify({'error': 'items must be a list'}), 400

    count = database.import_payload(payload)
    return jsonify({'imported': count, 'message': f'{count}개 항목을 적재했습니다.'})


@app.route('/api/sample', methods=['DELETE'])
def drop_sample():
    return jsonify({'removed': database.clear_sample_data()})


if __name__ == '__main__':
    print('Stepping Stones dashboard on http://127.0.0.1:5000 ...')
    app.run(host='127.0.0.1', port=5000, debug=True)
