import os
import requests
from flask import Blueprint, request, render_template, flash, session, redirect, url_for
from bs4 import BeautifulSoup
from qdrant_client import QdrantClient # type: ignore
from qdrant_client.http import models # type: ignore
import google.generativeai as genai # type: ignore
from dotenv import load_dotenv
import uuid
import re
import pickle

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
gemini_url_scrap_qa = Blueprint('gemini_url_scrap_qa', __name__, template_folder='../templates')

# Initialize Qdrant client
if QDRANT_URL.startswith(("http://", "https://")):
    qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, verify=False)
elif QDRANT_URL == ":memory:":
    qdrant_client = QdrantClient(":memory:")
else:
    os.makedirs(QDRANT_URL, exist_ok=True)
    qdrant_client = QdrantClient(path=QDRANT_URL)

# Models
embedding_model = "models/gemini-embedding-001"
generation_model = genai.GenerativeModel("gemini-2.5-flash")

# Configuration
MAX_CONVERSATION_HISTORY = 5
MAX_TEXT_LENGTH = 100000  # Limit scraped text to 100k characters
CHUNK_SIZE = 512
TOP_K = 5
CACHE_DIR = "cache"
MIN_QUESTION_LENGTH = 3

# Ensure cache directory exists
os.makedirs(CACHE_DIR, exist_ok=True)

def get_cache_file(session_id):
    """Get the file path for caching scraped text."""
    return os.path.join(CACHE_DIR, f"scraped_text_{session_id}.pkl")

def save_scraped_text(session_id, text):
    """Save scraped text to a file."""
    try:
        with open(get_cache_file(session_id), 'wb') as f:
            pickle.dump(text, f)
    except Exception as e:
        raise RuntimeError(f"Failed to save scraped text: {str(e)}")

def load_scraped_text(session_id):
    """Load scraped text from a file."""
    try:
        with open(get_cache_file(session_id), 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return None
    except Exception as e:
        raise RuntimeError(f"Failed to load scraped text: {str(e)}")

def get_collection_name(session_id):
    """Generate a unique Qdrant collection name for the session."""
    return f"url_chunks_{session_id}"

def initialize_qdrant_collection(collection_name):
    """Initialize or recreate a Qdrant collection for storing text embeddings."""
    try:
        if qdrant_client.collection_exists(collection_name):
            qdrant_client.delete_collection(collection_name)
        qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=768, distance=models.Distance.COSINE)
        )
    except Exception as e:
        raise RuntimeError(f"Failed to initialize Qdrant collection: {str(e)}")

def scrape_url(url):
    """Scrape text content from a given URL, prioritizing relevant HTML tags."""
    try:
        # Validate URL format
        if not re.match(r'^https?://', url):
            url = 'https://' + url
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        if 'text/html' not in response.headers.get('Content-Type', ''):
            raise ValueError("URL does not point to an HTML page.")

        soup = BeautifulSoup(response.text, 'html.parser')
        # Remove unwanted elements
        for element in soup(['script', 'style', 'comment', 'nav', 'footer', 'header']):
            element.decompose()

        # Extract text from specific tags to ensure comprehensive content capture
        relevant_tags = ['h1', 'h2', 'h3', 'p', 'li', 'article', 'section', 'div']
        text_parts = []
        for tag in soup.find_all(relevant_tags):
            tag_text = tag.get_text(separator=' ', strip=True)
            if tag_text:
                text_parts.append(tag_text)

        text = ' '.join(text_parts)
        text = re.sub(r'\s+', ' ', text).strip()

        if not text:
            raise ValueError("No text content found on the page.")
        if len(text) > MAX_TEXT_LENGTH:
            text = text[:MAX_TEXT_LENGTH]
        return text
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Failed to fetch URL: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error processing URL content: {str(e)}")

def chunk_text(text, chunk_size=CHUNK_SIZE):
    """Split text into chunks for embedding."""
    words = text.split()
    chunks = [' '.join(words[i:i + chunk_size]) for i in range(0, len(words), chunk_size - 50)]
    return chunks

def add_chunks_to_qdrant(text_chunks, full_text, collection_name):
    """Generate embeddings for text chunks and store them in Qdrant."""
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
    
    qdrant_client.upsert(collection_name=collection_name, points=points)

def get_relevant_chunks_and_full_text(query, collection_name, top_k=TOP_K):
    """Retrieve relevant text chunks from Qdrant based on query embedding."""
    try:
        response = genai.embed_content(model=embedding_model, content=query, output_dimensionality=768)
        if 'embedding' not in response:
            raise ValueError("Embedding generation failed")
        query_embedding = response['embedding']

        search_result = qdrant_client.query_points(
            collection_name=collection_name,
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

def get_conversation_history():
    """Retrieve conversation history from session."""
    if 'url_conversation_history' not in session:
        session['url_conversation_history'] = []
    return session['url_conversation_history']

def add_to_conversation_history(question, answer):
    """Add a question-answer pair to conversation history."""
    history = get_conversation_history()
    history.append({"question": question, "answer": answer})
    if len(history) > MAX_CONVERSATION_HISTORY:
        history = history[-MAX_CONVERSATION_HISTORY:]
    session['url_conversation_history'] = history
    session.modified = True

def format_conversation_history():
    """Format conversation history for inclusion in prompts."""
    history = get_conversation_history()
    if not history:
        return ""
    formatted = "**Previous Conversation:**\n\n"
    for i, qa in enumerate(history):
        formatted += f"Q{i+1}: {qa['question']}\n"
        formatted += f"A{i+1}: {qa['answer']}\n\n"
    return formatted

def validate_question(question):
    """Validate the user's question."""
    if not question:
        return False, "Question cannot be empty."
    if len(question.strip()) < MIN_QUESTION_LENGTH:
        return False, f"Question must be at least {MIN_QUESTION_LENGTH} characters long."
    if re.match(r'^[\W_]+$', question):
        return False, "Question contains only special characters."
    return True, ""

@gemini_url_scrap_qa.route('/gemini_url_scrap_qa_generate', methods=['GET', 'POST'])
def gemini_url_scrap_qa_generate():
    """Handle URL scraping and RAG-based question-answering."""
    answer = None
    scraped_url = session.get('scraped_url')
    scraped_text = load_scraped_text(session.get('session_id', str(uuid.uuid4())))
    conversation_history = get_conversation_history()
    session_id = session.get('session_id', str(uuid.uuid4()))
    session['session_id'] = session_id
    collection_name = get_collection_name(session_id)

    if request.method == 'POST':
        if 'url' in request.form:
            url = request.form.get('url')
            if not url:
                flash("Please enter a URL.", 'error')
                return render_template('usecase/gemini_url_scrap_qa/gemini_url_scrap_qa.html',
                                       conversation_history=conversation_history)

            try:
                text = scrape_url(url)
                session['url_conversation_history'] = []
                session['scraped_url'] = url
                save_scraped_text(session_id, text)
                initialize_qdrant_collection(collection_name)
                text_chunks = chunk_text(text)
                add_chunks_to_qdrant(text_chunks, text, collection_name)
                scraped_url = url
                scraped_text = text
                flash(f"URL '{url}' processed successfully!", 'success')
            except ValueError as ve:
                flash(str(ve), 'error')
            except Exception as e:
                flash(f"Failed to process URL: {str(e)}", 'error')

        elif 'user_question' in request.form:
            user_question = request.form.get('user_question', '').strip()
            is_valid, error_message = validate_question(user_question)
            if not is_valid:
                flash(error_message, 'error')
            elif not scraped_text:
                flash("Please provide a URL first.", 'error')
            else:
                try:
                    relevant_chunks, full_text = get_relevant_chunks_and_full_text(user_question, collection_name)
                    if not full_text:
                        answer = "No relevant content found in the scraped text."
                        flash("No relevant content found.", 'warning')
                    else:
                        context = full_text
                        conversation_context = format_conversation_history()
                        # prompt = (
                        #     "You are an advanced language model assistant trained to interpret and extract meaning from raw webpage content. "
                        #     "Your task is to read the provided scraped text and answer the user's question based **only** on that content. "
                        #     "Follow these rules strictly:\n"
                        #     "1. Base your answer solely on the scraped text. Do not rely on prior knowledge or make assumptions.\n"
                        #     "2. If the question cannot be fully answered with the available information, explicitly state that and explain why.\n"
                        #     "3. Focus on clarity, factual accuracy, and conciseness. Avoid unnecessary elaboration.\n"
                        #     "4. If helpful, summarize relevant parts of the scraped content before answering.\n"
                        #     "5. Use a neutral and informative tone.\n\n"
                            
                        #     "=== Scraped Webpage Content ===\n"
                        #     f"{context}\n\n"

                        #     "=== Conversation History (if applicable) ===\n"
                        #     f"{conversation_context if conversation_context.strip() else '[No prior conversation context provided]'}\n\n"

                        #     "=== User Question ===\n"
                        #     f"{user_question}\n\n"

                        #     "=== Answer ===\n"
                        # )

                        prompt = (
                            "You are an advanced language model assistant trained to extract, interpret, and summarize information from raw webpage content. "
                            "Your task is to read the provided scraped text and respond to the user's question with the most relevant, accurate, and complete information available in the content. "
                            "If the exact answer is not present, perform a similarity search within the scraped content to find related or similar information that could help answer the question. "
                            "Follow these strict rules:\n"
                            "1. Base your answer solely on the scraped text. Do not use external knowledge or assumptions.\n"
                            "2. If the question cannot be fully answered with the provided information, clearly state that and explain why.\n"
                            "3. Search for and highlight related or similar concepts in the scraped text that could help answer the question.\n"
                            "4. Summarize relevant parts of the scraped content before answering, if helpful.\n"
                            "5. Focus on clarity, factual accuracy, and conciseness. Avoid unnecessary elaboration.\n"
                            "6. Use a neutral and informative tone.\n\n"

                            "=== Scraped Webpage Content ===\n"
                            f"{context}\n\n"

                            "=== Conversation History (if applicable) ===\n"
                            f"{conversation_context if conversation_context.strip() else '[No prior conversation context provided]'}\n\n"

                            "=== User Question ===\n"
                            f"{user_question}\n\n"

                            "=== Answer ===\n"
                        )

                        response = generation_model.generate_content(prompt)
                        answer = response.text.strip()
                        add_to_conversation_history(user_question, answer)
                        conversation_history = get_conversation_history()
                        flash("Answer generated successfully.", 'success')
                except Exception as e:
                    answer = "Could not generate an answer based on the scraped text."
                    flash(f"Error generating answer: {str(e)}", 'error')

        else:
            flash("Invalid form submission.", 'error')

    return render_template(
        'usecase/gemini_url_scrap_qa/gemini_url_scrap_qa.html',
        answer=answer,
        scraped_url=scraped_url,
        scraped_text=scraped_text,
        conversation_history=conversation_history
    )

@gemini_url_scrap_qa.route('/delete_history', methods=['POST'])
def delete_history():
    """Clear conversation history."""
    session['url_conversation_history'] = []
    flash("Conversation history cleared.", 'success')
    return redirect(url_for('gemini_url_scrap_qa.gemini_url_scrap_qa_generate'))