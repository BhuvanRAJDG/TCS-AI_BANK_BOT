from app import create_app, db
from app.models import User

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        print("[SentinelBank] Database schema verified & ready.")

        # If database is fresh/empty, auto-seed with demo accounts
        try:
            if User.query.count() == 0:
                print("[SentinelBank] Empty database detected. Auto-seeding demo records...")
                from seed.seed_database import seed
                seed()
                print("[SentinelBank] Demo records seeded successfully.")
        except Exception as se:
            print(f"[SentinelBank] Note on seeding: {se}")

    print("[SentinelBank] Starting Server on http://0.0.0.0:5000 (Access at http://127.0.0.1:5000)")
    app.run(host='0.0.0.0', port=5000, debug=True)