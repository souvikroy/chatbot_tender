import json
import os
from typing import Dict, Any, Optional, List

import pymongo
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
# from google import genai
from google.generativeai import types
# Import model tuning parameters from config
from config import MAX_FILES_TO_PROCESS, TOP_FILES_TO_USE, TEMPERATURE, MAX_TOKENS, SYSTEM_PROMPT


import google.generativeai as genai


# Import text chunker for optimized document processing
from text_chunker import chunk_tender_documents

# Define API models
class TenderRequest(BaseModel):
    tender_id: str
    question: str

class TenderResponse(BaseModel):
    answer: str

class ErrorResponse(BaseModel):
    error: str

# Define lifespan context manager for startup events
from contextlib import asynccontextmanager
import traceback
import sys

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to MongoDB on startup
    global mongo_client, db, collection
    try:
        print("\n[STARTUP] Initializing application...")
        print(f"[STARTUP] Gemini Model: {GEMINI_MODEL}")
        print(f"[STARTUP] MongoDB URI: {MONGODB_URI[:20]}...")
        print(f"[STARTUP] MongoDB DB: {MONGODB_DB_NAME}")
        print(f"[STARTUP] MongoDB Collection: {MONGODB_PROCESSED_COLLECTION}")
        print(f"[STARTUP] MAX_FILES_TO_PROCESS: {MAX_FILES_TO_PROCESS}")
        print(f"[STARTUP] TOP_FILES_TO_USE: {TOP_FILES_TO_USE}")
        
        # Configure error handling for uncaught exceptions
        def handle_exception(exc_type, exc_value, exc_traceback):
            print(f"[ERROR] Uncaught exception: {exc_type.__name__}: {exc_value}")
            traceback.print_exception(exc_type, exc_value, exc_traceback)
            return sys.__excepthook__(exc_type, exc_value, exc_traceback)
            
        sys.excepthook = handle_exception
        
        # Connect to MongoDB
        print("[STARTUP] Connecting to MongoDB...")
        mongo_client = pymongo.MongoClient(MONGODB_URI)
        db = mongo_client[MONGODB_DB_NAME]
        collection = db[MONGODB_PROCESSED_COLLECTION]
        
        # Verify connection
        count = collection.count_documents({})
        print(f"[STARTUP] Connected to MongoDB. Found {count} documents in collection {MONGODB_PROCESSED_COLLECTION}")
                    
        # Test Gemini API connection
        print("[STARTUP] Testing Gemini API connection...")
        try:
            model = genai.GenerativeModel(model_name=GEMINI_MODEL)
            response = model.generate_content("Explain how AI works in a few words")
            print(f"[STARTUP] Gemini API test successful: {response.text}")
        except Exception as e:
            print(f"[STARTUP] Gemini API test failed: {str(e)}")
            traceback.print_exc()
            print("[STARTUP] Continuing startup despite Gemini API test failure")

        print("[STARTUP] Application initialized successfully")
    except Exception as e:
        print(f"[STARTUP] Error during startup: {str(e)}")
        traceback.print_exc()
        raise
    
    yield  # This is where the app runs
    
    # Close MongoDB connection on shutdown
    if mongo_client:
        mongo_client.close()
        print("[SHUTDOWN] MongoDB connection closed")

# Initialize FastAPI app
app = FastAPI(
    title="Tender Information Extraction API",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load environment variables
load_dotenv()

# Gemini API configuration
GEMINI_MODEL = os.getenv("GEMINI_MODEL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)

# MongoDB configuration
MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME")
MONGODB_PROCESSED_COLLECTION = os.getenv("MONGODB_PROCESSED_COLLECTION")

# File processing configuration is now imported from config.py



# MongoDB client
mongo_client = None
db = None
collection = None



def get_tender_by_id(tender_id: str) -> Optional[Dict[str, Any]]:
    """Find a tender by its ID in MongoDB"""
    try:
        print(f"[DEBUG] Attempting to find tender with ID: {tender_id}")
        tender = collection.find_one({"tender_id": tender_id})
        if tender:
            print(f"[DEBUG] Found tender with ID: {tender_id}")
            print(f"[DEBUG] Tender keys: {list(tender.keys())}")
            if 'file_texts' in tender:
                file_texts_type = type(tender['file_texts']).__name__
                print(f"[DEBUG] file_texts is of type: {file_texts_type}")
                if isinstance(tender['file_texts'], dict):
                    print(f"[DEBUG] file_texts contains {len(tender['file_texts'])} files")
                elif isinstance(tender['file_texts'], str):
                    print(f"[DEBUG] file_texts is a string of length {len(tender['file_texts'])}")
                else:
                    print(f"[DEBUG] file_texts is of unexpected type: {file_texts_type}")
            else:
                print(f"[DEBUG] Tender does not contain 'file_texts' key")
        else:
            print(f"[DEBUG] No tender found with ID: {tender_id}")
        return tender
    except Exception as e:
        print(f"[ERROR] Error retrieving tender from MongoDB: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def combine_file_texts(file_texts: Dict[str, str]) -> str:
    """Combine all file texts into a single string
    First chunks the documents to extract relevant qualification criteria and clauses,
    then combines the most relevant chunks with the largest files if needed.
    """
    if not file_texts:
        return ""
        
    # Handle different possible structures in MongoDB
    if isinstance(file_texts, dict):
        # Process the documents to extract relevant chunks by criteria
        print("Chunking documents by qualification criteria and important clauses...")
        chunked_documents = chunk_tender_documents(file_texts)
        
        # Extract the most relevant chunks for each category
        relevant_chunks = []
        
        # Add chunks from each category to our relevant chunks list
        for category in ['technical', 'financial', 'joint_venture', 'commercial_clauses']:
            if category in chunked_documents['categorized_chunks']:
                category_chunks = chunked_documents['categorized_chunks'][category]
                # Add all chunks from this category (we'll limit the total later)
                for chunk in category_chunks:
                    relevant_chunks.append(chunk['text'])
        
        # Add specific criteria extractions
        for criteria_type, extractions in chunked_documents['specific_criteria'].items():
            for extraction in extractions:
                relevant_chunks.append(extraction['text'])
        
        # Remove duplicates while preserving order
        unique_chunks = []
        for chunk in relevant_chunks:
            if chunk not in unique_chunks:
                unique_chunks.append(chunk)
        
        # If we have enough relevant chunks, use those
        if len(unique_chunks) >= TOP_FILES_TO_USE:
            print(f"Found {len(unique_chunks)} relevant chunks based on criteria")
            combined_text = "\n\n---\n\n".join(unique_chunks[:TOP_FILES_TO_USE*2])  # Use twice as many chunks as we would files
            return combined_text
        
        # If we don't have enough relevant chunks, fall back to using the largest files
        print(f"Found only {len(unique_chunks)} relevant chunks, supplementing with largest files")
        
        # If there are more than MAX_FILES_TO_PROCESS files, only use the TOP_FILES_TO_USE largest files
        if len(file_texts) > MAX_FILES_TO_PROCESS:
            print(f"Found {len(file_texts)} files, selecting the {TOP_FILES_TO_USE} largest ones")
            # Sort files by size (number of characters)
            files_by_size = sorted(file_texts.items(), key=lambda x: len(x[1]), reverse=True)
            # Take only the TOP_FILES_TO_USE largest files
            selected_files = files_by_size[:TOP_FILES_TO_USE]
            
            # Combine the texts from the selected files
            combined_text = "\n\n---\n\n".join([text for _, text in selected_files])
            
            # If we have any unique chunks, prepend them to the combined text
            if unique_chunks:
                chunk_text = "\n\n---\n\n".join(unique_chunks[:TOP_FILES_TO_USE])
                combined_text = chunk_text + "\n\n==========\n\n" + combined_text
                
            return combined_text
        else:
            # If we have fewer files than the limit, use all of them
            print(f"Using all {len(file_texts)} files")
            combined_text = "\n\n---\n\n".join(file_texts.values())
            
            # If we have any unique chunks, prepend them to the combined text
            if unique_chunks:
                chunk_text = "\n\n---\n\n".join(unique_chunks)
                combined_text = chunk_text + "\n\n==========\n\n" + combined_text
                
            return combined_text
    elif isinstance(file_texts, str):
        # If it's already a single string, just return it
        return file_texts
    else:
        # If it's neither a dict nor a string, return an empty string
        print(f"[WARNING] file_texts is of unexpected type: {type(file_texts)}")
        return ""



def get_gemini_response(prompt: str, system_prompt: str):
    """Get response from Gemini API"""
    try:
        print(f"[INFO] Calling Gemini API with prompt length: {len(prompt)} characters")
        
        # Create the model
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL,
            generation_config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_TOKENS,
            }
        )
        
        # Combine system prompt and user prompt for models that don't support system_instruction
        combined_prompt = f"{system_prompt}\n\n{prompt}"
        
        response = model.generate_content(combined_prompt)
        
        if not response.text:
            raise Exception("Empty response from Gemini")
        
        print(f"[INFO] Gemini response: {len(response.text)} characters")
        return response.text
    except Exception as e:
        print(f"[ERROR] Gemini API error: {str(e)}")
        raise Exception(f"Gemini API error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and monitoring"""
    return {"status": "healthy", "message": "Tender Information Extraction API is running"}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Tender Information Extraction API",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "ask": "/ask (POST)",
            "docs": "/docs"
        }
    }

@app.post("/ask", response_model=TenderResponse)
async def ask_question(request: TenderRequest):
    """
    Endpoint to ask questions about tender documents
    """
    import time
    try:
        print(f"\n[INFO] Received request for tender_id: {request.tender_id}")
        print(f"[INFO] Question: {request.question}")
        
        # Validate input
        if not request.tender_id:
            print("[ERROR] Tender ID is missing")
            raise HTTPException(status_code=400, detail="Tender ID is required")
        if not request.question:
            print("[ERROR] Question is missing")
            raise HTTPException(status_code=400, detail="Question is required")
        
        # Find the tender
        print(f"[INFO] Looking up tender with ID: {request.tender_id}")
        tender = get_tender_by_id(request.tender_id)
        if not tender:
            print(f"[ERROR] Tender not found with ID: {request.tender_id}")
            return TenderResponse(answer=f"No tender found with ID: {request.tender_id}. Please check the tender ID and try again.")
        
        print(f"[INFO] Found tender. Keys: {list(tender.keys())}")
        
        # Extract file_texts
        file_texts = tender.get("file_texts", {})
        if not file_texts:
            print("[ERROR] No file texts found in tender document")
            return TenderResponse(answer="No file texts found for this tender. The document may be empty or not properly processed.")
        
        if isinstance(file_texts, dict):
            print(f"[INFO] File texts contains {len(file_texts)} files")
            print(f"[INFO] File names: {list(file_texts.keys())}")
        else:
            print(f"[INFO] File texts is of type {type(file_texts)}")
        
        # Combine all file texts
        print("[INFO] Combining file texts...")
        combined_text = combine_file_texts(file_texts)
        print(f"[INFO] Combined text length: {len(combined_text)} characters")
        
        # Use the system prompt from config.py
        system_prompt = SYSTEM_PROMPT
        
        # Create the user prompt
        user_prompt = f"Here is the tender document with ID {request.tender_id}:\n\n{combined_text}\n\nQuestion: {request.question}"
        print(f"[INFO] User prompt length: {len(user_prompt)} characters")
        
        # Get response from Gemini
        try:
            print("[INFO] Calling Gemini API...")
            answer = get_gemini_response(user_prompt, system_prompt)
            print("[INFO] Received response from Gemini")
            return TenderResponse(answer=answer)
        except Exception as e:
            print(f"[ERROR] Gemini API error: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return a fallback response instead of raising an exception
            return TenderResponse(answer="I'm sorry, I encountered an error while processing your question. Please try again later or with a more specific question.")
    except Exception as e:
        print(f"[ERROR] Unhandled exception: {str(e)}")
        import traceback
        traceback.print_exc()
        # Return a fallback response instead of raising an exception
        return TenderResponse(answer="I'm sorry, I encountered an unexpected error while processing your request. Please try again later.")
