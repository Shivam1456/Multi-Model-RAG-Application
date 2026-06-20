


Production URL: https://multiple-model-rag-usecases.vercel.app


Vercel Project Dashboard: https://multiple-model-rag-usecases.vercel.app/

multiple-model-rag-usecases-7u8pf6g97.vercel.app



****

![image](https://github.com/user-attachments/assets/87e64e7d-170e-4469-9a86-1d301a830b71)


![image](https://github.com/user-attachments/assets/cb5e60c3-075b-436b-9291-4770ed713be0)

![image](https://github.com/user-attachments/assets/3a16efdc-84a3-46a1-b80d-ffd398be995e)

![image](https://github.com/user-attachments/assets/95acef7e-ef3a-4f52-8191-aebc06e253e4)


![image](https://github.com/user-attachments/assets/fd4fd275-b780-4e77-a3f2-6a0ae3b7de39)


![image](https://github.com/user-attachments/assets/4796ef69-36b5-484b-a286-2398328adafb)

![image](https://github.com/user-attachments/assets/44358798-6192-403f-80e9-f137a1f697a8)

![image](https://github.com/user-attachments/assets/11e505e0-a74d-4269-83c5-3b85e7b27cea)


****
---
# 🚀 Multi-Model RAG (Retrieval-Augmented Generation) Application

An advanced, multi-usecase Retrieval-Augmented Generation (RAG) platform powered by **Flask**, **Google Gemini (2.5-Flash)**, **Qdrant Vector Database**, and **MongoDB**. This project provides four powerful AI features for chatting, processing documents, web scraping, and analyzing images.

---

## 📷 Application Preview

<p align="center">
  <img src="https://github.com/user-attachments/assets/87e64e7d-170e-4469-9a86-1d301a830b71" alt="Dashboard Preview" width="45%" />
  <img src="https://github.com/user-attachments/assets/cb5e60c3-075b-436b-9291-4770ed713be0" alt="Chat Interface" width="45%" />
</p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/3a16efdc-84a3-46a1-b80d-ffd398be995e" alt="PDF RAG" width="45%" />
  <img src="https://github.com/user-attachments/assets/95acef7e-ef3a-4f52-8191-aebc06e253e4" alt="Image QA" width="45%" />
</p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/fd4fd275-b780-4e77-a3f2-6a0ae3b7de39" alt="URL RAG" width="45%" />
  <img src="https://github.com/user-attachments/assets/4796ef69-36b5-484b-a286-2398328adafb" alt="History" width="45%" />
</p>

<p align="center">
  <img src="https://github.com/user-attachments/assets/44358798-6192-403f-80e9-f137a1f697a8" alt="Code Formatting" width="45%" />
  <img src="https://github.com/user-attachments/assets/11e505e0-a74d-4269-83c5-3b85e7b27cea" alt="Responsive View" width="45%" />
</p>

---

## 🌟 Key Features

1. **💬 Gemini Chatbot (Multimodal)**
   * Multipurpose conversational agent powered by `gemini-2.5-flash`.
   * **Persistence:** Auto-saves chat history in MongoDB (falls back seamlessly to in-memory/session if MongoDB is offline).
   * **Rich UI Elements:** Converts AI-generated CSV tables into formatted HTML tables, and formats code snippets with syntax highlighting via `pygments`.

2. **📄 PDF Question Answering (RAG)**
   * Extracts text from uploaded PDFs using `fitz` (PyMuPDF).
   * **OCR Fallback:** Scans non-selectable/scanned PDF files automatically using `easyocr` (for local runs).
   * **Vector Search:** Chunks document text, generates embeddings with Gemini, and stores vectors in **Qdrant** for real-time similarity search.

3. **🖼️ Image Q&A (Multimodal RAG)**
   * Upload an image to start a conversation about it.
   * Leverages Gemini's visual capability to describe visual contents combined with OCR extraction for text inside images.

4. **🌐 URL Scraper & Q&A (Web RAG)**
   * Input any website URL to scrape its main content using `BeautifulSoup`.
   * Automatically stores the text chunks in a session-specific Qdrant collection, enabling you to ask questions directly based on the webpage.

---

## 🛠️ Technology Stack

* **Backend Framework:** Flask (Python)
* **LLM & Embeddings:** Google Gemini API (`gemini-2.5-flash` & `gemini-embedding-001`)
* **Vector Store:** Qdrant Database (Supports in-memory `:memory:` or persistent cloud/local database paths)
* **Database:** MongoDB (for storing chat sessions and history)
* **OCR Engines:** PyMuPDF, EasyOCR, Pillow (PIL)
* **Frontend:** HTML5, CSS3, JavaScript, Pygments (for syntax coloring)

---

## 📦 Project Directory Structure

```text
Multiple-Model-RAG-Usecases/
│
├── app.py                      # Main entrypoint for Flask Server
├── vercel.json                 # Vercel Serverless deployment config
├── requirements.txt            # Python Dependencies
├── .env.example                # Environment variables template
│
├── backend_usecase/            # Application Blueprints
│   ├── gemini_chatbot/         # Blueprint for general chatbot
│   ├── gemini_pdf_ques_answer/ # Blueprint for PDF RAG
│   ├── gemini_image_text_ext_qa/# Blueprint for Image RAG
│   └── gemini_url_scrap_qa/    # Blueprint for Web scraper RAG
│
├── templates/                  # HTML templates
│   ├── common/                 # Dashboard/Index pages
│   └── usecase/                # Blueprint UI templates
│
└── cache/                      # Scraped URL cache directory (local)
```

---

## 🚀 Local Installation & Setup

### Prerequisites
* Python 3.10 to 3.12 (Highly recommended)
* A Google Gemini API Key (Get one from [Google AI Studio](https://aistudio.google.com/))
* MongoDB (Optional - runs in fallback mode if not installed)

### 1. Clone the Repository
```bash
git clone https://github.com/Shivam1456/Multi-Model-RAG-Application.git
cd Multi-Model-RAG-Application
```

### 2. Create and Activate Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```
*(Optional: If you want to use the local OCR fallback on your local machine, run `pip install easyocr`)*

### 4. Setup Environment Variables
Create a `.env` file in the root directory and specify the following variables:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
FLASK_SECRET_KEY=any_random_secret_string
MONGO_URI=mongodb://localhost:27017
QDRANT_URL=:memory:
QDRANT_API_KEY=local
```

### 5. Run the Server
```bash
python app.py
```
Open **[http://127.0.0.1:10000](http://127.0.0.1:10000)** in your browser!

---

## ☁️ Vercel Cloud Deployment

This repository is optimized to deploy directly on **Vercel** as a Python Serverless Function.

### Vercel Package Size Note
Vercel serverless functions have a strict **500 MB limit** for runtime environments. Heavy deep-learning packages like PyTorch (`torch`), which are required for `easyocr`, cannot fit within this limit. 

To enable seamless Vercel deployment:
1. `easyocr` is excluded from the cloud environment `requirements.txt`.
2. The codebase implements **lazy imports** and handles the absence of local OCR engines gracefully. 
3. When deployed on the cloud, the Image Q&A feature automatically utilizes Gemini's native multimodal capabilities, yielding high-performance image understanding without local server-side models.

### Steps to Deploy:
1. Fork or push this repository to your GitHub account.
2. Link the repository on the [Vercel Dashboard](https://vercel.com).
3. Add the required Environment Variables in Vercel settings:
   * `GOOGLE_API_KEY`
   * `FLASK_SECRET_KEY`
   * `QDRANT_URL` (Set to `:memory:` or connect a cloud Qdrant cluster)
   * `QDRANT_API_KEY`
   * `MONGO_URI` (Use MongoDB Atlas since Vercel cannot connect to `localhost`)
4. Click **Deploy**.

---

## 🤝 Contributing
Feel free to open issues or submit pull requests to improve the RAG capabilities, add more multimodal models, or enhance the dashboard UI!






