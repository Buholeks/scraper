from flask import Flask, request, jsonify
from flask_cors import CORS
from scraper_original import scrape_single_product
import traceback

app = Flask(__name__)
CORS(app)

@app.route("/scraper_original", methods=["POST"])
def scrape_product():
    try:
        data = request.get_json()
        url = data.get("url")
        
        if not url:
            return jsonify({"status": "error", "message": "URL requerida"}), 400
        
        result = scrape_single_product(url)
        return jsonify(result)
        
    except Exception as e:
        traceback.print_exc()
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)