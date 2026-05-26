Here's the fully rewritten README in English with a polished, high-quality GitHub style:

---

<div align="center">

<img src="https://img.shields.io/badge/version-1.0.0-blue?style=flat-square" /> <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" /> <img src="https://img.shields.io/badge/python-3.10+-blue?style=flat-square&logo=python" /> <img src="https://img.shields.io/badge/node-18+-green?style=flat-square&logo=node.js" /> <img src="https://img.shields.io/badge/FastAPI-async-009688?style=flat-square&logo=fastapi" /> <img src="https://img.shields.io/badge/Vue-3-42b883?style=flat-square&logo=vue.js" />

# 🏛️ Campus Indoor Navigation System

**A mobile-first indoor navigation web app with AI-powered visual localization, multi-floor pathfinding, and natural language queries.**

[Getting Started](#-quick-start) · [API Reference](#-api-reference) · [Architecture](#-project-structure) · [Deployment](#-deployment)

</div>

---

## ✨ Features

| Feature                    | Description                                                                                  |
| -------------------------- | -------------------------------------------------------------------------------------------- |
| 📸 **Visual Localization** | Upload a photo of your surroundings — CLIP + ChromaDB identifies your location automatically |
| 🔍 **Destination Search**  | Fuzzy keyword search across all mapped locations                                             |
| 🗺️ **Path Planning**       | A\* algorithm computes the shortest path, with full multi-floor support                      |
| 🧭 **Visual Navigation**   | Real-time 2D and 3D map views with animated route overlays                                   |
| ✏️ **Map Editor**          | Drag-and-drop node placement on uploaded floor plans                                         |
| 🤖 **Intelligent Chat**    | Natural language navigation queries powered by OpenAI function calling                       |
| 🌐 **External Navigation** | Google Maps integration for routes beyond campus                                             |
| 🏗️ **3D Map View**         | Three-dimensional floor-stacked visualization with path rendering                            |

---

## 🛠️ Tech Stack

### Backend

- **FastAPI** — fully async web framework
- **SQLAlchemy Async + SQLite** — zero-config async ORM with file-based database
- **Alembic** — database schema migrations
- **Pydantic V2** — data validation and serialization
- **A\* Algorithm** — heuristic shortest-path planning
- **OpenAI API** — LLM integration with tool/function calling
- **Google Maps API** — external routing service
- **CLIP + ChromaDB** — image feature extraction and vector similarity search
- **Pillow** — image processing

### Frontend

- **Vue 3 + TypeScript + Vite** — modern, type-safe frontend with fast HMR
- **Vant UI** — mobile-first component library
- **Pinia** — Vue 3 official state management
- **Vue Router 4** — client-side routing
- **Canvas API + CSS 3D** — 2D/3D map rendering
- **Tailwind CSS** — utility-first styling
- **Axios** — HTTP client
- **Marked** — Markdown rendering

---

## 📂 Project Structure

```
campus-indoor-nav/
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI app entry point
│   │   ├── core/config.py              # App configuration
│   │   ├── api/endpoints/
│   │   │   ├── navigation.py           # Navigation API
│   │   │   ├── recognition.py          # Image recognition API
│   │   │   ├── maps.py                 # Maps management API
│   │   │   └── chat.py                 # Intelligent chat API
│   │   ├── models/
│   │   │   ├── node.py                 # Node model
│   │   │   ├── edge.py                 # Edge model
│   │   │   └── map.py                  # Map model
│   │   ├── schemas/                    # Pydantic schemas
│   │   ├── services/
│   │   │   ├── graph_service.py        # Graph algorithms & path planning
│   │   │   ├── vision_client.py        # Visual recognition service
│   │   │   ├── navigation_client.py    # External navigation client
│   │   │   └── ai_service.py           # AI service layer
│   │   ├── utils/navigation_text.py    # Navigation instruction generation
│   │   └── db/database.py             # Database connection
│   ├── data/
│   │   ├── campus_nav.db              # SQLite database
│   │   └── maps/                      # Floor plan image storage
│   ├── scripts/
│   │   ├── import_map_data.py         # Single-file map data import
│   │   ├── import_nodes_and_edges.py  # Smart graph import
│   │   └── export_node_coordinates.py # Coordinate export utility
│   ├── alembic/                       # Database migrations
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── main.ts
│   │   ├── App.vue
│   │   ├── api/index.ts               # Typed API client
│   │   ├── components/
│   │   │   ├── Map3DInterface.vue     # 3D map interface
│   │   │   ├── AgentChat.vue          # AI chat assistant
│   │   │   ├── NavigationMap.vue      # Navigation map view
│   │   │   ├── MapCanvas.vue          # Map canvas renderer
│   │   │   └── ZoomableMapCanvas.vue  # Pannable/zoomable canvas
│   │   ├── views/
│   │   │   ├── Home.vue
│   │   │   ├── Navigation.vue
│   │   │   ├── MapEditor.vue
│   │   │   ├── Map3DView.vue
│   │   │   └── Recognition.vue
│   │   ├── stores/
│   │   │   ├── navigation.ts
│   │   │   └── editor.ts
│   │   └── router/index.ts
│   ├── package.json
│   ├── vite.config.ts
│   └── tailwind.config.js
│
├── image_data/                        # Location image dataset
│   ├── L1/                            # Floor 1 images
│   ├── L2/                            # Floor 2 images
│   └── ...
├── chroma/                            # Vector database storage
├── project1230/                       # Map graph data (JSON)
├── key.py                             # API key configuration
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+** (3.11 recommended)
- **Node.js 18+** (20+ recommended)
- **SQLite 3** (bundled with Python — no separate install needed)
- **Optional:** CUDA-capable GPU for accelerated CLIP inference

### 1. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp key.py.example key.py
# Edit key.py — add your OpenAI and Google Maps API keys

# Import map data (choose one approach)
python scripts/import_map_data.py ../project1230/campus_map.json --clear          # single file
python scripts/import_map_data_batch.py ../project1230/*.json --clear             # glob pattern
python scripts/import_map_data_batch.py ../project1230/ --clear                   # entire directory

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### 3. Access the App

| Service      | URL                          |
| ------------ | ---------------------------- |
| Frontend     | http://localhost:5173        |
| Backend API  | http://localhost:8000        |
| Swagger UI   | http://localhost:8000/docs   |
| Health Check | http://localhost:8000/health |

---

## 📡 API Reference

### Navigation

| Method | Endpoint                    | Description                    |
| ------ | --------------------------- | ------------------------------ |
| `POST` | `/api/v1/navigation/route`  | Compute navigation route       |
| `GET`  | `/api/v1/navigation/search` | Search nodes by keyword        |
| `GET`  | `/api/v1/navigation/nodes`  | List all nodes                 |
| `POST` | `/api/v1/navigation/reload` | Reload graph structure from DB |

### Image Recognition

| Method | Endpoint                        | Description                  |
| ------ | ------------------------------- | ---------------------------- |
| `POST` | `/api/v1/recognition/recognize` | Identify location from photo |

### Map Management

| Method | Endpoint                           | Description                    |
| ------ | ---------------------------------- | ------------------------------ |
| `POST` | `/api/v1/maps/upload`              | Upload a floor plan image      |
| `GET`  | `/api/v1/maps/{floor}`             | Get floor plan by floor number |
| `GET`  | `/api/v1/maps/`                    | List all floor plans           |
| `PUT`  | `/api/v1/maps/nodes/{id}/position` | Update node coordinates        |
| `PUT`  | `/api/v1/maps/nodes/batch-update`  | Batch update node coordinates  |

### Intelligent Chat

| Method | Endpoint      | Description                       |
| ------ | ------------- | --------------------------------- |
| `POST` | `/api/chat`   | Natural language navigation query |
| `GET`  | `/api/status` | Service health status             |
| `GET`  | `/api/config` | Runtime configuration info        |

---

## 🗃️ Data Format

Map graphs are defined as JSON with `nodes` (locations) and `edges` (connections):

```json
{
  "nodes": [
    {
      "id": "LT5",
      "name": "LectureTheater5",
      "detail": "NS2-02-07",
      "floor": 2
    }
  ],
  "edges": [
    {
      "from": "LT5",
      "to": "LT6",
      "weight": 20
    }
  ]
}
```

---

## 🧩 How It Works

### 1. Data Preparation

Use `scripts/import_map_data_batch.py` to bulk-import JSON map files. The script supports single files, directories, and glob patterns, and populates nodes and edges in the SQLite database.

### 2. Map Configuration

Upload floor plan images (PNG/JPG) through the Map Editor. Then drag nodes onto their correct positions — coordinates are stored as pixel offsets from the top-left origin.

### 3. AI Model Setup

On first launch, the system automatically downloads the CLIP model (`openai/clip-vit-base-patch32`) and builds a ChromaDB vector index from the `image_data/` directory. For development without GPU access, enable **Mock Mode** to skip model loading and return randomized candidates.

### 4. Navigation

- **Basic**: Enter a destination keyword on the home screen — the A\* engine computes and displays the shortest route.
- **AI Chat**: Ask in natural language (e.g., _"Where's the nearest printer?"_). The LLM calls the appropriate tool and returns a conversational response.
- **Visual Localization**: Upload a photo — CLIP extracts features, ChromaDB retrieves the top-K most similar indexed locations.

---

## 🏗️ Architecture Decisions

**Why SQLite?** Zero-ops setup for campus scale. Easily migrated to PostgreSQL for larger deployments via Alembic.

**Why A\*?** Optimal for sparse campus graphs. The graph is loaded once into memory at startup for sub-millisecond query times.

**Why CLIP + ChromaDB?** CLIP provides strong zero-shot visual features without task-specific fine-tuning. ChromaDB handles approximate nearest-neighbor search efficiently in-process.

---

## 🚢 Deployment

### Development

```bash
# Backend with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend with HMR
cd frontend && npm run dev
```

### Production (recommended)

- **Nginx** as reverse proxy with SSL termination
- **Docker** containerization (Dockerfile included)
- **Environment variables** for secrets (never commit `key.py`)
- **PostgreSQL** if scaling beyond SQLite limits
- **Redis** caching layer for graph queries

### Performance Notes

- Graph structure is cached in memory at startup
- Fully async I/O via FastAPI + SQLAlchemy async
- ChromaDB vector search is in-process (no network hop)
- Frontend uses virtual scrolling for large node lists

---

## 🔧 Troubleshooting

| Symptom                                   | Likely Cause                                     | Fix                                                                     |
| ----------------------------------------- | ------------------------------------------------ | ----------------------------------------------------------------------- |
| Backend fails to start                    | Missing API keys or wrong Python version         | Check `key.py` exists and Python ≥ 3.10                                 |
| Frontend build fails                      | Node.js version or missing packages              | Ensure Node ≥ 18, delete `node_modules` and re-run `npm install`        |
| Map not displaying                        | No floor plan uploaded or nodes lack coordinates | Upload a floor image in the Map Editor and set node positions           |
| Recognition always returns wrong location | ChromaDB index not built                         | Ensure `image_data/` is populated and the backend ran the indexing step |

---

## 🛣️ Roadmap

- [ ] FAISS integration for faster large-scale vector search
- [ ] OCR-assisted localization from signage images
- [ ] Offline PWA support for no-connectivity environments
- [ ] WebSocket-based real-time multi-user navigation

---

## 📄 License

MIT © Campus Indoor Navigation System contributors

---

<div align="center">

If this project helped you, consider giving it a ⭐

</div>
