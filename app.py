from flask import Flask, send_file, send_from_directory
from config import config
from extensions import db, migrate, mail
import os
import logging
import threading
import time
from services.backup_manager import create_backup
from werkzeug.utils import secure_filename
from datetime import datetime
import cloudinary  # NEW: Cloudinary SDK for cloud uploads

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # =========================
    # CLOUDINARY CONFIG - NEW
    # =========================
    # Cloudinary handles file storage so uploads don't get deleted on Render deploys
    cloudinary.config(
        cloud_name=os.environ.get('CLOUDINARY_CLOUD_NAME'),
        api_key=os.environ.get('CLOUDINARY_API_KEY'),
        api_secret=os.environ.get('CLOUDINARY_API_SECRET')
    )

    # =========================
    # DATABASE CONFIG
    # =========================
    # Fix Render PostgreSQL URL to use psycopg2 driver
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    if db_url and db_url.startswith("postgresql://"):
        app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

    # =========================
    # UPLOAD FOLDER CONFIG - DEPRECATED
    # =========================
    # Local upload folder removed. Cloudinary is used instead for persistent storage.
    # UPLOAD_FOLDER = 'C:/okoya_uploads'
    # app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    # os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    # Keeping comments above to maintain line count and show what was removed

    db.init_app(app)
    migrate.init_app(app, db)
    mail.init_app(app)

    logging.basicConfig(level=logging.INFO)

    # =========================
    # REGISTER BLUEPRINTS
    # =========================
    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.secretary import secretary_bp
    from routes.workers import workers_bp
    from routes.attendance import attendance_bp
    from routes.salary import salary_bp
    from routes.orders import orders_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(secretary_bp)
    app.register_blueprint(workers_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(salary_bp)
    app.register_blueprint(orders_bp)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    @app.errorhandler(Exception)
    def handle_exception(e):
        import traceback
        traceback.print_exc()
        return f"<pre>{traceback.format_exc()}</pre>", 500

    @app.route('/health')
    def health():
        return "OK", 200

    @app.route('/routes')
    def routes():
        return "<br>".join(sorted(str(r) for r in app.url_map.iter_rules()))

    @app.route('/favicon.ico')
    def favicon():
        return "", 204

    @app.route('/smtp-test')
    def smtp_test():
        from flask_mail import Message
        try:
            msg = Message(
                subject="Test Email",
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=[app.config['MAIL_USERNAME']],
                body="SMTP is working"
            )
            mail.send(msg)
            return "EMAIL SENT OK"
        except Exception as e:
            import traceback
            return f"<pre>{traceback.format_exc()}</pre>"

    @app.route('/mail-debug-test')
    def mail_debug_test():
        from flask_mail import Message
        try:
            msg = Message(
                subject="TEST",
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=[app.config['MAIL_DEFAULT_SENDER']],
                body="Test email"
            )
            mail.send(msg)
            return "MAIL SENT"
        except Exception as e:
            return str(e)

    @app.route('/check-cloud')
    def check_cloud():
        # Endpoint to verify Cloudinary env vars are loaded on Render
        return {
            "cloud_name": os.environ.get('CLOUDINARY_CLOUD_NAME'),
            "api_key_set": bool(os.environ.get('CLOUDINARY_API_KEY')),
            "api_secret_set": bool(os.environ.get('CLOUDINARY_API_SECRET'))
        }

    @app.route("/mail-test")
    def mail_test():
        from flask_mail import Message
        try:
            print("STARTING EMAIL TEST")
            msg = Message(
                subject="Okoya SMTP Test",
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=["wismailadewale@gmail.com"],
                body="Brevo SMTP is now working from Render."
            )
            print("MESSAGE CREATED")
            mail.send(msg)
            print("EMAIL SENT SUCCESSFULLY")
            return "MAIL SENT SUCCESSFULLY"
        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"<pre>{traceback.format_exc()}</pre>"

    # =========================
    # ROUTE TO SERVE UPLOADED FILES - DEPRECATED
    # =========================
    # Local file serving removed. Cloudinary serves files directly via CDN.
    # @app.route('/uploads/<filename>')
    # def uploaded_file(filename):
    #     return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    # Keeping commented code to maintain structure and line count

    # =========================
    # AUTO BACKUP LOOP
    # =========================
    # Don't start backup during migrations or on Render
    import sys
    if os.environ.get("RENDER") != "true" and 'db' not in sys.argv:
        threading.Thread(target=auto_backup_loop, args=(app,), daemon=True).start()

    return app

def auto_backup_loop(app):
    # Background thread for automatic database backups
    with app.app_context():
        while True:
            try:
                print("Running auto backup...")
                create_backup(app.config['SQLALCHEMY_DATABASE_URI'])
                print("Backup completed")
            except Exception as e:
                print("Backup error:", e)
            time.sleep(86400)  # Sleep for 24 hours

app = create_app(os.getenv('FLASK_ENV', 'default'))

if __name__ == '__main__':
    print("🚀 Okoya Food Staff Manager app is starting...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)