from functools import wraps
from flask import session, redirect, url_for, abort, flash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            user_role = session.get('role')
            if user_role not in allowed_roles:
                flash('You are not authorized to view that page.', 'danger')
                # Redirect to their corresponding dashboard if they are logged in but unauthorized
                if user_role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user_role == 'security':
                    return redirect(url_for('staff_dashboard'))
                else:
                    return redirect(url_for('student_dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# Role-specific decorators
def admin_required(f):
    return role_required(['admin'])(f)

def staff_required(f):
    return role_required(['admin', 'security'])(f)

def student_required(f):
    return role_required(['admin', 'student'])(f)
