from flask import Flask, render_template, request, send_file
import os
import time
from werkzeug.utils import secure_filename
from utils.crypto_utils import encrypt_message, decrypt_message
from utils.stego import encode_image, decode_image

app = Flask(__name__)

# ==============================
# MAX IMAGE SIZE: 10MB
# ==============================
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB limit

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}


# ==============================
# Helper: Validate File Extension
# ==============================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ==============================
# Routes
# ==============================
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/encode")
def encode():
    return render_template("encode.html")


@app.route("/decode")
def decode():
    return render_template("decode.html")


# ==============================
# Encode Action
# ==============================
@app.route("/encode_action", methods=["POST"])
def encode_action():

    image_source = request.form.get("image_source")
    message = request.form.get("message")
    password = request.form.get("password")

    if not image_source or not message or not password:
        return "Missing required fields", 400

    encrypted_data = encrypt_message(message, password)

    # --------------------------------
    # Handle Sample Image
    # --------------------------------
    if image_source == "sample":
        sample_name = request.form.get("sample_img")
        if not sample_name:
            return "No sample selected", 400

        image_path = os.path.join("static", "sample_images", sample_name)

    # --------------------------------
    # Handle Uploaded Image
    # --------------------------------
    else:
        file = request.files.get("image")
        if not file or file.filename == "":
            return "No file uploaded", 400

        if not allowed_file(file.filename):
            return "Only PNG, JPG, JPEG allowed.", 400

        safe_name = secure_filename(file.filename)
        image_path = os.path.join(UPLOAD_FOLDER, safe_name)
        file.save(image_path)

    # --------------------------------
    # Output File
    # --------------------------------
    timestamp = str(int(time.time()))
    filename = f"stego_{timestamp}.png"
    output_path = os.path.join(UPLOAD_FOLDER, filename)

    try:
        encode_image(image_path, encrypted_data, output_path)
    except Exception:
        return "Encoding failed. Try a smaller image.", 400

    return send_file(
        output_path,
        as_attachment=True,
        download_name=filename,
        mimetype="image/png"
    )


# ==============================
# Decode Action
# ==============================
@app.route("/decode_action", methods=["POST"])
def decode_action():

    file = request.files.get("image")
    password = request.form.get("password")

    if not file or not password:
        return "Missing required fields", 400

    if not allowed_file(file.filename):
        return "Only PNG, JPG, JPEG allowed.", 400

    safe_name = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, safe_name)
    file.save(path)

    try:
        encrypted_data = decode_image(path)
        message = decrypt_message(encrypted_data, password)
        return message
    except Exception:
        return "ERROR: Wrong password or corrupted image.", 400


# ==============================
# Important for Local Only
# Render will use Gunicorn
# ==============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)