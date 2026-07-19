from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
import os
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db
from auth import login_required, admin_required, staff_required, student_required, role_required

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = Config.UPLOAD_FOLDER
app.secret_key = Config.SECRET_KEY

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Redirect according to role
    role = session.get('role')
    if role == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif role == 'security':
        return redirect(url_for('staff_dashboard'))
    else:
        return redirect(url_for('student_dashboard'))

# Dashboard Routes
@app.route('/dashboard')
@student_required
def student_dashboard():
    return render_template('index.html')

@app.route('/staff-dashboard')
@staff_required
def staff_dashboard():
    return render_template('index.html')

@app.route('/admin-dashboard')
@admin_required
def admin_dashboard():
    return render_template('index.html')

# Items APIs
@app.route('/get_items')
@login_required
def get_items():
    current_user_id = session.get('user_id')
    return jsonify(db.get_all_items(current_user_id=current_user_id))

@app.route('/add', methods=['POST'])
@login_required
def add_item():
    item_name = request.form.get('item')
    description = request.form.get('description')
    file = request.files.get('image')
    item_type = request.form.get('type', 'Lost')
    category = request.form.get('category')
    location = request.form.get('location')
    date = request.form.get('date')

    filename = None
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

    # Use session variables for creator info to prevent impersonation
    creator_id = session['user_id']
    creator_name = session['name']
    creator_roll = session['roll_number']
    creator_phone = session['phone']
    creator_email = session.get('email', '')

    db.add_item(
        creator_id=creator_id,
        creator_name=creator_name,
        creator_roll=creator_roll,
        creator_phone=creator_phone,
        item_name=item_name,
        description=description,
        filename=filename,
        item_type=item_type,
        category=category,
        location=location,
        date=date,
        creator_email=creator_email
    )
    return jsonify({'status': 'ok'})

@app.route('/mark_found/<item_id>', methods=['POST'])
@login_required
def mark_found(item_id):
    current_user_id = str(session.get('user_id'))
    item = db.get_item_by_id(item_id, current_user_id=current_user_id)
    if not item:
        return 'Item not found', 404
        
    # Check permissions: Only creator/owner of the post can mark it as found
    item_owner_id = str(item.get('creator_id') or item.get('owner_id'))

    if current_user_id == item_owner_id:
        db.mark_item_found(item_id)
        return '', 200
    return 'Unauthorized', 403

@app.route('/add_Response/<item_id>', methods=['POST'])
@login_required
def add_Response(item_id):
    Response_text = request.form.get('Response') or request.form.get('message')
    if not Response_text:
        return 'Response message required', 400
    
    # Use session variables for responder identity
    responder_id = session['user_id']
    responder_name = session['name']
    responder_role = session.get('role', 'student')
    responder_roll = session['roll_number']
    responder_phone = session['phone']

    db.add_response(
        item_id=item_id,
        responder_id=responder_id,
        responder_name=responder_name,
        responder_role=responder_role,
        responder_roll=responder_roll,
        responder_phone=responder_phone,
        message=Response_text
    )
    return '', 200

@app.route('/delete_item/<item_id>', methods=['POST'])
@login_required
def delete_item(item_id):
    current_user_id = str(session.get('user_id'))
    item = db.get_item_by_id(item_id, current_user_id=current_user_id)
    if not item:
        return 'Item not found', 404
        
    # Check permissions: Only creator/owner of the post can delete it
    item_owner_id = str(item.get('creator_id') or item.get('owner_id'))

    if current_user_id == item_owner_id:
        db.delete_item(item_id)
        return '', 200
    return 'Unauthorized', 403

@app.route('/edit_item/<item_id>', methods=['POST'])
@login_required
def edit_item(item_id):
    current_user_id = str(session.get('user_id'))
    item = db.get_item_by_id(item_id, current_user_id=current_user_id)
    if not item:
        return 'Item not found', 404
        
    # Check permissions: Only creator/owner of the post can edit it
    item_owner_id = str(item.get('creator_id') or item.get('owner_id'))

    if current_user_id != item_owner_id:
        return 'Unauthorized', 403

    item_name = request.form.get('item')
    description = request.form.get('description')
    location = request.form.get('location')
    category = request.form.get('category')
    file = request.files.get('image')

    filename = None
    if file and file.filename != '':
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

    db.update_item(
        item_id=item_id,
        item_name=item_name,
        description=description,
        location=location,
        category=category,
        filename=filename
    )
    return jsonify({'status': 'ok'})

# Registration & Login routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        roll_number = request.form.get('roll_number')
        email = request.form.get('email')
        phone = request.form.get('phone')
        role = request.form.get('role')
        password = request.form.get('password')
        
        # Validations
        if not (name and roll_number and email and phone and role and password):
            flash('All fields are required.', 'danger')
            return render_template('register.html')
            
        if role not in ['student', 'security']:
            flash('Invalid role selected.', 'danger')
            return render_template('register.html')
            
        if db.check_duplicate_email(email):
            flash('Email address is already registered.', 'danger')
            return render_template('register.html')
            
        if db.check_duplicate_roll(roll_number):
            flash('Roll Number / Employee ID is already registered.', 'danger')
            return render_template('register.html')
            
        # Hash password and create user
        password_hash = generate_password_hash(password)
        db.create_user(
            name=name,
            roll_number=roll_number,
            email=email,
            phone=phone,
            password_hash=password_hash,
            role=role
        )
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember_me = request.form.get('remember_me')
        
        user = db.get_user_by_email(email)
        
        if user and check_password_hash(user.password_hash, password):
            session.clear()
            session['user_id'] = str(user.id)
            session['role'] = user.role
            session['name'] = user.name
            session['email'] = user.email
            session['roll_number'] = user.roll_number
            session['phone'] = user.phone
            
            if remember_me:
                session.permanent = True
                
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Invalid email or password.', 'danger')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have logged out successfully.', 'success')
    return redirect(url_for('login'))

# Profile & Password Update routes
@app.route('/profile')
@login_required
def profile():
    user = db.get_user_by_id(session['user_id'])
    return render_template('profile.html', user=user)

@app.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    
    user = db.get_user_by_id(session['user_id'])
    
    if not (current_password and new_password):
        flash('All fields are required.', 'danger')
        return redirect(url_for('profile'))
        
    if not user or not check_password_hash(user.password_hash, current_password):
        flash('Incorrect current password.', 'danger')
        return redirect(url_for('profile'))
        
    if len(new_password) < 6:
        flash('New password must be at least 6 characters long.', 'danger')
        return redirect(url_for('profile'))
        
    # Update password hash in MongoDB
    new_hash = generate_password_hash(new_password)
    db.update_user_password(user.id, new_hash)
    flash('Password changed successfully!', 'success')
    return redirect(url_for('profile'))

# Forgot Password route (Dev-mode verification)
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if 'user_id' in session:
        return redirect(url_for('home'))
        
    step = 1
    email = None
    
    if request.method == 'POST':
        form_step = request.form.get('step')
        
        if form_step == '1':
            email = request.form.get('email')
            user = db.get_user_by_email(email)
            if user:
                step = 2
            else:
                flash('No account found with that email address.', 'danger')
        elif form_step == '2':
            email = request.form.get('email')
            new_password = request.form.get('password')
            user = db.get_user_by_email(email)
            
            if user and new_password:
                new_hash = generate_password_hash(new_password)
                db.update_user_password(user.id, new_hash)
                flash('Password reset successful! Please log in.', 'success')
                return redirect(url_for('login'))
            else:
                flash('An error occurred during password reset.', 'danger')
                
    return render_template('forgot_password.html', step=step, email=email)

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
