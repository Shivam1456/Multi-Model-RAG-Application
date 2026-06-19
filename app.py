from flask import Flask, render_template
from backend_usecase.gemini_pdf_ques_answer.gemini_pdf_ques_answer import gemini_pdf_ques_answer
from backend_usecase.gemini_chatbot.gemini_chatbot import gemini_chatbot
from backend_usecase.gemini_image_text_ext_qa.gemini_image_text_ext_qa import gemini_image_text_ext_qa
from backend_usecase.gemini_url_scrap_qa.gemini_url_scrap_qa import gemini_url_scrap_qa
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, template_folder="templates")

app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret-key-change-in-production")

# Register Blueprints
app.register_blueprint(gemini_chatbot, url_prefix="/gemini_chatbot")
app.register_blueprint(gemini_pdf_ques_answer, url_prefix="/gemini_pdf_ques_answer")
app.register_blueprint(gemini_image_text_ext_qa, url_prefix="/gemini_image_text_ext_qa")
app.register_blueprint(gemini_url_scrap_qa, url_prefix="/gemini_url_scrap_qa")

@app.template_filter('basename')
def basename_filter(file_path):
    """Extract the base name from a file path."""
    return os.path.basename(file_path)

@app.route('/')
def index():
    return render_template('common/index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(debug=False, host="0.0.0.0", port=port)