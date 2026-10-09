from flask import Flask, jsonify

app = Flask(__name__)


@app.get("/")
def home():
    return jsonify(
        service="AI-CI/CD-Demo",
        status="running",
        version="1.0.0"
    )


@app.get("/health")
def health():
    return jsonify(status="healthy")
