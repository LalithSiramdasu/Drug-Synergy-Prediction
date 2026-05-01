from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from backend.routes.api_routes import api_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(api_bp)

    @app.errorhandler(HTTPException)
    def handle_http_exception(error):
        return jsonify({"status": "error", "error": error.description}), error.code

    @app.errorhandler(Exception)
    def handle_unexpected_exception(_error):
        return jsonify({"status": "error", "error": "Internal server error."}), 500

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000)
