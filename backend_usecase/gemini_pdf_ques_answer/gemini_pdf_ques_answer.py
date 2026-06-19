import os
import secrets
import tempfile
from flask import Blueprint, request, render_template, flash, session, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge
import fitz  # type: ignore # PyMuPDF
import google.generativeai as genai  # type: ignore
import easyocr # type: ignore
from dotenv import load_dotenv
from qdrant_client import QdrantClient  # type: ignore
from qdrant_client.http import models  # type: ignore
import uuid
import io
from PIL import Image

# Load environment variables
load_dotenv()
API_KEY = os.getenv('GOOGLE_API_KEY')
QDRANT_URL = os.getenv('QDRANT_URL')
QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')

if not API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables")
if not QDRANT_URL:
    raise ValueError("QDRANT_URL not found in environment variables")
if not QDRANT_API_KEY:
    raise ValueError("QDRANT_API_KEY not found in environment variables")

genai.configure(api_key=API_KEY)

# Initialize Blueprint
gemini_pdf_ques_answer = Blueprint('gemini_pdf_ques_answer', __name__, template_folder='../templates')

# Initialize Qdrant client (synchronous)
if QDRANT_URL.startswith(("http://", "https://")):
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, verify=False)
elif QDRANT_URL == ":memory:":
    qdrant_client = QdrantClient(":memory:")
else:
    os.makedirs(QDRANT_URL, exist_ok=True)
    qdrant_client = QdrantClient(path=QDRANT_URL)
COLLECTION_NAME = "pdf_chunks"

# Initialize EasyOCR reader with lazy loading
ocr_reader = None
def get_ocr_reader():
    global ocr_reader
    if ocr_reader is None:
        ocr_reader = easyocr.Reader(['en'])
    return ocr_reader

embedding_model = "models/gemini-embedding-001"
generation_model = genai.GenerativeModel("gemini-2.5-flash")

# Configuration
MAX_CONVERSATION_HISTORY = 5  # Limit for Q&A pairs in history
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Server-side PDF store (avoids oversized Flask session cookies)
_pdf_store = {}


def _get_pdf_session_id():
    if "pdf_session_id" not in session:
        session["pdf_session_id"] = secrets.token_hex(16)
    return session["pdf_session_id"]


def get_uploaded_pdf_state():
    pdf_session_id = session.get("pdf_session_id")
    if not pdf_session_id:
        return None, None
    stored = _pdf_store.get(pdf_session_id)
    if not stored:
        return session.get("uploaded_filename"), None
    return stored.get("filename"), stored.get("text")


def save_uploaded_pdf_state(filename, text):
    pdf_session_id = _get_pdf_session_id()
    _pdf_store[pdf_session_id] = {"filename": filename, "text": text}
    session["uploaded_filename"] = filename
    session["pdf_ready"] = True
    session.modified = True

# Initialize Qdrant collection only once at startup
def initialize_qdrant_collection():
    try:
        if qdrant_client.collection_exists(COLLECTION_NAME):
            qdrant_client.delete_collection(COLLECTION_NAME)
        qdrant_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
        )
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Qdrant collection: {str(e)}")

# Call initialization once at module load
initialize_qdrant_collection()

def extract_text_from_pdf(pdf_stream, filename):
    try:
        if not pdf_stream or len(pdf_stream) == 0:
            raise ValueError("PDF stream is empty or invalid.")
        with fitz.open(stream=pdf_stream, filetype="pdf") as pdf:
            selectable_text = ""
            for page in pdf:
                selectable_text += page.get_text()
            if selectable_text.strip():
                return selectable_text, "non-scanned"
            else:
                text = extract_text_with_easyocr(pdf, filename)
                return text, "scanned"
    except Exception as e:
        raise ValueError(f"Invalid PDF file: {str(e)}")

def extract_text_with_easyocr(pdf_doc, filename):
    text = ""
    ocr = get_ocr_reader()
    for page_num in range(len(pdf_doc)):
        pix = pdf_doc[page_num].get_pixmap(dpi=300)
        img_bytes = pix.tobytes("png")
        ocr_result = ocr.readtext(img_bytes)
        text += " ".join([result[1] for result in ocr_result]) + " "
    return text.strip()

def chunk_text(text, chunk_size=512):
    words = text.split()
    chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size - 50)]
    return chunks

def add_chunks_to_qdrant(text_chunks, full_text):
    points = []
    for chunk in text_chunks:
        try:
            response = genai.embed_content(model=embedding_model, content=chunk, output_dimensionality=768)
            if 'embedding' not in response:
                raise ValueError("Embedding generation failed")
            embedding = response['embedding']
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={"text": chunk, "full_text": full_text}
                )
            )
        except Exception as e:
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")

    qdrant_client.upsert(collection_name=COLLECTION_NAME, points=points)

def get_relevant_chunks_and_full_text(query, top_k=5):
    try:
        response = genai.embed_content(model=embedding_model, content=query, output_dimensionality=768)
        if 'embedding' not in response:
            response = genai.embed_content(model=embedding_model, content=query, output_dimensionality=768)
        query_embedding = response['embedding']

        search_result = qdrant_client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_embedding,
            limit=top_k,
        )
        if not search_result.points:
            return [], ""
        chunks = [hit.payload["text"] for hit in search_result.points]
        full_text = search_result.points[0].payload["full_text"]
        return chunks, full_text
    except Exception as e:
        raise RuntimeError(f"Failed to retrieve from Qdrant: {str(e)}")

def allowed_file(filename):
    return filename.lower().endswith('.pdf')

def get_conversation_history():
    if 'conversation_history' not in session:
        session['conversation_history'] = []
    return session['conversation_history']

def add_to_conversation_history(question, answer):
    history = get_conversation_history()
    history.append({"question": question, "answer": answer})
    if len(history) > MAX_CONVERSATION_HISTORY:
        history = history[-MAX_CONVERSATION_HISTORY:]
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

# Error handler for file size limit
@gemini_pdf_ques_answer.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(error):
    flash("File is too large. Maximum allowed size is 50MB.", 'error')
    return redirect(url_for('gemini_pdf_ques_answer.gemini_pdf_ques_answer_generate'))

@gemini_pdf_ques_answer.route('/gemini_pdf_ques_answer_generate', methods=['GET', 'POST'])
def gemini_pdf_ques_answer_generate():
    answer = None
    uploaded_filename, extracted_text = get_uploaded_pdf_state()
    conversation_history = get_conversation_history()

    if request.method == 'POST':
        if 'pdf_file' in request.files:
            pdf_file = request.files.get('pdf_file')
            if not pdf_file or not pdf_file.filename:
                flash("No file selected.", 'error')
                return render_template('usecase/gemini_pdf_ques_answer/gemini_pdf_ques_answer.html',
                                       conversation_history=conversation_history)

            filename = secure_filename(pdf_file.filename)
            if not allowed_file(filename):
                flash("Invalid file type. Only PDF files are allowed.", 'error')
                return render_template('usecase/gemini_pdf_ques_answer/gemini_pdf_ques_answer.html',
                                       conversation_history=conversation_history)

            try:
                # Save file to a temporary location
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                    pdf_file.save(temp_file.name)
                    temp_file_path = temp_file.name

                # Process the PDF from disk
                with open(temp_file_path, 'rb') as f:
                    pdf_stream = f.read()

                if not pdf_stream:
                    flash("Uploaded file is empty.", 'error')
                    os.unlink(temp_file_path)
                    return render_template('usecase/gemini_pdf_ques_answer/gemini_pdf_ques_answer.html',
                                           conversation_history=conversation_history)

                text, pdf_type = extract_text_from_pdf(pdf_stream, filename)
                if not text:
                    flash("No text extracted from the PDF.", 'warning')
                    os.unlink(temp_file_path)
                    return render_template('usecase/gemini_pdf_ques_answer/gemini_pdf_ques_answer.html',
                                           conversation_history=conversation_history)

                # Clean up temporary file
                os.unlink(temp_file_path)
                temp_file_path = None

                session['conversation_history'] = []
                session.modified = True
                save_uploaded_pdf_state(filename, text)
                qdrant_client.delete_collection(COLLECTION_NAME)
                qdrant_client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
                )

                text_chunks = chunk_text(text)
                add_chunks_to_qdrant(text_chunks, text)
                uploaded_filename = filename
                extracted_text = text
                flash(f"PDF '{filename}' processed successfully! Type: {pdf_type}", 'success')
            except ValueError as ve:
                flash(str(ve), 'error')
                if 'temp_file_path' in locals() and temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
            except Exception as e:
                flash(f"Failed to process PDF: {str(e)}", 'error')
                if 'temp_file_path' in locals() and temp_file_path and os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)

        elif 'query' in request.form:
            user_question = request.form.get('user_question')
            if not user_question:
                flash("Please enter a question.", 'error')
            elif not session.get("pdf_ready") or not extracted_text:
                flash("Please upload a PDF first.", 'error')
            else:
                try:
                    relevant_chunks, full_text = get_relevant_chunks_and_full_text(user_question)
                    if not full_text:
                        answer = "No relevant content found in the extracted text."
                        flash("No relevant content found.", 'warning')
                    else:
                        context = full_text
                        conversation_context = format_conversation_history()
                        prompt = (
                            f"You are an expert assistant skilled at interpreting text extracted from PDFs. "
                            f"Your task is to provide a clear, concise, and accurate answer to the user's question based solely on the text below. "
                            f"Avoid speculation or external knowledge; focus only on the provided content. "
                            f"If the answer is not fully clear from the text, indicate uncertainty and explain why.\n\n"
                            f"**Extracted Text from PDF:**\n{context}\n\n"
                            f"{conversation_context}"
                            f"**Current Question:**\n{user_question}\n\n"
                            f"Provide your answer below:"
                        )
                        response = generation_model.generate_content(prompt)
                        answer = response.text.strip()
                        add_to_conversation_history(user_question, answer)
                        conversation_history = get_conversation_history()
                        flash("Answer generated successfully.", 'success')
                except Exception as e:
                    answer = "Could not generate an answer based on the extracted text."
                    flash(f"Error generating answer: {str(e)}", 'error')

    return render_template(
        'usecase/gemini_pdf_ques_answer/gemini_pdf_ques_answer.html',
        answer=answer,
        uploaded_filename=uploaded_filename,
        extracted_text=extracted_text,
        conversation_history=conversation_history
    )

@gemini_pdf_ques_answer.route('/delete_history', methods=['POST'])
def delete_history():
    session['conversation_history'] = []
    flash("Conversation history cleared.", 'success')
    return redirect(url_for('gemini_pdf_ques_answer.gemini_pdf_ques_answer_generate'))