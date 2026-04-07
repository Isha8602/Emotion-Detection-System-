from app import app, db
from app import User

with app.app_context():
    db.create_all()
    print("Tables created.")

    # Add default users if none exist
    if User.query.count() == 0:
        agent = User(name="Default Agent", email='agent@example.com', role='agent')
        agent.set_password('agent123')
        supervisor = User(name="Default Supervisor", email='supervisor@example.com', role='supervisor')
        supervisor.set_password('sup456')
        db.session.add(agent)
        db.session.add(supervisor)
        db.session.commit()
        print("Default users added.")
    else:
        print("Users already exist.")