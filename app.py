from flask import Flask, render_template, request, jsonify
import database

app = Flask(__name__)

# Initialize DB on server start
with app.app_context():
    database.init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/todos', methods=['GET'])
def get_todos():
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    priority = request.args.get('priority', '').strip()
    status = request.args.get('status', '').strip()
    
    todos = database.fetch_all_todos(search=search, category=category, priority=priority, status=status)
    return jsonify(todos)

@app.route('/api/todos', methods=['POST'])
def create_todo():
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
        
    description = data.get('description', '').strip()
    category = data.get('category', 'Work').strip()
    priority = data.get('priority', 'Medium').strip()
    due_date = data.get('due_date', '').strip()
    
    todo_id = database.add_todo(
        title=title,
        description=description,
        category=category,
        priority=priority,
        due_date=due_date
    )
    new_todo = database.get_todo_by_id(todo_id)
    return jsonify(new_todo), 201

@app.route('/api/todos/<int:todo_id>', methods=['GET'])
def get_single_todo(todo_id):
    todo = database.get_todo_by_id(todo_id)
    if not todo:
        return jsonify({'error': 'Todo not found'}), 404
    return jsonify(todo)

@app.route('/api/todos/<int:todo_id>', methods=['PUT'])
def update_todo(todo_id):
    data = request.get_json() or {}
    title = data.get('title', '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
        
    description = data.get('description', '').strip()
    category = data.get('category', 'Work').strip()
    priority = data.get('priority', 'Medium').strip()
    due_date = data.get('due_date', '').strip()
    
    success = database.update_todo(
        todo_id=todo_id,
        title=title,
        description=description,
        category=category,
        priority=priority,
        due_date=due_date
    )
    if not success:
        return jsonify({'error': 'Todo not found'}), 404
        
    updated_todo = database.get_todo_by_id(todo_id)
    return jsonify(updated_todo)

@app.route('/api/todos/<int:todo_id>/toggle', methods=['PATCH'])
def toggle_todo(todo_id):
    result = database.toggle_todo(todo_id)
    if result is None:
        return jsonify({'error': 'Todo not found'}), 404
    
    updated_todo = database.get_todo_by_id(todo_id)
    return jsonify(updated_todo)

@app.route('/api/todos/<int:todo_id>', methods=['DELETE'])
def delete_todo(todo_id):
    success = database.delete_todo(todo_id)
    if not success:
        return jsonify({'error': 'Todo not found'}), 404
    return jsonify({'message': 'Deleted successfully', 'id': todo_id})

@app.route('/api/todos/completed', methods=['DELETE'])
def delete_completed():
    count = database.delete_completed_todos()
    return jsonify({'message': f'Deleted {count} completed items', 'deleted_count': count})

@app.route('/api/stats', methods=['GET'])
def get_stats():
    stats = database.get_stats()
    return jsonify(stats)

if __name__ == '__main__':
    print("Starting Task Flow Flask Web Server on http://127.0.0.1:5000...")
    app.run(host='127.0.0.1', port=5000, debug=True)
