

```mermaid
flowchart TD
    A[Start] --> B{Request Method?}
    B -->|GET| C[Render Form\nFlask]
    B -->|POST| D{Form Type?}
    
    D -->|PDF Upload| E[Validate PDF]
    E --> F[Save Temp File]
    F --> G[Extract Text]
    G -->|Selectable| H[PyMuPDF]
    G -->|Scanned| I[EasyOCR\nCRNN Model]
    H & I --> J[Chunk Text]
    J --> K[Gemini\nembedding-001]
    K --> L[Qdrant\nHNSW Index]
    L --> M[Update Session]
    M --> C
    
    D -->|Question| N[Validate Input]
    N --> O[Qdrant Search\nCosine Sim]
    O --> P[Get Context]
    P --> Q[Build Prompt]
    Q --> R[Gemini-2.0-Flash]
    R --> S[Format Answer]
    S --> T[Update History]
    T --> C
    
    D -->|Clear History| U[Reset Session]
    U --> C
    
    C --> V[Render Template]

    classDef tech fill:#f96,stroke:#333;
    classDef model fill:#6af,stroke:#333;
    classDef storage fill:#9f9,stroke:#333;
    
    class H,I,K,R model;
    class L,O storage;
    class E,F,G,J,N,P,Q,S,T,U,V tech;
```

### Model-to-Function Mapping Table:

| Step | Technology | Model Used | Model Type | Key Specs |
|------|------------|------------|------------|-----------|
| PDF Text Extract | PyMuPDF | - | Rule-based | PDF parsing |
| Scanned PDF OCR | EasyOCR | CRNN | CNN+LSTM | 90%+ accuracy |
| Text Embeddings | Gemini | embedding-001 | Transformer | 768-dim vectors |
| Vector Search | Qdrant | HNSW | Graph-based | Cosine similarity |
| Answer Generation | Gemini | gemini-2.0-flash | Transformer | 128K context |

### Legend:
- **Blue Nodes**: AI/ML Models
- **Green Nodes**: Storage/DB Systems
- **Orange Nodes**: Technical Processes


