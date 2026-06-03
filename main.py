# Project: PDF Q&A System With RAG
# Author: Imtiaz Adar
# Email: imtiazadarofficial@gmail.com

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, text
import os
import time
import shutil
from typing import Optional

from database import SessionLocal, init_db, QARecord, PDFDocument, engine
from models import QuestionRequest, FeedbackRequest
from rag_engine import rag_engine

os.makedirs("uploads", exist_ok=True)

app = FastAPI(title="PDF Q&A API with RAG", version="1.0.0", description="""This API powers a **Retrieval-Augmented Generation (RAG)** system that lets you upload PDF documents and ask natural language questions about their content.

### 🔥 Key Features
- **PDF Upload & Processing** - Upload any PDF, automatically chunked and indexed
- **Semantic Search** - Uses ChromaDB vector database for intelligent chunk retrieval
- **AI-Powered Answers** - Google Gemini generates accurate answers based ONLY on your PDF content
- **User Feedback** - Rate answers 1-5 stars to improve system understanding
- **Chat History** - Complete Q&A history with timestamps (Bangladesh timezone)

### 🛠️ How It Works
1. Upload a PDF → System extracts text and creates semantic chunks
2. Each chunk is converted to vector embeddings (384-dim)
3. Ask a question → System finds top-k relevant chunks via similarity search
4. Gemini synthesizes an answer using ONLY the retrieved context
5. Rate the answer to help track quality

### 📊 Technical Stack
- **FastAPI** - Async web framework
- **PostgreSQL** - Stores Q&A history and ratings
- **ChromaDB** - Vector database for semantic search
- **Gemini 1.5 Flash** - LLM for answer generation
- **Sentence Transformers** - Embedding generation (all-MiniLM-L6-v2)

### 📖 API Endpoints
- `POST /upload` - Upload a PDF file
- `POST /ask` - Ask a question about a PDF
- `POST /feedback/{qa_id}` - Rate an answer (1-5 stars)
- `GET /history` - View Q&A history
- `GET /stats` - System analytics
- `GET /pdfs` - List uploaded PDFs
- `DELETE /pdf/{filename}` - Remove a PDF

### 🌐 Web Interface
Visit `/web` for a full-featured chat interface.""", contact={
    "name": "Imtiaz Adar", "email": "imtiazadarofficial@gmail.com", "url": "https://tinyurl.com/Portfolio1Imtiaz"
})

def get_db():
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        print(f"Database connection error: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        db.close()

@app.on_event("startup")
async def startup_event():
    print("\n" + "="*50)
    print("🚀 Starting PDF Q&A API Server")
    print("="*50)
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ PostgreSQL connection: SUCCESS")
    except Exception as e:
        print(f"❌ PostgreSQL connection: FAILED - {e}")
    init_db()
    print(f"📚 API Docs: http://localhost:8000/docs")
    print(f"🌐 Web Interface: http://localhost:8000")
    print("="*50 + "\n")

@app.get("/", response_class=HTMLResponse)
async def root():
    return get_html()

@app.get("/web", response_class=HTMLResponse)
async def web():
    return get_html()

@app.get("/doc.png")
async def serve_logo():
    try:
        return FileResponse("doc.png", media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=404, detail="Logo not found")

def get_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Q&A System with RAG</title>
    <link rel="icon" type="image/png" href="/doc.png">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f5c3b 0%, #1a8f5a 50%, #0d4a2f 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header { text-align: center; color: white; margin-bottom: 30px; }
        .header h1 { font-size: 2.5rem; margin-bottom: 10px; text-shadow: 2px 2px 4px rgba(0,0,0,0.2); }
        .header p { font-size: 1.1rem; opacity: 0.95; }
        .developer-name {
            font-size: 1.2rem;
            margin-top: 15px;
            padding: 10px 20px;
            display: inline-block;
            background: rgba(255,255,255,0.2);
            border-radius: 50px;
            backdrop-filter: blur(5px);
        }
        .developer-name span { color: #ffd700; font-weight: bold; text-shadow: 0 0 10px rgba(255,215,0,0.5); }
        .main-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 20px;
        }
        .card h2 {
            color: #0d4a2f;
            margin-bottom: 20px;
            border-bottom: 2px solid #1a8f5a;
            padding-bottom: 10px;
        }
        .upload-area {
            border: 2px dashed #1a8f5a;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-area:hover { background: #e8f5ed; border-color: #0d4a2f; }
        .upload-area input { display: none; }
        select, textarea, button {
            width: 100%;
            padding: 12px;
            margin: 10px 0;
            border: 1px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
        }
        select:focus, textarea:focus {
            outline: none;
            border-color: #1a8f5a;
            box-shadow: 0 0 5px rgba(26,143,90,0.3);
        }
        button {
            background: linear-gradient(135deg, #0f5c3b 0%, #1a8f5a 100%);
            color: white;
            border: none;
            cursor: pointer;
            font-weight: bold;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); background: linear-gradient(135deg, #1a8f5a 0%, #0d4a2f 100%); }
        .chat-message {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
        }
        .question-message { background: #e8f5ed; border-left: 4px solid #1a8f5a; }
        .answer-message { background: #f0f7f3; border-left: 4px solid #0f5c3b; }
        .message-header { font-weight: bold; margin-bottom: 10px; color: #0d4a2f; }
        .history-answer-preview {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            padding: 5px;
            background: #f0f0f0;
            border-radius: 5px;
            font-style: italic;
        }

        .history-item {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            cursor: pointer;
            transition: all 0.2s;
        }

        .history-item:hover {
            transform: translateX(5px);
            background: #e8f5ed;
        }
        
        .rating-container {
            margin-top: 15px;
            padding-top: 10px;
            border-top: 1px solid #ddd;
        }
        .rating-label {
            font-size: 12px;
            color: #666;
            margin-bottom: 8px;
        }
        .rating-stars {
            display: flex;
            gap: 8px;
            margin: 10px 0;
        }
        .star {
            font-size: 32px;
            cursor: pointer;
            color: #ddd;
            transition: all 0.2s;
            background: none;
            border: none;
            padding: 0;
        }
        .star:hover {
            transform: scale(1.1);
            color: #ffc107;
        }
        .star.active { color: #ffc107; }
        .rating-feedback {
            font-size: 12px;
            color: #1a8f5a;
            margin-top: 5px;
        }
        
        .sources {
            background: #e8f5ed;
            border-radius: 8px;
            padding: 10px;
            margin-top: 10px;
            font-size: 12px;
        }
        .source-item {
            padding: 5px;
            margin: 5px 0;
            background: white;
            border-radius: 5px;
        }
        .history-item {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 15px;
            margin: 10px 0;
            cursor: pointer;
            transition: all 0.2s;
        }
        .history-item:hover { transform: translateX(5px); background: #e8f5ed; }
        .history-question { font-weight: bold; margin-bottom: 8px; color: #0d4a2f; }
        .history-rating { margin-top: 5px; font-size: 14px; }
        .stat-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-top: 15px;
        }
        .stat-card {
            background: linear-gradient(135deg, #0f5c3b 0%, #1a8f5a 100%);
            color: white;
            padding: 15px;
            border-radius: 10px;
            text-align: center;
        }
        .stat-value { font-size: 2rem; font-weight: bold; }
        .loading { text-align: center; padding: 20px; }
        .spinner {
            border: 3px solid #e8f5ed;
            border-top: 3px solid #1a8f5a;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        @media (max-width: 768px) { .main-grid { grid-template-columns: 1fr; } }
        .alert { padding: 12px; border-radius: 8px; margin: 10px 0; }
        .alert-success { background: #d4edda; color: #155724; }
        .alert-error { background: #f8d7da; color: #721c24; }
        .btn-rate {
            background: #1a8f5a;
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 15px;
            cursor: pointer;
            font-size: 12px;
            margin-left: 10px;
        }
        .btn-rate:hover { background: #0d4a2f; }
        
        .footer {
            margin-top: 40px;
            text-align: center;
            padding: 20px;
            background: rgba(255,255,255,0.1);
            border-radius: 15px;
            backdrop-filter: blur(5px);
        }
        .footer p { color: white; margin-bottom: 10px; }
        .social-links { display: flex; justify-content: center; gap: 20px; flex-wrap: wrap; }
        .social-link {
            color: white;
            text-decoration: none;
            padding: 8px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 25px;
            transition: all 0.3s;
            display: inline-flex;
            align-items: center;
            gap: 8px;
        }
        .social-link:hover {
            background: rgba(255,255,255,0.3);
            transform: translateY(-2px);
        }
        .social-link.x:hover { background: #000000; }
        .social-link.portfolio:hover { background: #ff6b35; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 PDF Q&A System with RAG</h1>
            <p>Upload PDFs, ask questions, and get AI-powered answers based ONLY on your documents</p>
            <div class="developer-name">
                Built with ❤️ by <span>Imtiaz Adar</span>
            </div>
        </div>
        <div class="main-grid">
            <div>
                <div class="card">
                    <h2>📤 Upload PDF</h2>
                    <div class="upload-area" onclick="document.getElementById('fileInput').click()">
                        <input type="file" id="fileInput" accept=".pdf" onchange="uploadPDF()">
                        <p>📄 Click or drag to upload PDF</p>
                    </div>
                    <div id="uploadStatus"></div>
                    <h2 style="margin-top: 20px;">❓ Ask Question</h2>
                    <select id="pdfSelect">
                        <option value="">Select a PDF first...</option>
                    </select>
                    <textarea id="questionInput" rows="3" placeholder="Type your question here..."></textarea>
                    <button onclick="askQuestion()">🤖 Ask AI</button>
                </div>
                <div class="card">
                    <h2>📊 Statistics</h2>
                    <div class="stat-grid">
                        <div class="stat-card"><div class="stat-value" id="totalQuestions">0</div><div class="stat-label">Questions</div></div>
                        <div class="stat-card"><div class="stat-value" id="avgTime">0</div><div class="stat-label">Avg Response (ms)</div></div>
                        <div class="stat-card"><div class="stat-value" id="pdfCount">0</div><div class="stat-label">PDFs</div></div>
                    </div>
                </div>
            </div>
            <div>
                <div class="card">
                    <h2>💬 Current Conversation</h2>
                    <div id="chatArea">
                        <p style="color:#999;text-align:center;">Ask a question to see the answer here</p>
                    </div>
                </div>
                <div class="card">
                    <h2>📜 Chat History (Click to load question)</h2>
                    <div id="historyArea">
                        <p style="color:#999;text-align:center;">Loading history...</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Connect with me</p>
            <div class="social-links">
                <a href="https://x.com/imtiazaadar" target="_blank" class="social-link x">
                    🐦 X (Twitter) - @imtiazaadar
                </a>
                <a href="https://tinyurl.com/Portfolio1Imtiaz" target="_blank" class="social-link portfolio">
                    🌐 Portfolio - Imtiaz Adar
                </a>
            </div>
            <p style="margin-top: 15px; font-size: 12px;">© 2026 Imtiaz Adar - RAG PDF Q&A System</p>
        </div>
    </div>

        <script>
        let currentQAId = null;

        async function loadPDFs() {
            try {
                const response = await fetch('/pdfs');
                const pdfs = await response.json();
                const select = document.getElementById('pdfSelect');
                select.innerHTML = '<option value="">Select a PDF...</option>';
                pdfs.forEach(pdf => {
                    select.innerHTML += `<option value="${pdf.filename}">${pdf.filename}</option>`;
                });
                document.getElementById('pdfCount').innerText = pdfs.length;
            } catch (error) { console.error(error); }
        }

        async function uploadPDF() {
            const file = document.getElementById('fileInput').files[0];
            if (!file) return;
            const formData = new FormData();
            formData.append('file', file);
            const statusDiv = document.getElementById('uploadStatus');
            statusDiv.innerHTML = '<div class="loading"><div class="spinner"></div><p>Uploading...</p></div>';
            try {
                const response = await fetch('/upload', { method: 'POST', body: formData });
                const data = await response.json();
                if (response.ok) {
                    statusDiv.innerHTML = `<div class="alert alert-success">✅ ${data.message}</div>`;
                    loadPDFs();
                    setTimeout(() => statusDiv.innerHTML = '', 3000);
                } else {
                    statusDiv.innerHTML = `<div class="alert alert-error">❌ ${data.detail}</div>`;
                }
            } catch (error) {
                statusDiv.innerHTML = `<div class="alert alert-error">❌ Upload failed</div>`;
            }
        }

        async function askQuestion() {
            const pdfFilename = document.getElementById('pdfSelect').value;
            const question = document.getElementById('questionInput').value;
            if (!pdfFilename) { alert('Select a PDF'); return; }
            if (!question.trim()) { alert('Enter a question'); return; }
            const chatArea = document.getElementById('chatArea');
            chatArea.innerHTML = '<div class="loading"><div class="spinner"></div><p>Getting answer...</p></div>';
            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question, pdf_filename: pdfFilename, top_k: 5 })
                });
                const data = await response.json();
                if (response.ok) {
                    await loadLatestQAId();
                    displayAnswer(question, data);
                    loadHistory();
                    loadStats();
                } else {
                    chatArea.innerHTML = `<div class="alert alert-error">❌ ${data.detail}</div>`;
                }
            } catch (error) {
                chatArea.innerHTML = `<div class="alert alert-error">❌ Request failed</div>`;
            }
        }

        async function loadLatestQAId() {
            try {
                const response = await fetch('/history?limit=1');
                const history = await response.json();
                if (history.length > 0) {
                    currentQAId = history[0].id;
                    console.log('Current QA ID set to:', currentQAId);
                }
            } catch (error) { console.error(error); }
        }

        async function displayAnswer(question, data) {
            await loadLatestQAId();
            
            let sourcesHtml = '';
            if (data.sources && data.sources.length > 0) {
                sourcesHtml = '<div class="sources"><strong>📚 Sources:</strong>';
                for (let idx = 0; idx < data.sources.length; idx++) {
                    const source = data.sources[idx];
                    sourcesHtml += `<div class="source-item"><strong>Source ${idx+1}</strong> (${(source.relevance_score*100).toFixed(1)}% relevant)<br><small>${source.preview.substring(0,150)}...</small></div>`;
                }
                sourcesHtml += '</div>';
            }

            const chatArea = document.getElementById('chatArea');
            const formattedAnswer = escapeHtml(data.answer).replace(/\\n/g, '<br>');
            chatArea.innerHTML = `
                <div class="chat-message question-message">
                    <div class="message-header">❓ You asked:</div>
                    <div>${escapeHtml(question)}</div>
                </div>
                <div class="chat-message answer-message" id="latestAnswer">
                    <div class="message-header">🤖 AI Answer (${data.response_time_ms.toFixed(0)}ms):</div>
                    <div>${formattedAnswer}</div>
                    ${sourcesHtml}
                    <div class="rating-container">
                        <div class="rating-label">⭐ Rate this answer (1-5 stars):</div>
                        <div class="rating-stars">
                            <button class="star" onclick="submitRating(1)">★</button>
                            <button class="star" onclick="submitRating(2)">★</button>
                            <button class="star" onclick="submitRating(3)">★</button>
                            <button class="star" onclick="submitRating(4)">★</button>
                            <button class="star" onclick="submitRating(5)">★</button>
                        </div>
                        <div id="ratingFeedback" class="rating-feedback"></div>
                        <div style="margin-top: 10px; font-size: 11px; color: #999;">QA ID: ${currentQAId || 'loading...'}</div>
                    </div>
                </div>
            `;
            
            if (currentQAId) {
                checkExistingRating(currentQAId);
            }
        }
        
        async function checkExistingRating(qaId) {
            try {
                const response = await fetch('/history?limit=50');
                const history = await response.json();
                const item = history.find(h => h.id === qaId);
                if (item && item.rating) {
                    highlightStars(item.rating);
                    const feedback = document.getElementById('ratingFeedback');
                    if (feedback) {
                        feedback.innerHTML = `✅ Already rated ${item.rating}/5 stars. Thank you!`;
                    }
                }
            } catch (error) { console.error(error); }
        }
        
        function highlightStars(rating) {
            const stars = document.querySelectorAll('.star');
            stars.forEach((star, index) => {
                if (index < rating) {
                    star.classList.add('active');
                } else {
                    star.classList.remove('active');
                }
            });
        }

        async function submitRating(rating) {
            console.log(`Submitting rating: ${rating} for QA ID: ${currentQAId}`);
            
            if (!currentQAId) {
                await loadLatestQAId();
            }
            
            if (!currentQAId) {
                alert('Please ask a question first before rating');
                return;
            }
            
            try {
                const response = await fetch(`/feedback/${currentQAId}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ rating: rating })
                });
                
                const result = await response.json();
                console.log('Rating response:', result);
                
                if (response.ok) {
                    highlightStars(rating);
                    const feedback = document.getElementById('ratingFeedback');
                    if (feedback) {
                        feedback.innerHTML = `✅ Thank you! You rated this answer ${rating}/5 stars.`;
                        setTimeout(() => {
                            if (feedback) feedback.innerHTML = '';
                        }, 3000);
                    }
                    loadHistory();
                    loadStats();
                } else {
                    alert(`Failed to submit rating: ${result.detail || 'Unknown error'}`);
                }
            } catch (error) {
                console.error('Rating error:', error);
                alert('Error submitting rating: ' + error.message);
            }
        }

        async function loadHistory() {
            try {
                const response = await fetch('/history?limit=20');
                const history = await response.json();
                const historyArea = document.getElementById('historyArea');
                if (!history || history.length === 0) {
                    historyArea.innerHTML = '<p style="color:#999;text-align:center;">No history yet</p>';
                    return;
                }
                
                // Store the full history data globally
                window.historyData = history;
                
                let html = '';
                for (let i = 0; i < history.length; i++) {
                    const item = history[i];
                    
                    // FIX: Convert UTC to Bangladesh time (UTC+6)
                    const utcDate = new Date(item.created_at);
                    const bangladeshDate = new Date(utcDate.getTime() + (6 * 60 * 60 * 1000));
                    const bangladeshTime = bangladeshDate.toLocaleString('en-BD', {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: true
                    });
                    
                    let ratingDisplay = '';
                    if (item.rating) {
                        const stars = '★'.repeat(item.rating) + '☆'.repeat(5 - item.rating);
                        ratingDisplay = `<div class="history-rating">⭐ Rated: ${stars} (${item.rating}/5)</div>`;
                    } else {
                        ratingDisplay = `<div class="history-rating">⭐ Not rated yet 
                            <button class="btn-rate" onclick="event.stopPropagation(); rateHistoryItem(${item.id})">Rate Now</button>
                        </div>`;
                    }
                    
                    // Get short preview of answer (first 150 characters)
                    const answerPreview = item.answer ? escapeHtml(item.answer.substring(0, 150)) + '...' : 'No answer';
                    const shortQuestion = escapeHtml(item.question.substring(0, 100)) + '...';
                    
                    html += `
                        <div class="history-item" onclick="loadFullHistoryItem(${item.id})">
                            <div class="history-question">❓ ${shortQuestion}</div>
                            <div class="history-answer-preview" style="font-size: 12px; color: #666; margin-top: 5px; padding: 5px; background: #f0f0f0; border-radius: 5px;">
                                💬 Answer preview: ${answerPreview}
                            </div>
                            ${ratingDisplay}
                            <small>📅 ${bangladeshTime}</small>
                        </div>
                    `;
                }
                historyArea.innerHTML = html;
            } catch (error) { 
                console.error('History error:', error);
                document.getElementById('historyArea').innerHTML = '<p style="color:#999;text-align:center;">Error loading history</p>';
            }
        }

        // New function to load full history item - uses stored data, not HTML attributes
        function loadFullHistoryItem(id) {
            // Find the item in stored history data
            const item = window.historyData.find(h => h.id === id);
            if (!item) return;
            
            // Set current QA ID for rating
            currentQAId = id;
            
            // Display the full Q&A in the chat area
            const chatArea = document.getElementById('chatArea');
            
            // Create stars HTML based on existing rating
            let starsHtml = '';
            for (let i = 1; i <= 5; i++) {
                const activeClass = i <= (item.rating || 0) ? 'active' : '';
                starsHtml += `<button class="star ${activeClass}" onclick="submitRating(${i})">★</button>`;
            }
            
            // Show FULL answer in a beautiful card
            chatArea.innerHTML = `
                <div class="chat-message question-message">
                    <div class="message-header">❓ You asked (from history):</div>
                    <div style="font-size: 16px; line-height: 1.5;">${escapeHtml(item.question)}</div>
                </div>
                <div class="chat-message answer-message" id="latestAnswer">
                    <div class="message-header">🤖 AI Answer (from history):</div>
                    <div style="font-size: 15px; line-height: 1.6; color: #2d2d2d;">
                        ${escapeHtml(item.answer).replace(/\\n/g, '<br>')}
                    </div>
                    <div class="rating-container" style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #ddd;">
                        <div class="rating-label" style="font-size: 13px; color: #666; margin-bottom: 8px;">⭐ Rate this answer (1-5 stars):</div>
                        <div class="rating-stars" style="display: flex; gap: 8px;">
                            ${starsHtml}
                        </div>
                        <div id="ratingFeedback" class="rating-feedback" style="font-size: 12px; color: #1a8f5a; margin-top: 5px;"></div>
                        <div style="margin-top: 10px; font-size: 11px; color: #999;">QA ID: ${id}</div>
                    </div>
                </div>
            `;
            
            // Scroll to the answer
            chatArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
            
            // Show feedback if already rated
            if (item.rating && item.rating > 0) {
                const feedback = document.getElementById('ratingFeedback');
                if (feedback) {
                    feedback.innerHTML = `✅ Previously rated ${item.rating}/5 stars. You can update your rating!`;
                    setTimeout(() => {
                        if (feedback) feedback.innerHTML = '';
                    }, 3000);
                }
            }
        }
        async function rateHistoryItem(qaId) {
            const rating = prompt('Rate this answer from 1 to 5 stars:', '5');
            if (rating && rating >= 1 && rating <= 5) {
                try {
                    const response = await fetch(`/feedback/${qaId}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ rating: parseInt(rating) })
                    });
                    if (response.ok) {
                        alert('✅ Rating submitted successfully!');
                        loadHistory();
                        loadStats();
                    } else {
                        alert('❌ Failed to submit rating');
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                }
            }
        }
        
        function loadQuestionToAsk(question) {
            document.getElementById('questionInput').value = question;
            alert('Question loaded! Click "Ask AI" to get the answer again.');
        }

        async function loadStats() {
            try {
                const response = await fetch('/stats');
                const stats = await response.json();
                document.getElementById('totalQuestions').innerText = stats.total_questions || 0;
                document.getElementById('avgTime').innerText = (stats.avg_response_time_ms || 0).toFixed(0);
            } catch (error) { console.error(error); }
        }

        function escapeHtml(text) {
            if (!text) return '';
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Initialize everything
        loadPDFs();
        loadHistory();
        loadStats();
        setInterval(() => { loadStats(); loadHistory(); }, 30000);
    </script>
</body>
</html>"""

@app.get("/pdfs")
async def get_pdfs(db: Session = Depends(get_db)):
    pdfs = db.query(PDFDocument).all()
    return [{"filename": p.filename, "chunk_count": p.chunk_count} for p in pdfs]

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    file_path = os.path.join("uploads", file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        chunk_count = rag_engine.upload_pdf(file_path, file.filename)
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    
    pdf_doc = PDFDocument(filename=file.filename, file_path=file_path, chunk_count=chunk_count)
    db.add(pdf_doc)
    db.commit()
    
    return {"filename": file.filename, "chunk_count": chunk_count, "message": "PDF uploaded successfully"}

@app.post("/ask")
async def ask_question(request: QuestionRequest, db: Session = Depends(get_db)):
    start_time = time.time()
    
    try:
        chunks = rag_engine.retrieve_relevant_chunks(request.pdf_filename, request.question, request.top_k)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    answer, sources = rag_engine.generate_answer(request.question, chunks)
    response_time = (time.time() - start_time) * 1000
    
    try:
        qa_record = QARecord(
            pdf_filename=request.pdf_filename,
            question=request.question,
            answer=answer,
            sources=sources,
            response_time_ms=response_time
        )
        db.add(qa_record)
        db.commit()
    except Exception as e:
        print(f"Database error: {e}")
        db.rollback()
    
    return {"answer": answer, "sources": sources, "response_time_ms": response_time}

@app.post("/feedback/{qa_id}")
async def submit_feedback(qa_id: int, feedback: FeedbackRequest, db: Session = Depends(get_db)):
    print(f"📝 Received rating: QA ID={qa_id}, Rating={feedback.rating}")
    
    qa_record = db.query(QARecord).filter(QARecord.id == qa_id).first()
    if not qa_record:
        raise HTTPException(status_code=404, detail=f"QA record {qa_id} not found")
    
    qa_record.user_rating = feedback.rating
    db.commit()
    
    print(f"✅ Rating saved successfully")
    return {"message": "Rating submitted", "rating": feedback.rating}

@app.get("/history")
async def get_history(pdf_filename: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    query = db.query(QARecord)
    if pdf_filename:
        query = query.filter(QARecord.pdf_filename == pdf_filename)
    records = query.order_by(QARecord.created_at.desc()).limit(limit).all()
    return [{"id": r.id, "question": r.question, "answer": r.answer[:200] + "...", "rating": r.user_rating, "created_at": r.created_at.isoformat()} for r in records]

@app.get("/stats")
async def get_stats(db: Session = Depends(get_db)):
    total = db.query(QARecord).count()
    avg_time = db.query(func.avg(QARecord.response_time_ms)).scalar() or 0
    return {"total_questions": total, "avg_response_time_ms": float(avg_time), "database": "PostgreSQL"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)