from flask import Flask, request, jsonify
from flask_cors import CORS
from scraper.product_details import obtener_producto_original

app = Flask(__name__)
CORS(app)

@app.route("/scraper_original", methods=["POST"])
def scraper_original():
    data = request.get_json()
    url = data.get("url")

    if not url:
        return jsonify({"error": "URL es requerida"}), 400

    producto = obtener_producto_original(url)
    if not producto:
        return jsonify({"error": "No se pudo obtener el producto"}), 404

    return jsonify(producto)

if __name__ == "__main__":
    app.run(debug=True)
