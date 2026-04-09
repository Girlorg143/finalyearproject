import os
import sys
from pathlib import Path

# Load environment variables FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()  # MUST be before importing anything that uses env vars

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

try:
    from flask import Flask, jsonify, render_template
    from flask_cors import CORS
    from sqlalchemy import text
    from backend.extensions import db, migrate, bcrypt, jwt
    from backend.config import Config
    from backend.routes.auth import auth_bp
    from backend.routes.dashboards import dashboards_bp
    from backend.routes.farmer import farmer_bp
    from backend.routes.warehouse import warehouse_bp
    from backend.routes.logistics import logistics_bp
    from backend.routes.admin import admin_bp
except Exception:
    import traceback

    try:
        sys.stderr.write("[startup] Import-time failure in backend/app.py. Traceback:\n")
        sys.stderr.flush()
    except Exception:
        pass
    traceback.print_exc(file=sys.stderr)
    try:
        sys.stderr.flush()
    except Exception:
        pass
    raise

def create_app():
    # Determine paths based on environment
    base_dir = Path(__file__).resolve().parent.parent
    static_folder = base_dir / "frontend" / "static"
    template_folder = base_dir / "frontend" / "templates"
    
    app = Flask(__name__, 
                static_folder=str(static_folder),
                template_folder=str(template_folder))
    # Load defaults from Config then force DB URI from env AFTER dotenv has loaded
    app.config.from_object(Config())

    # STEP 1: Database Configuration
    db_uri = os.getenv("DATABASE_URL", "sqlite:///finalyear.db")
    print(f"🔍 Raw DATABASE_URL from env: {os.getenv('DATABASE_URL', 'NOT SET (using default)')}")
    
    # STEP 2: Handle SQLite-specific path logic
    if db_uri.startswith("sqlite:///"):
        if not db_uri.startswith("sqlite:////"):
            rel = db_uri[len("sqlite:///") :]
            if rel and not os.path.isabs(rel):
                project_root = Path(__file__).resolve().parents[1]
                db_path = project_root / rel
                db_path.parent.mkdir(parents=True, exist_ok=True)
                db_uri = f"sqlite:///{db_path.as_posix()}"
        
        # SQLite engine options (check_same_thread)
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"check_same_thread": False}}
        print(f"✅ Using SQLite: {db_uri}")
    else:
        # PostgreSQL or other database - use URI as-is
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}
        print(f"✅ Using PostgreSQL: {db_uri}")
    
    app.config["SQLALCHEMY_DATABASE_URI"] = db_uri

    CORS(app, supports_credentials=True)

    db.init_app(app)
    migrate.init_app(app, db)
    bcrypt.init_app(app)
    jwt.init_app(app)

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(dashboards_bp, url_prefix="/")
    app.register_blueprint(farmer_bp, url_prefix="/api/farmer")
    app.register_blueprint(warehouse_bp, url_prefix="/api/warehouse")
    app.register_blueprint(logistics_bp, url_prefix="/api/logistics")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    # STEP 4: Ensure Tables Are Created Before Login
    with app.app_context():
        try:
            # Create database directory only for SQLite
            db_uri = app.config["SQLALCHEMY_DATABASE_URI"]
            if db_uri.startswith("sqlite:///"):
                db_path = Path(db_uri.replace("sqlite:///", ""))
                db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create all tables
            db.create_all()
            print("✅ Database initialized successfully")
            
            # Create default roles if they don't exist
            from backend.models import Role, User
            if not Role.query.filter_by(name="farmer").first():
                farmer_role = Role(name="farmer")
                db.session.add(farmer_role)
                print("✅ Created farmer role")
            
            if not Role.query.filter_by(name="warehouse").first():
                warehouse_role = Role(name="warehouse")
                db.session.add(warehouse_role)
                print("✅ Created warehouse role")
            
            if not Role.query.filter_by(name="admin").first():
                admin_role = Role(name="admin")
                db.session.add(admin_role)
                print("✅ Created admin role")
            
            db.session.commit()
            print("✅ Database setup completed")

        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            db.session.rollback()
            # Continue anyway - let individual endpoints handle database errors

    @app.route("/")
    def index():
        return render_template("login.html")

    @app.route("/login")
    def login():
        return render_template("login.html")

    @app.route("/signup")
    def signup():
        return render_template("signup.html")

    @app.route("/forgot-password")
    def forgot_password():
        return render_template("forgot-password.html")

    @app.route("/logistics")
    def logistics_page_direct():
        return render_template("logistics.html")

    @app.route("/api/health")
    def health():
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        # mask credentials in URI for safety
        safe_uri = uri
        if "@" in uri and "://" in uri:
            try:
                scheme, rest = uri.split("://", 1)
                creds, host = rest.split("@", 1)
                safe_uri = f"{scheme}://***:***@{host}"
            except Exception:
                safe_uri = uri
        backend = "sqlite" if uri.startswith("sqlite") else ("postgresql" if "postgresql" in uri else "other")
        return jsonify({"status": "ok", "db_backend": backend, "db_uri": safe_uri})

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
