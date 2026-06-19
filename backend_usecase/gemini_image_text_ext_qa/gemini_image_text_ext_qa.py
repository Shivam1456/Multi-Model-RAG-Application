import os
import io
import secrets
import uuid
import tempfile
from flask import Blueprint, request, render_template, flash, session, redirect, url_for
from PIL import Image
from qdrant_client import QdrantClient # type: ignore
from qdrant_client.http.models import Distance, VectorParams, PointStruct # type: ignore
import google.generativeai as genai # type: ignore
import easyocr # type: ignore
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from werkzeug.utils import secure_filename
import re

# Load environment variables
load_dotenv()
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

if not all([GOOGLE_API_KEY, QDRANT_URL, QDRANT_API_KEY]):
    raise ValueError("Missing required environment variables")
genai.configure(api_key=GOOGLE_API_KEY)

# Configuration
CONFIG = {
    "MAX_FILE_SIZE_MB": 10,
    "ALLOWED_EXTENSIONS": {'png', 'jpg', 'jpeg', 'gif'},
    "OCR_TIMEOUT": 30,
    "EMBEDDING_BATCH_SIZE": 50,
    "MAX_CONVERSATION_HISTORY": 5,
}

# Server-side image store (avoids oversized Flask session cookies)
_image_store = {}


def _get_image_session_id():
    if "image_session_id" not in session:
        session["image_session_id"] = secrets.token_hex(16)
    return session["image_session_id"]


def get_uploaded_image_state():
    image_session_id = session.get("image_session_id")
    if not image_session_id:
        return None, None
    stored = _image_store.get(image_session_id)
    if not stored:
        return session.get("uploaded_filename"), None
    return stored.get("filename"), stored.get("text")


def get_uploaded_image_bytes():
    image_session_id = session.get("image_session_id")
    if not image_session_id:
        return None
    stored = _image_store.get(image_session_id)
    return stored.get("image_bytes") if stored else None


def save_uploaded_image_state(filename, text, image_bytes):
    image_session_id = _get_image_session_id()
    _image_store[image_session_id] = {
        "filename": filename,
        "text": text,
        "image_bytes": image_bytes,
    }
    session["uploaded_filename"] = filename
    session["image_ready"] = True
    session.modified = True


def clear_uploaded_image_state():
    image_session_id = session.get("image_session_id")
    if image_session_id and image_session_id in _image_store:
        del _image_store[image_session_id]
    session.pop("uploaded_filename", None)
    session.pop("image_ready", None)
    session.pop("extracted_full_text", None)
    session.modified = True

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

gemini_image_text_ext_qa = Blueprint('gemini_image_text_ext_qa', __name__, template_folder='../templates', static_folder='static')

embedding_model = "models/gemini-embedding-001"
generation_model = genai.GenerativeModel("gemini-2.5-flash")

# Initialize Qdrant client
if QDRANT_URL.startswith(("http://", "https://")):
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, verify=False)
elif QDRANT_URL == ":memory:":
    qdrant_client = QdrantClient(":memory:")
else:
    os.makedirs(QDRANT_URL, exist_ok=True)
    qdrant_client = QdrantClient(path=QDRANT_URL)
collection_name = "image_text_embeddings"
dimension = 768

# Recreate Qdrant collection on each run (no persistence)
if qdrant_client.collection_exists(collection_name):
    qdrant_client.delete_collection(collection_name)
qdrant_client.create_collection(
    collection_name=collection_name,
    vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
)

class OCRManager:
    def __init__(self):
        self.reader = easyocr.Reader(['en'], gpu=False)

    def extract_text(self, image_path, timeout=CONFIG["OCR_TIMEOUT"]):
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.reader.readtext, image_path, detail=1)
                ocr_result = future.result(timeout=timeout)
                text = "\n".join([res[1] for res in ocr_result])
                return text
        except Exception:
            return ""

ocr_manager = OCRManager()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in CONFIG["ALLOWED_EXTENSIONS"]

def chunk_text(text, chunk_size=512):
    if not text.strip():
        return []
    words = text.split()
    chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size - 50)]
    return chunks

def add_chunks_to_qdrant(text_chunks, full_text, batch_size=CONFIG["EMBEDDING_BATCH_SIZE"]):
    if not text_chunks:
        return
    points = []
    for i in range(0, len(text_chunks), batch_size):
        batch = text_chunks[i:i + batch_size]
        response = genai.embed_content(model=embedding_model, content=batch, output_dimensionality=768)
        embeddings = response["embedding"]
        for j, embedding in enumerate(embeddings):
            point_id = str(uuid.uuid4())
            points.append(PointStruct(
                id=point_id,
                vector=embedding,
                payload={"chunk": batch[j], "full_text": full_text},
            ))
    qdrant_client.upsert(collection_name=collection_name, points=points)


def extract_text_from_image(image_path):
    text = ocr_manager.extract_text(image_path)
    if text.strip():
        return text

    try:
        img = Image.open(image_path)
        response = generation_model.generate_content([
            "Extract all visible text and describe all important information in this image. "
            "Include names, labels, numbers, objects, and context.",
            img,
        ])
        return response.text.strip()
    except Exception:
        return ""

def get_relevant_chunks_and_full_text(query, top_k=5):
    try:
        response = genai.embed_content(model=embedding_model, content=query, output_dimensionality=768)
        query_embedding = response['embedding']
        search_result = qdrant_client.query_points(
            collection_name=collection_name,
            query=query_embedding,
            limit=top_k,
        )
        chunks = [hit.payload["chunk"] for hit in search_result.points]
        full_text = search_result.points[0].payload["full_text"] if search_result.points else ""
        return chunks, full_text
    except Exception:
        return [], ""

def clean_response(text):
    text = re.sub(r'\*\*|\*|_', '', text)
    text = re.sub(r'\n\s*\n', '\n', text)
    return text.strip()

def get_conversation_history():
    if 'conversation_history' not in session:
        session['conversation_history'] = []
    return session['conversation_history']

def add_to_conversation_history(question, answer):
    history = get_conversation_history()
    history.append({"question": question, "answer": answer})
    if len(history) > CONFIG["MAX_CONVERSATION_HISTORY"]:
        history = history[-CONFIG["MAX_CONVERSATION_HISTORY"]:]
    session['conversation_history'] = history
    session.modified = True

def format_conversation_history():
    history = get_conversation_history()
    if not history:
        return ""

    formatted = "**Previous Conversation:**\n\n"
    for i, qa in enumerate(history):
        formatted += f"Q{i+1}: {qa['question']}\n"
        formatted += f"A{i+1}: {qa['answer']}\n\n"

    return formatted

def clear_qdrant_data():
    try:
        if qdrant_client.collection_exists(collection_name):
            qdrant_client.delete_collection(collection_name)
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dimension, distance=Distance.COSINE)
            )
        return True
    except Exception:
        return False

@gemini_image_text_ext_qa.route('/gemini_image_text_ext_qa_delete_history', methods=['POST'])
def delete_history():
    session['conversation_history'] = []
    clear_uploaded_image_state()
    session.modified = True

    success = clear_qdrant_data()

    if success:
        flash("History and stored data cleared successfully.", 'success')
    else:
        flash("Failed to clear vector data. Session data cleared.", 'warning')

    return redirect(url_for('gemini_image_text_ext_qa.gemini_image_text_ext_qa_handler'))

@gemini_image_text_ext_qa.route('/gemini_image_text_ext_qa_generate', methods=['GET', 'POST'])
def gemini_image_text_ext_qa_handler():
    answer = None
    uploaded_filename, extracted_text = get_uploaded_image_state()
    conversation_history = get_conversation_history()

    if request.method == 'POST':
        if 'image_files' in request.files:
            session['conversation_history'] = []
            session.modified = True
            clear_uploaded_image_state()
            clear_qdrant_data()

            image_file = request.files['image_files']
            if not image_file or not image_file.filename:
                flash("No file selected.", 'error')
                return render_template('usecase/gemini_image_text_ext_qa/gemini_image_text_ext_qa.html',
                                       CONFIG=CONFIG,
                                       conversation_history=conversation_history,
                                       uploaded_filename=uploaded_filename,
                                       extracted_text=extracted_text)

            filename = secure_filename(image_file.filename)
            if not allowed_file(filename):
                flash("Invalid file type. Allowed: png, jpg, jpeg, gif.", 'error')
                return render_template('usecase/gemini_image_text_ext_qa/gemini_image_text_ext_qa.html',
                                       CONFIG=CONFIG,
                                       conversation_history=conversation_history,
                                       uploaded_filename=uploaded_filename,
                                       extracted_text=extracted_text)

            try:
                image_bytes = image_file.read()
                if not image_bytes:
                    flash("Uploaded file is empty.", 'error')
                    return render_template('usecase/gemini_image_text_ext_qa/gemini_image_text_ext_qa.html',
                                           CONFIG=CONFIG,
                                           conversation_history=conversation_history,
                                           uploaded_filename=uploaded_filename,
                                           extracted_text=extracted_text)

                if len(image_bytes) > CONFIG["MAX_FILE_SIZE_MB"] * 1024 * 1024:
                    flash("File too large.", 'error')
                    return render_template('usecase/gemini_image_text_ext_qa/gemini_image_text_ext_qa.html',
                                           CONFIG=CONFIG,
                                           conversation_history=conversation_history,
                                           uploaded_filename=uploaded_filename,
                                           extracted_text=extracted_text)

                with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}") as temp_file:
                    temp_file.write(image_bytes)
                    image_path = temp_file.name

                text = extract_text_from_image(image_path)
                os.remove(image_path)

                if not text:
                    flash("Could not extract content from the image. Try a clearer image.", 'warning')
                    return render_template('usecase/gemini_image_text_ext_qa/gemini_image_text_ext_qa.html',
                                           CONFIG=CONFIG,
                                           conversation_history=conversation_history,
                                           uploaded_filename=uploaded_filename,
                                           extracted_text=extracted_text)

                save_uploaded_image_state(filename, text, image_bytes)
                text_chunks = chunk_text(text)
                if text_chunks:
                    add_chunks_to_qdrant(text_chunks, text)

                uploaded_filename = filename
                extracted_text = text
                flash(f"Image '{filename}' processed successfully.", 'success')
            except Exception as e:
                flash(f"Failed to process image: {str(e)}", 'error')

        elif 'query' in request.form:
            user_question = request.form.get('user_question')
            if not user_question:
                flash("Please enter a question.", 'error')
            elif not session.get("image_ready") or not extracted_text:
                flash("Please upload an image first.", 'error')
            else:
                full_text = extracted_text
                if not full_text:
                    _, full_text = get_relevant_chunks_and_full_text(user_question)

                if not full_text:
                    answer = "No relevant content found. Please upload an image first."
                    flash("No relevant content found.", 'warning')
                else:
                    conversation_context = format_conversation_history()
                    prompt = (
                        f"You are an expert assistant skilled at interpreting images and extracted text. "
                        f"Answer the user's question using only the image content and extracted text below. "
                        f"If the answer is unclear, say so briefly.\n\n"
                        f"**Extracted Text from Image:**\n{full_text}\n\n"
                        f"{conversation_context}"
                        f"**Current Question:**\n{user_question}\n\n"
                        f"Provide your answer below:"
                    )

                    try:
                        image_bytes = get_uploaded_image_bytes()
                        if image_bytes:
                            img = Image.open(io.BytesIO(image_bytes))
                            response = generation_model.generate_content([prompt, img])
                        else:
                            response = generation_model.generate_content(prompt)

                        answer = clean_response(response.text.strip())
                        add_to_conversation_history(user_question, answer)
                        conversation_history = get_conversation_history()
                        flash("Answer generated successfully.", 'success')
                    except Exception as e:
                        answer = "Could not generate an answer based on the image."
                        flash(f"Error generating answer: {str(e)}", 'error')

    return render_template(
        'usecase/gemini_image_text_ext_qa/gemini_image_text_ext_qa.html',
        answer=answer,
        uploaded_filename=uploaded_filename,
        extracted_text=extracted_text,
        conversation_history=conversation_history,
        CONFIG=CONFIG
    )
