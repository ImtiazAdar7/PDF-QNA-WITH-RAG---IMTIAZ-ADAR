# Project: PDF Q&A System With RAG
# Author: Imtiaz Adar
# Email: imtiazadarofficial@gmail.com

import chromadb
from chromadb.utils import embedding_functions
import google.generativeai as genai
from pypdf import PdfReader
import os
import hashlib
import time
from typing import List, Dict, Tuple
from dotenv import load_dotenv
import numpy as np
import re

load_dotenv()

# Initialize Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
gemini_model = genai.GenerativeModel('gemini-2.5-flash')

class RAGEngine:
    def __init__(self, persist_directory="./chroma_db"):
        self.chroma_client = chromadb.PersistentClient(path=persist_directory)
        self.embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )
        self.collections = {}
        
    def _get_collection_name(self, pdf_filename: str) -> str:
        safe_name = hashlib.md5(pdf_filename.encode()).hexdigest()
        return f"pdf_{safe_name}"
    
    def chunk_text_semantic(self, text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
        """Improved chunking by paragraphs and sentences"""
        if len(text) < 2000:
            return [text]
        
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = current_chunk[-overlap:] if overlap > 0 else ""
            
            current_chunk += para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk)
        
        if len(chunks) == 1 and len(chunks[0]) > chunk_size * 1.5:
            chunks = self._split_by_sentences(chunks[0], chunk_size, overlap)
        
        print(f"📦 Created {len(chunks)} semantic chunks")
        return chunks

    def _split_by_sentences(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text by sentences"""
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) > chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = current_chunk[-overlap:] if overlap > 0 else ""
            
            current_chunk += sentence + " "
        
        if current_chunk:
            chunks.append(current_chunk)
        
        return chunks
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page_num, page in enumerate(reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                    else:
                        print(f"⚠️ No text extracted from page {page_num+1}")
                except Exception as e:
                    print(f"⚠️ Error on page {page_num+1}: {e}")
                    continue
            
            if not text.strip():
                raise ValueError("No text could be extracted from PDF")
            
            print(f"✅ Extracted {len(text)} characters from PDF")
            print(f"📄 Preview: {text[:500]}...")
            return text
            
        except Exception as e:
            raise ValueError(f"PDF reading failed: {str(e)}")
    
    def upload_pdf(self, pdf_path: str, filename: str) -> int:
        print(f"\n📤 Uploading PDF: {filename}")
        
        full_text = self.extract_text_from_pdf(pdf_path)
        print(f"📝 Extracted text length: {len(full_text)} characters")
        
        if not full_text.strip():
            raise ValueError("No text could be extracted from PDF")
        
        chunks = self.chunk_text_semantic(full_text)
        print(f"📦 Created {len(chunks)} chunks")
        
        if chunks:
            print(f"🔍 First chunk preview: {chunks[0][:200]}...")
        
        collection_name = self._get_collection_name(filename)
        
        try:
            self.chroma_client.delete_collection(collection_name)
            print(f"🗑️ Deleted existing collection")
        except:
            pass
        
        collection = self.chroma_client.create_collection(
            name=collection_name,
            embedding_function=self.embedding_fn
        )
        
        ids = [f"chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {
                "filename": filename,
                "chunk_index": i,
                "chunk_preview": chunk[:200]
            }
            for i, chunk in enumerate(chunks)
        ]
        
        collection.add(
            documents=chunks,
            ids=ids,
            metadatas=metadatas
        )
        
        self.collections[filename] = collection
        
        print(f"✅ Successfully uploaded {len(chunks)} chunks to ChromaDB")
        return len(chunks)
    
    def retrieve_relevant_chunks(self, filename: str, question: str, top_k: int = 5) -> List[Tuple[str, Dict, float]]:
        collection_name = self._get_collection_name(filename)
        
        try:
            collection = self.chroma_client.get_collection(
                name=collection_name,
                embedding_function=self.embedding_fn
            )
        except:
            raise ValueError(f"PDF '{filename}' not found. Please upload it first.")
        
        results = collection.query(
            query_texts=[question],
            n_results=top_k
        )
        
        chunks_with_metadata = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                chunks_with_metadata.append((
                    results['documents'][0][i],
                    results['metadatas'][0][i] if results['metadatas'] else {},
                    results['distances'][0][i] if results['distances'] else 0
                ))
        
        return chunks_with_metadata
    
    def generate_answer(self, question: str, chunks: List[Tuple[str, Dict, float]]) -> Tuple[str, List[Dict]]:
        if not chunks:
            return "I couldn't find any relevant information in the PDF to answer this question.", []
        
        context_parts = []
        sources = []
        
        for i, (chunk, metadata, distance) in enumerate(chunks):
            context_parts.append(f"[Source {i+1}]:\n{chunk}")
            sources.append({
                "chunk_index": metadata.get('chunk_index', i),
                "preview": metadata.get('chunk_preview', chunk[:200]),
                "relevance_score": float(1 - distance) if distance else 1.0
            })
        
        context = "\n\n".join(context_parts)
        
        prompt = f"""You are a helpful assistant that answers questions based ONLY on the provided context from a PDF document.

CONTEXT from the PDF:
{context}

QUESTION: {question}

INSTRUCTIONS:
1. Answer based ONLY on the context above
2. If the answer is not in the context, say "I cannot answer this based on the provided PDF content"
3. Be concise but thorough
4. Quote specific parts from the context when helpful
5. Do not use external knowledge

ANSWER:"""
        
        response = gemini_model.generate_content(prompt)
        return response.text, sources

# Global instance
rag_engine = RAGEngine()