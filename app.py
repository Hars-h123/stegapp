from flask import Flask, render_template, request, send_file, jsonify
import os
import uuid
from werkzeug.utils import secure_filename

from utils.crypto_utils import encrypt_message, decrypt_message
from utils.stego import encode_image, decode_image

app = Flask(__name__)

# =============================
# Folder setup
# =============================
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# short link storage
link_map = {}

# =============================
# Helper
# =============================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# =============================
# Pages
# =============================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/encode")
def encode():
    return render_template("encode.html")


@app.route("/decode")
def decode():
    return render_template("decode.html")


# =============================
# Encode action
# =============================
@app.route("/encode_action", methods=["POST"])
def encode_action():

    image_source = request.form.get("image_source")
    message = request.form.get("message")
    password = request.form.get("password")

    if not image_source or not message or not password:
        return jsonify({"error": "Missing required fields"}), 400

    encrypted = encrypt_message(message, password)

    # Sample image
    if image_source == "sample":

        sample = request.form.get("sample_img")

        if not sample:
            return jsonify({"error": "No sample image selected"}), 400

        image_path = os.path.join("static", "sample_images", sample)

    # Uploaded image
    else:

        if "image" not in request.files:
            return jsonify({"error": "No image uploaded"}), 400

        file = request.files["image"]

        if file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        if not allowed_file(file.filename):
            return jsonify({"error": "Invalid file type"}), 400

        filename = secure_filename(file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, filename)

        file.save(image_path)

    # Generate encoded file
    file_id = uuid.uuid4().hex
    short_id = file_id[:6]

    output_filename = f"{file_id}.png"
    output_path = os.path.join(UPLOAD_FOLDER, output_filename)

    # Encode message into image
    encode_image(image_path, encrypted, output_path)

    # Save short link mapping
    link_map[short_id] = output_filename

    # Share URL
    share_url = request.host_url + "s/" + short_id

    return jsonify({
        "share_url": share_url
    })


# =============================
# Decode action (FIXED)
# =============================
@app.route("/decode_action", methods=["POST"])
def decode_action():

    if "image" not in request.files:
        return "No image uploaded", 400

    password = request.form.get("password")

    if not password:
        return "Password required", 400

    file = request.files["image"]

    if file.filename == "":
        return "Empty filename", 400

    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)

    file.save(path)

    try:
        encrypted_data = decode_image(path)
        message = decrypt_message(encrypted_data, password)
        return message

    except Exception:
        return "ERROR: Wrong password or corrupted image.", 400


# =============================
# Short share link
# =============================
@app.route("/s/<short_id>")
def short_redirect(short_id):

    filename = link_map.get(short_id)

    if not filename:
        return "Invalid or expired link", 404

    return render_template("share.html", filename=filename)


# =============================
# Download encoded image
# =============================
@app.route("/download/<filename>")
def download_file(filename):

    path = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(path):
        return "File not found", 404

    return send_file(
        path,
        mimetype="image/png",
        as_attachment=True,
        download_name=filename
    )


# =============================
# Run server
# =============================
if __name__ == "__main__":
    app.run(port=10000, debug=True)