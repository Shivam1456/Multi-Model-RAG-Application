


Here's a detailed Mermaid flow diagram with example PDF content integration:

```mermaid
%%{init: {'theme': 'base', 'fontFamily': 'Segoe UI', 'gantt': {'barHeight': 20}}}%%
flowchart TD
    A([Start]) --> B["Initialize EasyOCR (English)"]
    B --> C["Open: sample.pdf (2 pages)"]
    C --> D["normal_text = ''\nocr_text = ''"]
    
    subgraph Page_Processing["Page Processing (Per Page)"]
        direction TB
        E{{"For each page (1-2)"}} --> F["Page 1: Digital Text\n'Invoice: INV123\nDate: 2025-08-14'"]
        F --> G["normal_text += Digital Text"]
        G --> H["Convert to Image (200DPI)"]
        H --> I["OCR Results:\n'Invoice: INV123\nDate: 2025-08-14'"]
        I --> J["ocr_text += OCR Results"]
        
        E --> K["Page 2: Image Only"]
        K --> L["normal_text += '' (no digital text)"]
        L --> M["Convert to Image"]
        M --> N["OCR Results:\n'Item: Laptop\nPrice: $1200'"]
        N --> O["ocr_text += OCR Results"]
    end
    
    D --> Page_Processing
    Page_Processing --> P["Close PDF"]
    P --> Q["Combine:\ncomplete_text = normal_text + ocr_text"]
    Q --> R["Save to extracted_text_easyocr.txt"]
    R --> S([End])
    
    style A fill:#2ecc71,stroke:#27ae60
    style S fill:#e74c3c,stroke:#c0392b
    style E fill:#f39c12,stroke:#e67e22
    style F,K fill:#3498db,stroke:#2980b9
    style I,N fill:#2ecc71,stroke:#27ae60,stroke-dasharray:5
    style R fill:#9b59b6,stroke:#8e44ad
    
    %% Example File Content
    click F "data:image/svg+xml;base64,..." "Page 1 Preview"
    click K "data:image/svg+xml;base64,..." "Page 2 Preview"
```


### Final Output Simulation:
```plaintext
[normal_text]
Invoice: INV123
Date: 2025-08-14

[ocr_text]
Invoice: INV123
Date: 2025-08-14
Item: Laptop
Price: $1200
```


---

## 📄 `README.md` (For Local Windows Only – with Full Code)

````md
# 📄 PDF Text Extractor (with OCR) – Local Windows System Only

This Python project extracts complete text from any PDF, including:
- ✅ Normal (selectable) text
- ✅ Text inside scanned images using OCR

It is designed to run specifically on **Windows systems only** with proper paths configured for **Tesseract OCR** and **Poppler**.

---

## 🎯 Purpose and Use Cases

- 📚 Extract full text from academic or scanned PDF documents
- 🔍 Process government PDFs where text is image-based (scanned files)
- 📑 Digitize old printed documents or archives
- 💬 Use in NLP preprocessing pipelines for raw textual input

---

## 💻 System Requirement

- ✅ Works only on **Windows**
- Python 3.x installed
- Tesseract OCR installed at: `C:\Program Files\Tesseract-OCR`
- Poppler installed at: `C:\poppler\Library\bin`

---

## 🛠️ Dependencies

Install required libraries:

```bash
pip install pymupdf pdf2image pytesseract
````

Also install:

* [Tesseract for Windows (UB Mannheim build)](https://github.com/UB-Mannheim/tesseract/wiki)
* [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases)

Make sure both are extracted and their **paths are correct** (see below in code).

---

## 📜 Full Code: `extract_text.py`

```python
import fitz  # PyMuPDF
from pdf2image import convert_from_path
import pytesseract

# Set path to Tesseract (Windows only)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# PDF and Poppler paths
pdf_path = "sample.pdf"
poppler_path = r"C:\poppler\Library\bin"  # Make sure this contains pdfinfo.exe

# Step 1: Extract selectable text
doc = fitz.open(pdf_path)
normal_text = ""
for page in doc:
    normal_text += page.get_text()
doc.close()

# Step 2: OCR for scanned image-based text
images = convert_from_path(pdf_path, poppler_path=poppler_path)
ocr_text = ""
for img in images:
    ocr_text += pytesseract.image_to_string(img, lang='eng')  # Use 'hin' for Hindi

# Step 3: Combine all text
complete_text = normal_text + "\n" + ocr_text

# Step 4: Save output
with open("extracted_text.txt", "w", encoding="utf-8") as f:
    f.write(complete_text)

print("✅ Text extracted and saved to 'extracted_text.txt'")
```

---

## 📁 Folder Structure

```
project-folder/
│
├── sample.pdf               # Your input PDF file
├── extract_text.py          # Main script
├── extracted_text.txt       # Output text
└── README.md                # Project info
```

---

## ⚠️ Notes

* This project is tested on **Windows 10/11 only**
* For other platforms (Linux/macOS), Poppler and Tesseract need separate setup

---

## 📌 Output

After running the script, you’ll get a file called:

```
extracted_text.txt
```

Which contains **all the text extracted** from the PDF, including OCR-scanned content.

---

## ❌ Limitations

* Doesn’t work without installing Poppler & Tesseract
* Designed only for **local usage**, not web-based
* Doesn’t preserve formatting/tables (plain text only)

---

## 📜 License

MIT License. Free to use and modify.

---

## 🤝 Contributions

Not open for contribution – personal/local tool. But feel free to customize!

```

---

## ✅ Next Step

Would you like me to:

- Generate this `README.md` file as a **downloadable Markdown file**?
- Package it as a zip with the code and sample file?
- Convert this to a `.docx` or `.pdf` documentation file?

Let me know and I’ll prepare it.
```













****
****
****
****
****






****


****


****


## 📄 PDF Text Extractor with OCR using EasyOCR, PyMuPDF, and Pillow – Full Offline Solution for Extracting Text from Digital and Scanned PDFs (No Tesseract/Poppler Required, Windows/Linux/Mac)

****

****

****

Great! Since it's working now, here's a complete and professional `README.md` for your project, written specifically for local development with **EasyOCR**, **PyMuPDF**, and **Pillow**, and includes detailed steps for using in **Visual Studio Code (VS Code)**.

---



````markdown
# 📄 PDF Text Extractor (EasyOCR + PyMuPDF + Pillow)

A lightweight, local Python tool to **extract text from PDF files**, including both:
- Selectable digital text
- Scanned image-based text (using OCR)

This version **does not require Tesseract or Poppler**, and works entirely with:
- 🧠 [EasyOCR](https://github.com/JaidedAI/EasyOCR)
- 📕 [PyMuPDF (fitz)](https://pymupdf.readthedocs.io/)
- 🖼️ [Pillow (PIL)](https://python-pillow.org/)

---

## ✅ Features

- Extract **all visible text** from PDFs
- Supports **OCR for scanned pages**
- Saves output in a clean `.txt` file
- Fully **offline** and **cross-platform** (Windows/Linux/Mac)
- Can be used in **Visual Studio Code** or any Python IDE

---

## 🧱 Dependencies

Install the required Python libraries:

```bash
pip install pymupdf pillow easyocr
````

> ℹ️ You don’t need Poppler or Tesseract for this version.

---

## 🧑‍💻 How to Run (VS Code Setup)

### 1. Clone or copy the project folder

Open a terminal in VS Code or any command line:

```bash
mkdir pdf_text_extractor_easyocr
cd pdf_text_extractor_easyocr
```

### 2. Add your PDF file

Place your input file as `sample.pdf` in the same folder, or change the filename in the script.

### 3. Create Python file

Create a file named `extract_text.py` and paste this code inside:

```python
import fitz  # PyMuPDF
from PIL import Image
import easyocr
import io
import numpy as np

# Initialize EasyOCR
reader = easyocr.Reader(['en'])  # Add 'hi' for Hindi: ['en', 'hi']

# Input PDF
pdf_path = "sample.pdf"

# Extract text
doc = fitz.open(pdf_path)
normal_text = ""
ocr_text = ""

for page_num in range(len(doc)):
    page = doc[page_num]
    normal_text += page.get_text()

    pix = page.get_pixmap(dpi=200)
    img_bytes = pix.tobytes("png")
    img = Image.open(io.BytesIO(img_bytes))
    img_np = np.array(img)

    results = reader.readtext(img_np)
    for _, text, _ in results:
        ocr_text += text + "\n"

doc.close()

# Combine
complete_text = normal_text + "\n" + ocr_text

# Save
with open("extracted_text_easyocr.txt", "w", encoding="utf-8") as f:
    f.write(complete_text)

print("✅ Text extraction completed and saved to 'extracted_text_easyocr.txt'")
```

### 4. Run the script

Open the terminal in VS Code and run:

```bash
python extract_text.py
```

---

## 📦 Output

Your result will be saved in:

```
extracted_text_easyocr.txt
```

It will include both:

* Text from digitally generated PDFs
* OCR output from scanned or image-based pages

---

## 📝 Sample Output (Preview)

```text
This is sample text from Page 1.

--- OCR Text ---
Invoice Number: 123456
Date: 2025-08-14
Total Amount: ₹1,250.00
```

---

## ⚠️ Notes

* You’ll see a warning: `Neither CUDA nor MPS are available` → It's safe to ignore. It just means EasyOCR is using CPU.
* If you want to **speed up processing**, run it on a machine with a GPU (NVIDIA supported).
* Use languages like Hindi by changing:

  ```python
  reader = easyocr.Reader(['en', 'hi'])
  ```

---

## 📚 Future Improvements

* Save output to `.json` or `.csv`
* Extract table structures
* Add a simple GUI with `Tkinter` or `Streamlit`
* Support for batch processing multiple PDFs

---

## 🧑‍🔧 Author

Made with ❤️ for PDF text automation projects using Python.

---

```

Let me know if you want the `README.md` saved as a downloadable file or extended with:
- Table extraction
- Hindi support
- JSON output

I can help you generate all of that too.
```




















































































****



****

****

****
