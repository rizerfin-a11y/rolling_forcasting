# backend/app.py
print("--- BOOTING RIZER AI ENGINE ---")
import os
print("Importing Flask...")
from flask import Flask
print("Importing CORS...")
from flask_cors import CORS
print("Importing JWT...")
from flask_jwt_extended import JWTManager
print("Importing Dotenv...")
from dotenv import load_dotenv

load_dotenv()  # loads .env file

app = Flask(__name__)
CORS(app)

# JWT config
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-this')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False  # tokens don't expire for dev
jwt = JWTManager(app)

# ── Register all blueprints ───────────────────────────────────────────────────
from routes.forecast_routes import forecast_bp
app.register_blueprint(forecast_bp)

from routes.data_routes import data_bp
app.register_blueprint(data_bp)

from routes.model_routes import model_bp
app.register_blueprint(model_bp)

from routes.integration_routes import integration_bp
app.register_blueprint(integration_bp)

from flask_route_with_memory import memory_bp
app.register_blueprint(memory_bp)

# ── Root ──────────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return {'message': 'Rizer AI API is Live!', 'endpoints': ['/api/health', '/api/data/live']}

# ── Health check ──────────────────────────────────────────────────────────────
@app.route('/health')
@app.route('/api/health')
def health():
    return {'status': 'ok', 'message': 'Rizer AI backend running'}

# ── Auth routes (basic — replace with Supabase auth later) ───────────────────
from flask_jwt_extended import create_access_token
from flask import request, jsonify

@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    POST /api/auth/login
    Body: {"email": "...", "password": "..."}
    Returns JWT token for testing
    """
    body = request.get_json()
    email = body.get('email', '')
    # In production: verify with Supabase auth
    # For now: any email/password returns a token (dev mode)
    token = create_access_token(identity=f"user_{email.split('@')[0]}")
    return jsonify({'access_token': token, 'user_id': f"user_{email.split('@')[0]}"})

@app.route('/api/auth/register', methods=['POST'])
def register():
    body = request.get_json()
    email = body.get('email', '')
    company_name = body.get('company_name', 'My Business')
    token = create_access_token(identity=f"user_{email.split('@')[0]}")
    return jsonify({
        'access_token': token,
        'user_id': f"user_{email.split('@')[0]}",
        'company_name': company_name,
        'message': 'Account created successfully'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'development') == 'development'
    print(f"\n{'='*50}")
    print(f"  Rizer AI Backend starting on port {port}")
    print(f"  Debug mode: {debug}")
    print(f"  Health check: http://localhost:{port}/health")
    print(f"{'='*50}\n")
    app.run(host='0.0.0.0', port=port, debug=debug)