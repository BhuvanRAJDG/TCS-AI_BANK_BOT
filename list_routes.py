import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, '.')
os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
from app import create_app
app = create_app()
with app.app_context():
    for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
        methods = ','.join(rule.methods - {'OPTIONS','HEAD'})
        print(f'{rule.rule:40s} -> {rule.endpoint:30s} [{methods}]')
