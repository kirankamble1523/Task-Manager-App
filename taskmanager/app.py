from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Task
from config import Config
from datetime import datetime
import re

app = Flask(__name__)
app.config.from_object(Config)

# Initialize extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def get_greeting():
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Good Morning"
    elif 12 <= hour < 17:
        return "Good Afternoon"
    elif 17 <= hour < 21:
        return "Good Evening"
    else:
        return "Good Night"

def is_password_complex(password):
    """Check if password meets complexity requirements"""
    if len(password) < 8:
        return False
    if not re.search("[a-z]", password):
        return False
    if not re.search("[A-Z]", password):
        return False
    if not re.search("[0-9]", password):
        return False
    return True

# Create tables
with app.app_context():
    db.create_all()

@app.route('/')
@login_required
def dashboard():
    total_tasks = Task.query.filter_by(user_id=current_user.id).count()
    completed_tasks = Task.query.filter_by(user_id=current_user.id, is_completed=True).count()
    pending_tasks = total_tasks - completed_tasks
    greeting = get_greeting()
    
    return render_template('dashboard.html', 
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         pending_tasks=pending_tasks,
                         greeting=greeting)

@app.route('/tasks')
@login_required
def tasks():
    task_list = Task.query.filter_by(user_id=current_user.id).all()
    greeting = get_greeting()
    return render_template('tasks.html', tasks=task_list, greeting=greeting)

@app.route('/add_task', methods=['GET', 'POST'])
@login_required
def add_task():
    greeting = get_greeting()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        category = request.form['category']
        deadline_str = request.form['deadline']
        
        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d') if deadline_str else None
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('add_task'))
        
        task = Task(
            title=title,
            description=description,
            category=category,
            deadline=deadline,
            author=current_user
        )
        
        db.session.add(task)
        db.session.commit()
        flash('Task added successfully!', 'success')
        return redirect(url_for('tasks'))
    
    return render_template('add_task.html', greeting=greeting)

@app.route('/edit_task/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    greeting = get_greeting()
    task = Task.query.get_or_404(task_id)
    
    if task.author != current_user:
        flash('You can only edit your own tasks!', 'danger')
        return redirect(url_for('tasks'))
    
    if request.method == 'POST':
        task.title = request.form['title']
        task.description = request.form['description']
        task.category = request.form['category']
        deadline_str = request.form['deadline']
        
        try:
            task.deadline = datetime.strptime(deadline_str, '%Y-%m-%d') if deadline_str else None
        except ValueError:
            flash('Invalid date format. Please use YYYY-MM-DD.', 'danger')
            return redirect(url_for('edit_task', task_id=task_id))
        
        db.session.commit()
        flash('Task updated successfully!', 'success')
        return redirect(url_for('tasks'))
    
    return render_template('add_task.html', task=task, greeting=greeting)

@app.route('/delete_task/<int:task_id>')
@login_required
def delete_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if task.author != current_user:
        flash('You can only delete your own tasks!', 'danger')
        return redirect(url_for('tasks'))
    
    db.session.delete(task)
    db.session.commit()
    flash('Task deleted successfully!', 'success')
    return redirect(url_for('tasks'))

@app.route('/complete_task/<int:task_id>')
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)
    
    if task.author != current_user:
        flash('You can only complete your own tasks!', 'danger')
        return redirect(url_for('tasks'))
    
    task.is_completed = not task.is_completed
    db.session.commit()
    flash('Task status updated!', 'success')
    return redirect(url_for('tasks'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if not is_password_complex(password):
            flash('Password must be at least 8 characters long and contain uppercase, lowercase, and numbers.', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken. Please choose another.', 'danger')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use another.', 'danger')
            return redirect(url_for('register'))
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)