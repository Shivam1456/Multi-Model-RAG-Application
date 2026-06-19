






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

## ✅ Steps to Run a Cloned Flask App in VS Code

### **1. Clone the Repository**

In the terminal:

```bash
git clone https://github.com/satyamjaysawal/Multiple-Model-RAG-Usecases.git
cd Multiple-Model-RAG-Usecases
```

> Replace the URL with your actual GitHub repo link.
---

### **2. Open the Project in VS Code**

```bash
code .
```

---

### **3. Create and Activate a Virtual Environment**

```bash
# Create
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

---

### **4. Install Dependencies**

```bash
pip install -r requirements.txt
```

---

### **5. Create a `.env` File (Optional but Recommended)**

In the project root, create a file named `.env` with:

```env
GOOGLE_API_KEY=
FLASK_SECRET_KEY=
MONGO_URI=
QDRANT_URL=
QDRANT_API_KEY=
```

> Replace `app.py` with the actual entry point of your app (e.g., `run.py`, or a package name).

To use `.env` files automatically, install **`python-dotenv`** (if not already in requirements):

```bash
pip install python-dotenv
```

Flask will automatically read the `.env` file if `python-dotenv` is installed and you're using the Flask CLI.

---

### **6. Run the Flask App**

```bash
flask run
```

---

### **7. Open in Browser**

Go to:
📍 `http://127.0.0.1:5000/`








