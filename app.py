import os

from flask import Flask, render_template, request, jsonify

import database

app = Flask(__name__)

with app.app_context():
    database.init_db()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/overview', methods=['GET'])
def overview():
    days = request.args.get('days', '').strip()
    try:
        days = int(days) if days else None
    except ValueError:
        days = None
    return jsonify(database.get_overview(days=days))


@app.route('/api/sessions', methods=['GET'])
def sessions():
    days = request.args.get('days', '').strip()
    try:
        days = int(days) if days else None
    except ValueError:
        days = None
    return jsonify(database.fetch_sessions(days=days))


@app.route('/api/study', methods=['GET'])
def study():
    return jsonify(database.fetch_study_items(
        status=request.args.get('status', '').strip(),
        category=request.args.get('category', '').strip(),
        search=request.args.get('search', '').strip(),
    ))


@app.route('/api/study/<int:item_id>/status', methods=['PATCH'])
def study_status(item_id):
    data = request.get_json() or {}
    status = (data.get('status') or '').strip()
    if status not in database.STATUSES:
        return jsonify({'error': f'status must be one of {database.STATUSES}'}), 400
    if not database.set_study_status(item_id, status):
        return jsonify({'error': 'Item not found'}), 404
    return jsonify(database.get_study_item(item_id))


@app.route('/api/load', methods=['POST'])
def load():
    """추출기가 만든 데이터셋을 통째로 적재한다."""
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload.get('sessions'), list):
        return jsonify({'error': 'sessions must be a list'}), 400
    return jsonify(database.load_dataset(payload, replace=payload.get('replace', True)))


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f'Stepping Stones dashboard on http://127.0.0.1:{port} ...')
    app.run(host='127.0.0.1', port=port, debug=True)
