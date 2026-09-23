from app import create_app, db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        # Auto-create tables for SQLite local development
        if 'sqlite' in app.config.get('SQLALCHEMY_DATABASE_URI', ''):
            db.create_all()
            print("[SentinelBank] SQLite tables created.")

    # Use Flask built-in server for development; production uses gunicorn (Docker CMD)
    app.run(host='0.0.0.0', port=5000, debug=True)
