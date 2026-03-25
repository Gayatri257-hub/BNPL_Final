import base64
import os
from datetime import datetime

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user

from extensions import bcrypt, db
from models.kyc import KYCRecord
from models.user import User
from utils.encryption import decrypt_field, encrypt_field, hash_for_lookup

auth_bp = Blueprint('auth', __name__)


# ---------------------------------------------------------------------------
# Signup
# ---------------------------------------------------------------------------

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        monthly_income = request.form.get('monthly_income_range', '')
        city = request.form.get('city', '').strip()
        dob_str = request.form.get('date_of_birth', '')

        # Validations
        if not all([name, email, password, confirm_password]):
            flash('Please fill in all required fields.', 'error')
            return render_template('auth/signup.html')
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('auth/signup.html')
        if len(password) < 8:
            flash('Password must be at least 8 characters.', 'error')
            return render_template('auth/signup.html')

        email_hash = hash_for_lookup(email)
        if User.query.filter_by(email_hash=email_hash).first():
            flash('An account with this email already exists.', 'error')
            return render_template('auth/signup.html')

        dob = None
        if dob_str:
            try:
                dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        new_user = User(
            name_encrypted=encrypt_field(name),
            email_encrypted=encrypt_field(email),
            email_hash=email_hash,
            phone_encrypted=encrypt_field(phone) if phone else None,
            password_hash=bcrypt.generate_password_hash(password).decode('utf-8'),
            monthly_income_range=monthly_income,
            city=city,
            date_of_birth=dob,
        )
        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash('Account created! Please complete KYC verification.', 'success')
        return redirect(url_for('auth.kyc'))

    return render_template('auth/signup.html')


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.home'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        email_hash = hash_for_lookup(email)
        user = User.query.filter_by(email_hash=email_hash).first()

        if not user or not bcrypt.check_password_hash(user.password_hash, password):
            flash('Invalid email or password.', 'error')
            return render_template('auth/login.html')

        if user.is_blacklisted:
            flash('Your account has been suspended. Contact support.', 'error')
            return render_template('auth/login.html')

        user.last_login = datetime.utcnow()
        db.session.commit()
        login_user(user, remember=request.form.get('remember_me') == 'on')

        if user.kyc_status != 'verified':
            return redirect(url_for('auth.kyc'))
        if not user.agreement_signed:
            return redirect(url_for('auth.agreement'))

        return redirect(url_for('dashboard.home'))

    return render_template('auth/login.html')


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


# ---------------------------------------------------------------------------
# KYC
# ---------------------------------------------------------------------------

@auth_bp.route('/kyc', methods=['GET', 'POST'])
@login_required
def kyc():
    if current_user.kyc_status == 'verified' and current_user.agreement_signed:
        return redirect(url_for('dashboard.home'))

    if request.method == 'POST':
        step = request.form.get('step', '1')

        if step == '3':
            # Final KYC submission
            pan = request.form.get('pan_number', '').strip().upper()
            aadhaar_last4 = request.form.get('aadhaar_last4', '').strip()
            liveness_score = float(request.form.get('liveness_score', 0.85))
            face_match_score = float(request.form.get('face_match_score', 0.88))
            deepfake_score = float(request.form.get('deepfake_score', 0.05))

            kyc_record = KYCRecord.query.filter_by(user_id=current_user.id).first()
            if not kyc_record:
                kyc_record = KYCRecord(user_id=current_user.id)
                db.session.add(kyc_record)

            kyc_record.pan_encrypted = encrypt_field(pan) if pan else None
            kyc_record.aadhaar_last4 = aadhaar_last4
            kyc_record.liveness_score = liveness_score
            kyc_record.face_match_score = face_match_score
            kyc_record.deepfake_score = deepfake_score

            if liveness_score > 0.7 and face_match_score > 0.65 and deepfake_score < 0.3:
                kyc_record.verification_status = 'verified'
                kyc_record.verified_at = datetime.utcnow()
                current_user.kyc_status = 'verified'
                db.session.commit()
                flash('KYC verified successfully!', 'success')
                return redirect(url_for('auth.agreement'))
            else:
                kyc_record.verification_status = 'failed'
                current_user.kyc_status = 'failed'
                db.session.commit()
                flash('KYC verification failed. Please try again.', 'error')

    return render_template('auth/kyc.html')


# ---------------------------------------------------------------------------
# Agreement & Digital Signature
# ---------------------------------------------------------------------------

@auth_bp.route('/agreement', methods=['GET', 'POST'])
@login_required
def agreement():
    if current_user.agreement_signed:
        return redirect(url_for('dashboard.home'))

    if request.method == 'POST':
        signature_data = request.form.get('signature_data', '')
        if not signature_data or len(signature_data) < 100:
            flash('Please provide your digital signature.', 'error')
            return render_template('auth/agreement.html')

        # Save signature image
        sig_dir = os.path.join('static', 'uploads', 'signatures')
        os.makedirs(sig_dir, exist_ok=True)
        sig_filename = f'sig_{current_user.id}_{int(datetime.utcnow().timestamp())}.png'
        sig_path = os.path.join(sig_dir, sig_filename)

        try:
            _header, data = signature_data.split(',', 1)
            with open(sig_path, 'wb') as f:
                f.write(base64.b64decode(data))
        except Exception:
            flash('Error saving signature. Please try again.', 'error')
            return render_template('auth/agreement.html')

        current_user.agreement_signed = True
        current_user.agreement_signed_at = datetime.utcnow()
        current_user.digital_signature_path = sig_path
        db.session.commit()

        flash('Agreement signed! Welcome to SmartPay.', 'success')
        return redirect(url_for('dashboard.home'))

    return render_template('auth/agreement.html')
