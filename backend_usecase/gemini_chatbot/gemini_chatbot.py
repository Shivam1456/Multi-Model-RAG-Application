import re
import numpy as np
from flask import Blueprint, request, render_template, session, jsonify, redirect, url_for
import google.generativeai as genai
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name
from typing import Tuple, Optional, Dict, Any
import os
from dataclasses import dataclass
import datetime
import time
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi
from bson.objectid import ObjectId

# Load environment variables from .env file
load_dotenv()

@dataclass
class Config:
    EMBEDDING_DIMENSION: int = 768
    MODEL_NAME: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    MAX_HISTORY_SIZE: int = 100
    RATE_LIMIT_SECONDS: float = 1.0
    MAX_QUERY_LENGTH: int = 1000
    RECENT_CHATS_LIMIT: int = 5  # Number of recent chats to display

# Initialize Blueprint and global components
gemini_chatbot = Blueprint('gemini_chatbot', __name__, template_folder='../../../templates')
config = Config()

# Global variables
mongo_client = None
mongo_db = None
response_store: list = []
collection_name = "chatbot_history"
use_mongo = True

# Initialize components with fallback
try:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY environment variable not set")
    genai.configure(api_key=GOOGLE_API_KEY)

    MONGO_URI = os.getenv("MONGO_URI")
    if not MONGO_URI:
        raise ValueError("MONGO_URI environment variable not set")
    
    mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    mongo_db = mongo_client.get_database("gemini_chatbot_db")
    mongo_collection = mongo_db[collection_name]
    
    mongo_client.server_info()
    response_store = []
except Exception as e:
    use_mongo = False
    mongo_client = None
    mongo_db = None
    response_store = []

class ChatbotError(Exception):
    """Custom exception for chatbot errors"""
    pass

def get_embedding(text: str) -> np.ndarray:
    retries = 3
    for attempt in range(retries):
        try:
            if not text or not isinstance(text, str):
                raise ValueError("Input text must be a non-empty string")
            if len(text) > config.MAX_QUERY_LENGTH:
                raise ValueError(f"Query exceeds maximum length of {config.MAX_QUERY_LENGTH} characters")
            
            embedding_response = genai.embed_content(
                model=config.EMBEDDING_MODEL,
                content=text,
                output_dimensionality=768,
            )
            
            if 'embedding' not in embedding_response:
                raise ValueError("Embedding generation failed: No embedding in response")
            
            embedding = np.array(embedding_response['embedding'], dtype=np.float32)
            if embedding.shape[0] != config.EMBEDDING_DIMENSION:
                raise ValueError(f"Embedding dimension mismatch: expected {config.EMBEDDING_DIMENSION}, got {embedding.shape[0]}")
            
            return embedding
        except Exception as e:
            if attempt == retries - 1:
                raise ChatbotError(f"Embedding generation failed after {retries} attempts: {str(e)}")
            time.sleep(2 ** attempt)

def load_gemini_pro_model() -> genai.GenerativeModel:
    try:
        return genai.GenerativeModel(config.MODEL_NAME)
    except Exception as e:
        raise ChatbotError("Failed to load AI model")

def generate_prompt(question: str) -> str:
    question = question.strip()
    if len(question) > config.MAX_QUERY_LENGTH:
        question = question[:config.MAX_QUERY_LENGTH]
    return (
        """
        ### INSTRUCTIONS FOR THE AI ###
        - You are an advanced AI assistant designed to answer user queries in a structured and informative way.
        - Do not include unnecessary phrases like "Okay, I understand" or "Here's my response to the query."
        - Your response should start directly with the relevant content.

        - If the query involves coding or algorithms, include:
          1. A properly formatted and functional code snippet enclosed within ``` markers.
          2. At the beginning of the code snippet, include a comment specifying the programming language (e.g., // Language: Java, # Language: Python).

        - Your response must include:
          1. A **textual explanation** summarizing the query and providing a concise, clear answer.
          2. A **clean table in CSV format** enclosed within ```csv``` markers, summarizing key aspects or metadata about the query.
          3. A **functional code snippet** enclosed within ``` markers if applicable.

        ### USER QUERY ###
        - {question}

        ### RESPONSE REQUIREMENTS ###
        1. **Textual Explanation:**
           - Provide a concise and clear summary of the answer.
           - If applicable, briefly explain the logic or algorithm used.

        2. **Table Requirements:**
           - If relevant, include a CSV table summarizing key details of the query.
           - Use proper headers and organize the data logically.

        3. **Code Requirements:**
           - If the query is related to coding, include the code snippet enclosed within ``` markers.
           - Add a comment line at the beginning of the code snippet specifying the programming language used (e.g., // Language: Python).
           - Ensure the code is well-formatted and functional.
           - Provide meaningful variable names and clear logic.

        4. **Fallback for Unanswerable Queries:**
           - If you cannot generate an appropriate response, reply with: "I'm sorry, I couldn't find information on this topic."
        """
    ).format(question=question)

def extract_response_content(response_text: str) -> Tuple[str, Optional[str], Optional[str], str]:
    try:
        csv_pattern = r"```csv\s*([\s\S]*?)\s*```"
        code_pattern = r"```(python|javascript|java|c\+\+|cpp|html|css|sql|mysql|r)\s*([\s\S]*?)\s*```"

        csv_match = re.search(csv_pattern, response_text, re.DOTALL)
        csv_content = csv_match.group(1).strip() if csv_match else None

        code_match = re.search(code_pattern, response_text, re.DOTALL)
        code_language = code_match.group(1).strip() if code_match else "python"
        code_content = code_match.group(2).strip() if code_match else None

        explanation = re.sub(csv_pattern, "", response_text, flags=re.DOTALL)
        explanation = re.sub(code_pattern, "", explanation, flags=re.DOTALL).strip()

        if not explanation:
            explanation = "No detailed explanation provided."

        return explanation, csv_content, code_content, code_language
    except Exception as e:
        raise ChatbotError("Failed to process response content")

def store_response(query: str, explanation: str, csv_content: Optional[str], 
                  code_content: Optional[str], code_language: str = "python") -> Dict[str, Any]:
    global mongo_db, response_store, use_mongo
    try:
        if not query or not explanation:
            raise ValueError("Query and explanation cannot be empty")
        
        response_data = {
            'query': query,
            'explanation': explanation,
            'csv_content': csv_content,
            'code_content': code_content,
            'code_language': code_language,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        if use_mongo and mongo_db is not None:
            result = mongo_db[collection_name].insert_one(response_data)
            response_data['_id'] = str(result.inserted_id)
        
        response_store.append(response_data)
        if len(response_store) > config.MAX_HISTORY_SIZE:
            removed_entry = response_store.pop(0)
            if use_mongo and mongo_db is not None and '_id' in removed_entry:
                mongo_db[collection_name].delete_one({"_id": ObjectId(removed_entry['_id'])})
        
        return response_data
    except Exception as e:
        raise ChatbotError(f"Failed to store response: {str(e)}")

def csv_to_html_table(csv_content: Optional[str]) -> str:
    if not csv_content:
        return "<p>No table data available.</p>"
    try:
        rows = [line.strip() for line in csv_content.strip().split("\n") if line.strip()]
        if not rows:
            return "<p>Empty table data.</p>"
        headers = rows[0].split(",")
        table_html = """
        <div class="overflow-auto">
            <table class="min-w-full divide-y divide-gray-200 border border-gray-300">
                <thead class="bg-gray-100">
                    <tr>
        """
        table_html += "".join(
            [f"<th class='px-4 py-2 text-left text-sm font-medium text-gray-600 uppercase tracking-wider'>{header.strip()}</th>" for header in headers]
        )
        table_html += """
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
        """
        for row in rows[1:]:
            columns = row.split(",")
            table_html += "<tr>" + "".join(
                [f"<td class='px-4 py-2 text-sm text-gray-700'>{col.strip()}</td>" for col in columns]
            ) + "</tr>"
        table_html += """
                </tbody>
            </table>
        </div>
        """
        return table_html
    except Exception as e:
        return "<p>Error rendering table.</p>"

def code_to_html_snippet(code_content: Optional[str], code_language: str = "python") -> str:
    if not code_content:
        return ""
    try:
        lexer = get_lexer_by_name(code_language, stripall=True)
    except Exception:
        lexer = get_lexer_by_name("text", stripall=True)
    
    try:
        formatter = HtmlFormatter(style="monokai", linenos='table', full=False, nowrap=True)
        highlighted_code = highlight(code_content.strip(), lexer, formatter)
        style_block = f"<style>{formatter.get_style_defs('.highlight')}</style>"
        return f"{style_block}<div class='highlight bg-gray-900 p-4 rounded-lg'>{highlighted_code}</div>"
    except Exception as e:
        return f"<pre>{code_content}</pre>"

def rate_limit_check() -> bool:
    last_request = session.get('last_request_time', 0)
    current_time = time.time()
    if current_time - last_request < config.RATE_LIMIT_SECONDS:
        return False
    session['last_request_time'] = current_time
    return True

@gemini_chatbot.route('/gemini_chatbot_generate', methods=['GET', 'POST'])
def generate_content():
    try:
        session.setdefault('history', [])
        
        if request.method == 'POST':
            if not rate_limit_check():
                return render_template('usecase/gemini_chatbot/gemini_chatbot.html', 
                                    error="Please wait before submitting another query.",
                                    history_count=len(session.get('history', [])),
                                    max_query_length=config.MAX_QUERY_LENGTH)

            user_query = request.form.get('query', '').strip()
            if not user_query:
                return render_template('usecase/gemini_chatbot/gemini_chatbot.html', 
                                    error="Query is required.",
                                    history_count=len(session.get('history', [])),
                                    max_query_length=config.MAX_QUERY_LENGTH)
            
            prompt = generate_prompt(user_query)
            model = load_gemini_pro_model()
            response = model.generate_content(prompt)
            
            if not hasattr(response, 'text') or not response.text:
                raise ChatbotError("No valid response from AI model")
                
            explanation, csv_content, code_content, code_language = extract_response_content(response.text)
            response_data = store_response(user_query, explanation, csv_content, code_content, code_language)

            html_table = csv_to_html_table(csv_content)
            html_code = code_to_html_snippet(code_content, code_language)

            session_entry = {
                'query': user_query,
                'explanation': explanation,
                'table_html': html_table,
                'code_html': html_code,
                'code_content': code_content,
                'code_language': code_language,
                'timestamp': response_data['timestamp'],
                '_id': response_data.get('_id')
            }
            session['history'].append(session_entry)
            if len(session['history']) > config.MAX_HISTORY_SIZE:
                session['history'].pop(0)
            session.modified = True

            return render_template(
                'usecase/gemini_chatbot/gemini_chatbot.html',
                query=user_query,
                explanation=explanation,
                table_html=html_table,
                code_html=html_code,
                code_language=code_language,
                code_content=code_content,
                history_count=len(session['history']),
                max_query_length=config.MAX_QUERY_LENGTH
            )

        return render_template(
            'usecase/gemini_chatbot/gemini_chatbot.html',
            history_count=len(session.get('history', [])),
            max_query_length=config.MAX_QUERY_LENGTH
        )
    except ChatbotError as e:
        return render_template('usecase/gemini_chatbot/gemini_chatbot.html', 
                              error=str(e),
                              history_count=len(session.get('history', [])),
                              max_query_length=config.MAX_QUERY_LENGTH)
    except Exception as e:
        return render_template('usecase/gemini_chatbot/gemini_chatbot.html', 
                              error=f"An unexpected error occurred: {str(e)}",
                              history_count=len(session.get('history', [])),
                              max_query_length=config.MAX_QUERY_LENGTH)

@gemini_chatbot.route('/history', methods=['GET'])
def show_history():
    """Display all chat history with pagination support."""
    try:
        history = session.get('history', [])
        history = sorted(history, key=lambda x: x['timestamp'], reverse=True)  # Sort by timestamp, newest first
        page = request.args.get('page', 1, type=int)
        per_page = 10
        total = len(history)
        start = (page - 1) * per_page
        end = start + per_page
        paginated_history = history[start:end]
        return render_template('usecase/gemini_chatbot/history.html', 
                              history=paginated_history, 
                              page=page, 
                              per_page=per_page, 
                              total=total,
                              view='all')
    except Exception as e:
        return render_template('usecase/gemini_chatbot/history.html', 
                              error="Failed to load history", view='all')

@gemini_chatbot.route('/recent_chats', methods=['GET'])
def show_recent_chats():
    """Display the most recent chats."""
    try:
        history = session.get('history', [])
        history = sorted(history, key=lambda x: x['timestamp'], reverse=True)  # Sort by timestamp, newest first
        recent_history = history[:config.RECENT_CHATS_LIMIT]  # Get the most recent entries
        return render_template('usecase/gemini_chatbot/history.html', 
                              history=recent_history, 
                              page=1, 
                              per_page=config.RECENT_CHATS_LIMIT, 
                              total=len(history),
                              view='recent')
    except Exception as e:
        return render_template('usecase/gemini_chatbot/history.html', 
                              error="Failed to load recent chats", view='recent')

@gemini_chatbot.route('/clear_history', methods=['POST'])
def clear_history():
    """Clear chat history with confirmation."""
    global mongo_db, response_store, use_mongo
    try:
        session.pop('history', None)
        if use_mongo and mongo_db is not None:
            mongo_db[collection_name].delete_many({})
        response_store.clear()
        return render_template('usecase/gemini_chatbot/history.html', history=[], view='all')
    except Exception as e:
        return render_template('usecase/gemini_chatbot/history.html', 
                              error="Failed to clear history", view='all')

@gemini_chatbot.route('/delete_history_entry', methods=['POST'])
def delete_history_entry():
    """Delete a specific history entry based on _id from session, response_store, and MongoDB."""
    global mongo_db, response_store, use_mongo
    try:
        entry_id = request.form.get('_id')
        if not entry_id:
            raise ValueError("_id is required to delete an entry")

        # Remove from session history
        history = session.get('history', [])
        history = [entry for entry in history if entry.get('_id') != entry_id]
        session['history'] = history
        session.modified = True

        # Remove from in-memory store
        response_store[:] = [entry for entry in response_store if entry.get('_id') != entry_id]

        # Remove from MongoDB if applicable
        if use_mongo and mongo_db is not None:
            mongo_db[collection_name].delete_one({"_id": ObjectId(entry_id)})

        return redirect(url_for('gemini_chatbot.show_history'))
    except Exception as e:
        return render_template('usecase/gemini_chatbot/history.html', 
                              error=f"Failed to delete entry: {str(e)}",
                              history=session.get('history', []),
                              view='all')

@gemini_chatbot.route('/health', methods=['GET'])
def health_check():
    try:
        if use_mongo and mongo_db is not None:
            mongo_size = mongo_db[collection_name].count_documents({})
            status = 'healthy'
        else:
            mongo_size = 0
            status = 'healthy (in-memory mode)'
        return jsonify({
            'status': status,
            'mongo_collection_size': mongo_size,
            'response_store_size': len(response_store),
            'timestamp': datetime.datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500