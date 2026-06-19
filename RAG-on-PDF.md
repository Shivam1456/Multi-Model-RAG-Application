



---


Here's the Mermaid diagram for your PDF processing and RAG system, accurately representing the code flow:

```mermaid
graph TD
    A["Start"] --> B["Load .env & Configure API"]
    B --> C{"API Key Valid?"}
    C -->|Yes| D["Open PDF (PyMuPDF)"]
    C -->|No| E["Raise ValueError"]
    D --> F["Extract Linear Docs"]
    F --> G["Process Text Blocks"]
    F --> H["Process Image Blocks"]
    G --> I["Create Text Document"]
    H --> J{"Image Extracted?"}
    J -->|Yes| K["OCR with Gemini"]
    J -->|No| L["Rasterize to PIL"]
    L --> K
    K --> M["Create OCR Document"]
    I --> N["Combine Documents"]
    M --> N
    D --> O["PDFPlumber Tables?"]
    O -->|Yes| P["Extract Structured Tables"]
    O -->|No| Q["Skip Table Extraction"]
    P --> N
    N --> R["Derive Tables from Text"]
    R --> S["Chunk Documents"]
    S --> T{"Is Table?"}
    T -->|Yes| U["Keep as Single Chunk"]
    T -->|No| V["Split with TextSplitter"]
    U --> W["Create FAISS Vector Store"]
    V --> W
    W --> X["Setup Retriever (k=6)"]
    X --> Y["Create RAG Chain"]
    Y --> Z["Interactive Query Loop"]
    Z --> AA{"Ask Question"}
    AA -->|Query| AB["Retrieve & Generate"]
    AB --> AC{"Success?"}
    AC -->|Yes| AD["Display Answer"]
    AC -->|No| AE{"Retries > 0?"}
    AE -->|Yes| AF["Retry with k=3"]
    AE -->|No| AG["Raise Error"]
    AF --> AD
    AA -->|Exit| AH["End"]

    %% Detailed Sub-processes
    subgraph PDF Processing
        F -->|Blocks| G
        F -->|Images| H
        O -->|"extract_tables()"| P
        P -->|"serialize_rows()"| N
    end

    subgraph Table Handling
        R -->|"try_vertical_columns_to_rows()"| S
        T -->|"CSV/TSV/JSONL"| U
    end

    subgraph RAG System
        X -->|"GoogleGenerativeAIEmbeddings"| Y
        Y -->|"ChatGoogleGenerativeAI"| Z
        AB -->|"similarity_search()"| AC
    end

    subgraph Error Handling
        AC -->|"Exception"| AE
        AG -->|"Fallback"| AH
    end
```

Key features represented:
1. **PDF Processing Path** (left branch):
   - Text extraction → Document creation
   - Image processing → OCR → Document creation
   - Optional PDFPlumber table extraction

2. **Table Handling**:
   - Special logic for table preservation
   - Vertical column detection
   - CSV/TSV/JSONL serialization

3. **RAG Pipeline**:
   - Chunking with table preservation
   - FAISS vector store with cosine similarity
   - Retriever with fallback mechanism

4. **Error Recovery**:
   - API key validation
   - OCR failure handling
   - Retry mechanism with reduced chunk count

The diagram maintains all key components from your code while organizing them into logical subsystems. Each decision point and fallback mechanism is explicitly represented.

---


```mermaid
graph TD
    A["Start"] --> B["Load .env and Configure GOOGLE_API_KEY | Libraries: dotenv, google.generativeai | Methods: load_dotenv, genai.configure"]
    B -->|"Check API Key"| C{"API Key Valid?"}
    C -->|"Yes"| D["Open PDF | Library: fitz | Method: fitz.open"]
    C -->|"No"| E["Raise ValueError | Library: os"]
    D --> F["Extract Linear Docs | Library: fitz | Method: extract_linear_docs"]
    F -->|"Process Pages"| G["Get Text Blocks (type=0) | Library: fitz | Method: page.get_text"]
    F -->|"Process Images"| H["Get Image Blocks (type=1) | Library: fitz | Method: page.get_text"]
    G --> I["Create Document (selectable_text_docs) | Library: langchain_core | Method: Document"]
    H -->|"Try Extract Image"| J{"PIL Image Extracted?"}
    J -->|"Yes"| K["OCR with Gemini | Libraries: PIL, google.generativeai | Methods: pdf.extract_image, ocr_with_gemini"]
    J -->|"No"| L["Rasterize Bbox to PIL | Libraries: fitz, PIL | Methods: _pil_from_bbox, page.get_pixmap"]
    L --> K
    K -->|"If OCR Text"| M["Create Document (ocr_image_docs) | Library: langchain_core | Method: Document"]
    I --> N["Append to linear_docs | Library: langchain_core"]
    M --> N
    N --> O["Save Linearized Output (pdf_linearized.txt) | Libraries: pathlib, io | Method: open"]
    N --> P["Save Selectable Text (pdf_raw_text.txt) | Libraries: pathlib, io | Method: open"]
    N --> Q["Save OCR Text (pdf_ocr_text.txt) | Libraries: pathlib, io | Method: open"]
    N --> R["Chunk Linear Docs | Library: langchain_text_splitters | Method: splitter.split_documents"]
    R --> S["Save Chunks (chunks.txt) | Libraries: pathlib, io | Method: open"]
    R --> T["Embed Chunks | Library: langchain_google_genai | Method: GoogleGenerativeAIEmbeddings"]
    T --> U["Create FAISS Vector Store (Cosine Similarity) | Library: langchain_community | Method: FAISS.from_documents"]
    U --> V["Setup Retriever (k=6) | Library: langchain_community | Method: vectorstore.as_retriever"]
    V --> W["Create RAG Chain | Libraries: langchain_google_genai, langchain_core | Methods: ChatGoogleGenerativeAI, create_stuff_documents_chain, create_retrieval_chain"]
    W --> X["Interactive Query Loop | Library: os | Method: input"]
    X -->|"User Input"| Y{"Ask Question"}
    Y -->|"Invoke RAG"| Z["Retrieve and Generate Answer | Libraries: langchain_core, langchain_community | Method: rag_chain.invoke"]
    Z -->|"Success"| AA["Display Answer and Sources | Library: os | Method: print"]
    Z -->|"Fail"| AB{"Retries > 0?"}
    AB -->|"Yes"| AC["Retry with k=3 | Library: langchain_community | Methods: vectorstore.as_retriever, create_retrieval_chain"]
    AB -->|"No"| AD["Raise Exception"]
    AC --> AA
    X -->|"Exit"| AE["End"]
```


---

```mermaid
graph TD
    %% Initialization
    A[("Start")] --> B[Load Config]
    B --> C{API Key Valid?}
    C -->|Yes| D[Open PDF]
    C -->|No| E[Error Exit]

    %% Content Extraction
    D --> F[Process PDF]
    F --> G[Extract Text]
    F --> H[Extract Images]

    %% Text Processing Path
    G --> I[Create Text Docs]
    
    %% Image Processing Path
    H --> J{Image Extract?}
    J -->|Success| K[Run OCR]
    J -->|Fail| L[Rasterize BBox]
    L --> K
    K --> M[Create OCR Docs]

    %% Document Processing
    I --> N[Combine Documents]
    M --> N

    %% Output Files
    N --> O[Save Outputs]

    %% RAG Pipeline
    N --> P[Chunk Documents]
    P --> Q[Generate Embeddings]
    Q --> R[Build FAISS Index]
    R --> S[Create Retriever]
    S --> T[Setup RAG Chain]

    %% Query Handling
    T --> U[Query Loop]
    U --> V{Question?}
    V -->|Yes| W[Generate Answer]
    W --> X[Show Results]
    W -->|Error| Y{Retry?}
    Y -->|Yes| Z[Reduce Scope]
    Y -->|No| AA[Fail]
    Z --> X
    V -->|Exit| AB[End]

    %% Library/Method Annotations
    B -.->|dotenv.load_dotenv<br>os.getenv| B
    D -.->|fitz.open| D
    G -.->|page.get_text| G
    H -.->|block.get| H
    I -.->|langchain_core.Document| I
    K -.->|PIL.Image.open<br>ocr_with_gemini| K
    L -.->|_pil_from_bbox| L
    M -.->|langchain_core.Document| M
    O -.->|pathlib.Path.open| O
    P -.->|RecursiveTextSplitter| P
    Q -.->|GoogleGenerativeAIEmbeddings| Q
    R -.->|FAISS.from_documents| R
    S -.->|as_retriever| S
    T -.->|create_retrieval_chain| T
    W -.->|rag_chain.invoke| W

    %% Styling
    classDef process fill:#e6f3ff,stroke:#0066cc;
    classDef decision fill:#ffeb99,stroke:#ffcc00;
    classDef data fill:#e6ffe6,stroke:#009900;
    classDef output fill:#f5f5f5,stroke:#696969;
    classDef api fill:#ffe6e6,stroke:#cc0000;
    classDef annotation fill:none,stroke:none;

    class A,B,D,F,G,H,I,J,K,L,M,N,P,Q,R,S,T,U,V,W,X,Y,Z,AA,AB process;
    class C,E,J,V,Y decision;
    class O data;
    class Q,T,W api;
    style annotation fill:none,stroke:none,color:#666;
```


# RAG on PDF (Text + OCR, Reading Order)

Minimal RAG pipeline that:

* pulls **selectable text** + **OCR from images** in the **same order** as the PDF,
* builds a **FAISS** index with **cosine-like** retrieval,
* answers questions **only from the PDF** with page citations,
* runs in an **interactive** terminal loop.



---

Here’s a clean **Project Structure** you can drop into your README:

```
.
├─ data/
│  └─ sample.pdf            # your PDF (change path in main.py if needed)
├─ main.py                  # extraction + OCR + chunk + FAISS + RAG Q&A
├─ .env                     # GOOGLE_API_KEY=...
├─ README.md                # this file
└─ (generated at runtime)
   ├─ pdf_linearized.txt    # reading-order text (selectable + OCR)
   ├─ pdf_raw_text.txt      # per-page selectable text
   ├─ pdf_ocr_text.txt      # per-image OCR text
   └─ chunks.txt            # chunk dump for inspection
```

*(Optional)* If you keep a virtual environment:

```
venv/                       # your local Python venv (not committed)
```



---

## Requirements

* Python 3.10+
* Google Generative AI API key

```bash
pip install pymupdf pillow python-dotenv langchain langchain-community langchain-google-genai faiss-cpu google-generativeai
```

Create a `.env` file:

```
GOOGLE_API_KEY=your_key_here
```

Place your PDF at `data/sample.pdf` (or change the path in `main.py`).

---

## Run

```bash
python main.py
```

You’ll be prompted:

```
❓ Enter your query (or 'exit' to quit):
```

Ask things like:

* Who is the candidate?
* How many projects are listed?
* Summarize responsibilities (with cites).

---

## What the script does

1. **Extract (reading order)**
   Uses PyMuPDF to iterate blocks in order:

   * Text blocks → text
   * Image blocks → try embedded image; if not, rasterize the area and OCR with Gemini Vision

2. **Chunk**
   Chunks are built from the linear (text+OCR) sequence so order is preserved.

3. **Embed & Index**
   Uses Google embeddings + FAISS (`normalize_L2=True`) and retrieves top-k similar chunks.

4. **Answer**
   Answers only from the provided context and cites pages like `(p. X)`.

---

## Outputs (generated)

* `pdf_linearized.txt` — reading order (text + OCR)
* `pdf_raw_text.txt` — selectable text per page
* `pdf_ocr_text.txt` — OCR text per image
* `chunks.txt` — chunk dump (for inspection)

---

## Config (edit in `main.py`)

```python
PDF_PATH = pathlib.Path("data/sample.pdf")

OCR_MODEL  = "gemini-1.5-flash"
CHAT_MODEL = "gemini-1.5-flash"
EMBED_MODEL = "models/text-embedding-004"

MAX_OCR_IMAGES_PER_DOC = None  # set to 0 to disable OCR, or a small number to limit cost
OCR_DELAY_SEC = 0.2

# Chunking & retrieval
chunk_size = 1000       # via RecursiveCharacterTextSplitter
chunk_overlap = 120
k = 6                   # retriever top-k
```

```python
#main.py
# main.py
import os, io, time, pathlib
import fitz  # PyMuPDF
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain

# ===================== Setup =====================
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "").strip()
if not GOOGLE_API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY missing. Put it in .env as GOOGLE_API_KEY=your_key")

genai.configure(api_key=GOOGLE_API_KEY)

PDF_PATH = pathlib.Path("data/sample.pdf")  # change as needed

# Controls
OCR_MODEL = "gemini-1.5-flash"
CHAT_MODEL = "gemini-1.5-flash"
EMBED_MODEL = "models/text-embedding-004"
MAX_OCR_IMAGES_PER_DOC = None   # e.g., 10 to limit OCR calls
OCR_DELAY_SEC = 0.2             # small delay between OCR calls

# ===================== Helpers =====================
def ocr_with_gemini(pil_img, model_name=OCR_MODEL):
    """Return plain text OCR via Gemini Vision."""
    model = genai.GenerativeModel(model_name)
    prompt = (
        "Extract ONLY the legible text visible in this image.\n"
        "Preserve line breaks and order.\n"
        "Return plain text only."
    )
    resp = model.generate_content([prompt, pil_img])
    return (getattr(resp, "text", "") or "").strip()

def _coerce_xref(image_field):
    """Try to convert various 'image' field shapes to an int xref."""
    if image_field is None:
        return None
    if isinstance(image_field, int):
        return image_field
    if isinstance(image_field, dict):
        for k in ("xref", "number", "id"):
            v = image_field.get(k)
            if isinstance(v, int):
                return v
            if isinstance(v, (bytes, bytearray)):
                try:
                    return int(v.decode("ascii"))
                except Exception:
                    pass
            if isinstance(v, str) and v.isdigit():
                return int(v)
        return None
    if isinstance(image_field, (bytes, bytearray)):
        try:
            return int(image_field.decode("ascii"))
        except Exception:
            return None
    if isinstance(image_field, str) and image_field.isdigit():
        return int(image_field)
    return None

def _pil_from_bbox(page, bbox, scale=2.0):
    """Rasterize a clipped region (bbox) to a PIL image as a robust fallback."""
    rect = fitz.Rect(bbox)
    matrix = fitz.Matrix(scale, scale)  # upscale for clearer OCR
    pix = page.get_pixmap(matrix=matrix, clip=rect, alpha=False)
    mode = "RGB" if pix.n < 4 else "RGBA"
    img = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    if img.mode != "RGB":
        img = img.convert("RGB")
    return img

def extract_linear_docs(pdf_path: str):
    """
    Extract text and images in the SAME reading order as the PDF:
    - Use page.get_text('dict') to iterate blocks in order
    - type=0 (text): append text
    - type=1 (image): extract by xref, else rasterize bbox and OCR
    Returns: (linear_docs, selectable_text_docs, ocr_image_docs)
    """
    linear_docs = []
    selectable_text_docs = []
    ocr_image_docs = []

    ocr_count = 0
    with fitz.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf, start=1):
            layout = page.get_text("dict")  # preserves reading order
            blocks = layout.get("blocks", [])

            for b_idx, block in enumerate(blocks, start=1):
                btype = block.get("type", 0)
                bbox = block.get("bbox", None)

                if btype == 0:
                    # TEXT block
                    text_parts = []
                    for line in block.get("lines", []):
                        spans = line.get("spans", [])
                        if spans:
                            text_parts.append("".join(span.get("text", "") for span in spans))
                    text = "\n".join([t for t in text_parts if t is not None]).strip()
                    if text:
                        doc = Document(
                            page_content=text,
                            metadata={
                                "source": str(pdf_path),
                                "page": page_num,
                                "type": "page_text",
                                "block_index": b_idx,
                                "bbox": bbox
                            }
                        )
                        selectable_text_docs.append(doc)
                        linear_docs.append(doc)

                elif btype == 1:
                    # IMAGE block
                    image_field = block.get("image", None)
                    xref = _coerce_xref(image_field)

                    pil_img = None
                    try:
                        if xref is not None:
                            base_img = pdf.extract_image(xref)
                            image_bytes = base_img.get("image")
                            if image_bytes:
                                pil_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                    except Exception:
                        # ignore and fall back to bbox
                        pass

                    # Fallback: rasterize the block's bbox area
                    if pil_img is None and bbox is not None:
                        try:
                            pil_img = _pil_from_bbox(page, bbox, scale=2.0)
                        except Exception as e:
                            print(f"⚠️ Failed to rasterize bbox on page {page_num}, block {b_idx}: {e}")

                    if pil_img is None:
                        # give up on this image block
                        continue

                    # Respect OCR limit if any
                    if (MAX_OCR_IMAGES_PER_DOC is not None) and (ocr_count >= MAX_OCR_IMAGES_PER_DOC):
                        ocr_text = ""
                    else:
                        try:
                            ocr_text = ocr_with_gemini(pil_img, OCR_MODEL)
                        except Exception as e:
                            print(f"⚠️ OCR failed on page {page_num}, block {b_idx}: {e}")
                            ocr_text = ""
                        ocr_count += 1
                        if OCR_DELAY_SEC:
                            time.sleep(OCR_DELAY_SEC)

                    if ocr_text:
                        doc = Document(
                            page_content=ocr_text,
                            metadata={
                                "source": str(pdf_path),
                                "page": page_num,
                                "type": "ocr_image",
                                "block_index": b_idx,
                                "image_xref": xref,
                                "bbox": bbox
                            }
                        )
                        ocr_image_docs.append(doc)
                        linear_docs.append(doc)

                else:
                    # ignore drawings/other types
                    continue

    return linear_docs, selectable_text_docs, ocr_image_docs

# ===================== Load + Linearize =====================
if not PDF_PATH.exists():
    raise FileNotFoundError(f"❌ PDF not found at {PDF_PATH.resolve()}")

print(f"🔎 Loading {PDF_PATH.name} and preserving reading order...")
linear_docs, text_docs, ocr_docs = extract_linear_docs(str(PDF_PATH))
print(f"✅ Linear items: {len(linear_docs)}  |  Text blocks: {len(text_docs)}  |  OCR image blocks: {len(ocr_docs)}")

# ===================== Save EXACT order to file =====================
linear_file = pathlib.Path("pdf_linearized.txt")
with open(linear_file, "w", encoding="utf-8") as f:
    if linear_docs:
        current_page = None
        for i, doc in enumerate(linear_docs, start=1):
            page = doc.metadata.get("page")
            if page != current_page:
                f.write(f"\n===== Page {page} =====\n")
                current_page = page
            dtype = doc.metadata.get("type")
            f.write(f"\n--- Item #{i} [{dtype}] ---\n")
            f.write(doc.page_content.strip() + "\n")
    else:
        f.write("(No text or OCR content found)\n")
print(f"💾 Linearized (text+image OCR) saved to {linear_file.resolve()}")

# (Optional) Also save pure selectable text per page
raw_text_file = pathlib.Path("pdf_raw_text.txt")
with open(raw_text_file, "w", encoding="utf-8") as f:
    if text_docs:
        by_page = {}
        for d in text_docs:
            by_page.setdefault(d.metadata["page"], []).append(d.page_content)
        for p in sorted(by_page):
            f.write(f"--- Page {p} (selectable text) ---\n")
            f.write("\n".join(by_page[p]).strip() + "\n\n")
    else:
        f.write("(No selectable text found)\n")
print(f"💾 Raw selectable text saved to {raw_text_file.resolve()}")

# (Optional) Save OCR text per image occurrence
ocr_text_file = pathlib.Path("pdf_ocr_text.txt")
with open(ocr_text_file, "w", encoding="utf-8") as f:
    if ocr_docs:
        for doc in ocr_docs:
            p = doc.metadata.get("page")
            xref = doc.metadata.get("image_xref")
            f.write(f"--- Page {p}, Image xref {xref} (OCR) ---\n")
            f.write(doc.page_content.strip() + "\n\n")
    else:
        f.write("(No OCR text found)\n")
print(f"💾 OCR text saved to {ocr_text_file.resolve()}")

# ===================== Chunking in SAME order =====================
# Use linear_docs (already in exact order)
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=120)
chunks = splitter.split_documents(linear_docs)

print(f"📚 Chunks (from linear order): {len(chunks)}\n")

chunks_file = pathlib.Path("chunks.txt")
with open(chunks_file, "w", encoding="utf-8") as f:
    for i, chunk in enumerate(chunks, start=1):
        chunk_text = chunk.page_content.strip()
        f.write(f"--- Chunk {i} ---\n")
        f.write(chunk_text + "\n")
        f.write(f"Metadata: {chunk.metadata}\n\n")

        # Console preview
        print(f"--- Chunk {i} ---")
        print(chunk_text)
        print(f"Metadata: {chunk.metadata}\n")

print(f"💾 All chunks saved to {chunks_file.resolve()}")

# ===================== Embed + Index (COSINE) =====================
try:
    embeddings = GoogleGenerativeAIEmbeddings(model=EMBED_MODEL)
except Exception as e:
    print(f"⚠️ Falling back to older embedding model due to: {e!r}")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

# normalize_L2=True makes L2 distance equivalent to cosine distance on unit vectors
vectorstore = FAISS.from_documents(chunks, embedding=embeddings, normalize_L2=True)
retriever = vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 6})
print("✅ Retriever ready (cosine)")

# (Optional) debug helper to see cosine scores
def debug_cosine_search(query: str, k: int = 6):
    results = vectorstore.similarity_search_with_score(query, k=k)
    out = []
    for doc, dist in results:
        cosine = 1.0 - (dist / 2.0)  # ||a-b||^2 = 2(1 - cosθ) → cos = 1 - d/2
        out.append((doc, float(cosine)))
    return out

# ===================== RAG chain =====================
llm = ChatGoogleGenerativeAI(
    model=CHAT_MODEL,
    temperature=0.2,
    max_output_tokens=256,
)

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful assistant. Use only the provided CONTEXT from the PDF to answer. "
     "If something is not in the CONTEXT, say you don't know. "
     "Cite page numbers like (p. X) for answers grounded in the CONTEXT. "
     "Answer clearly and concisely."),
    ("human",
     "QUESTION:\n{input}\n\nCONTEXT:\n{context}")
])

combine_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, combine_chain)
print("✅ RAG chain ready")

def ask(question: str, retries: int = 1):
    try:
        res = rag_chain.invoke({"input": question})
        print("\n💬 ANSWER:\n", res["answer"])
        print("\n🔗 SOURCES:")
        for d in res.get("context", []):
            print(f"- Page {d.metadata.get('page')}, Type: {d.metadata.get('type')}")
        return res
    except Exception as e:
        print("\n⚠️ Generation failed:", repr(e))
        if retries > 0:
            print("⏳ Retrying once with fewer retrieved chunks...")
            small_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
            small_chain = create_retrieval_chain(small_retriever, combine_chain)
            res = small_chain.invoke({"input": question})
            print("\n💬 ANSWER (retry):\n", res["answer"])
            print("\n🔗 SOURCES:")
            for d in res.get("context", []):
                print(f"- Page {d.metadata.get('page')}, Type: {d.metadata.get('type')}")
            return res
        else:
            raise

if __name__ == "__main__":
    while True:
        question = input("\n❓ Enter your query (or 'exit' to quit): ").strip()
        if not question or question.lower() in {"exit", "quit"}:
            print("👋 Exiting.")
            break
        _ = ask(question)
        # Uncomment to see cosine scores for debugging:
        # for i, (d, s) in enumerate(debug_cosine_search(question), 1):
        #     print(f"{i}. cos={s:.3f}  p={d.metadata.get('page')}  type={d.metadata.get('type')}")


```


---

## Tips

* Missed info? Try increasing `k` (e.g., 8–10) or `chunk_size` (e.g., 1200–1600).
* OCR quota/cost: set `MAX_OCR_IMAGES_PER_DOC` to a small number during testing or `0` to disable.

---

## Troubleshooting

* **`❌ GOOGLE_API_KEY missing`** → Add `.env` and restart the shell.
* **FAISS install issues**:

  ```bash
  pip uninstall faiss faiss-gpu faiss-cpu
  pip install faiss-cpu
  ```
* **Windows paths with spaces** → keep the default `data/sample.pdf` or use quoted paths.
