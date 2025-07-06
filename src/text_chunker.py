"""
Optimized text chunking module for tender document processing.
This module provides functions to chunk tender documents and identify sections
related to specific qualification criteria and important clauses.
"""

import re
from typing import Dict, List, Tuple, Any, Optional, Set
import json
from datetime import datetime
from functools import lru_cache

# Import context size from config
from config import CONTEXT_SIZE

# Define key terms for different categories - using frozensets for O(1) lookup
CRITERIA_KEYWORDS = {
    "technical": frozenset([
        "technical qualification", "technical criteria", "technical requirement", 
        "similar work", "work experience", "project experience", "completion certificate",
        "work order", "technical capacity", "technical capability", "eligible works",
        "qualification requirement", "technical eligibility"
    ]),
    "financial": frozenset([
        "turnover", "financial qualification", "financial criteria", "financial requirement",
        "annual turnover", "average annual turnover", "financial capacity", 
        "financial capability", "net worth", "liquid asset", "solvency", 
        "working capital", "financial statement", "balance sheet", "profit and loss",
        "financial position", "financial standing", "financial strength", "revenue"
    ]),
    "joint_venture": frozenset([
        "joint venture", "jv ", "consortium", "jv criteria", "jv requirement",
        "lead member", "lead partner", "jv agreement", "jv formation"
    ]),
    "commercial_clauses": frozenset([
        "earnest money", "emd", "bid security", "performance security", 
        "security deposit", "retention money", "defect liability", "completion period"
    ])
}

# Compile regex patterns once for better performance
SENTENCE_BOUNDARIES = re.compile(r'(?:\. |\.\n|\n\n)')
PARAGRAPH_SPLIT = re.compile(r'\n\s*\n')

@lru_cache(maxsize=128)
def _cached_keyword_search(text_lower: str, keyword: str) -> bool:
    """Cache keyword searches for repeated patterns."""
    return keyword in text_lower

def identify_section_type(text: str) -> List[str]:
    """
    Optimized function to identify which criteria categories a text section belongs to.
    
    Args:
        text: The text section to analyze
        
    Returns:
        List of category names that match this section
    """
    if not text or len(text.strip()) < 10:
        return []
    
    text_lower = text.lower()
    matched_categories = []
    
    # Use set operations for faster matching
    for category, keywords in CRITERIA_KEYWORDS.items():
        # Check if any keyword is found in text - early exit on first match
        if any(_cached_keyword_search(text_lower, keyword) for keyword in keywords):
            matched_categories.append(category)
                
    return matched_categories

def _find_sentence_boundaries(text: str, pos: int, direction: str = 'forward') -> int:
    """
    Helper function to find sentence boundaries efficiently.
    
    Args:
        text: The full text
        pos: Current position
        direction: 'forward' or 'backward'
        
    Returns:
        Position of sentence boundary
    """
    if direction == 'backward' and pos > 0:
        # Find previous sentence boundary
        boundaries = [
            text.rfind(". ", 0, pos),
            text.rfind(".\n", 0, pos),
            text.rfind("\n\n", 0, pos)
        ]
        boundary = max(b for b in boundaries if b != -1)
        return boundary + 2 if boundary != -1 else 0
    
    elif direction == 'forward' and pos < len(text):
        # Find next sentence boundary
        boundaries = [
            text.find(". ", pos),
            text.find(".\n", pos),
            text.find("\n\n", pos)
        ]
        valid_boundaries = [b for b in boundaries if b != -1]
        if valid_boundaries:
            boundary = min(valid_boundaries)
            return boundary + 1
    
    return pos

def extract_section_with_context(text: str, keyword: str, context_size: int = CONTEXT_SIZE) -> str:
    """
    Optimized function to extract a section of text containing the keyword with context.
    
    Args:
        text: The full text to search in
        keyword: The keyword to search for
        context_size: Number of characters to include before and after the keyword
        
    Returns:
        Text section with the keyword and its context
    """
    if not text or not keyword:
        return ""
    
    text_lower = text.lower()
    keyword_lower = keyword.lower()
    
    keyword_pos = text_lower.find(keyword_lower)
    if keyword_pos == -1:
        return ""
    
    # Calculate initial boundaries
    start_pos = max(0, keyword_pos - context_size)
    end_pos = min(len(text), keyword_pos + len(keyword) + context_size)
    
    # Expand to complete sentences for better readability
    start_pos = _find_sentence_boundaries(text, start_pos, 'backward')
    end_pos = _find_sentence_boundaries(text, end_pos, 'forward')
    
    return text[start_pos:end_pos].strip()

def _process_paragraph_chunk(paragraph: str, prev_para: str, next_para: str, filename: str) -> Optional[Dict[str, Any]]:
    """
    Helper function to process individual paragraph chunks.
    
    Args:
        paragraph: Current paragraph
        prev_para: Previous paragraph for context
        next_para: Next paragraph for context
        filename: Source filename
        
    Returns:
        Chunk info dictionary or None if paragraph is too short
    """
    if len(paragraph.strip()) < 50:
        return None
    
    # Build context efficiently
    context_parts = [prev_para, paragraph, next_para]
    context = "\n\n".join(part for part in context_parts if part)
    
    categories = identify_section_type(paragraph)
    
    return {
        "text": paragraph.strip(),
        "context": context,
        "source": filename,
        "categories": categories
    }

def chunk_by_criteria(file_texts: Dict[str, str]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Optimized function to process file texts and chunk them by different criteria categories.
    
    Args:
        file_texts: Dictionary mapping file names to their text content
        
    Returns:
        Dictionary with criteria categories as keys and lists of relevant text chunks as values
    """
    # Pre-initialize with all categories
    chunks_by_category = {category: [] for category in CRITERIA_KEYWORDS.keys()}
    chunks_by_category["other"] = []
    
    for filename, content in file_texts.items():
        if not content or len(content.strip()) < 100:
            continue
            
        # Split content into paragraphs using compiled regex
        paragraphs = [p.strip() for p in PARAGRAPH_SPLIT.split(content) if p.strip()]
        
        # Process paragraphs with context
        for i, paragraph in enumerate(paragraphs):
            prev_para = paragraphs[i-1] if i > 0 else ""
            next_para = paragraphs[i+1] if i < len(paragraphs) - 1 else ""
            
            chunk_info = _process_paragraph_chunk(paragraph, prev_para, next_para, filename)
            if not chunk_info:
                continue
            
            # Distribute chunk to appropriate categories
            if not chunk_info["categories"]:
                chunks_by_category["other"].append(chunk_info)
            else:
                for category in chunk_info["categories"]:
                    if category in chunks_by_category:
                        chunks_by_category[category].append(chunk_info)
    
    # Remove empty categories to reduce memory usage
    return {k: v for k, v in chunks_by_category.items() if v}

def _extract_criteria_sections(combined_text: str, file_texts: Dict[str, str], 
                             criteria_type: str, search_terms: List[str]) -> List[Dict[str, str]]:
    """
    Helper function to extract sections for specific criteria.
    
    Args:
        combined_text: Combined text from all files
        file_texts: Original file texts
        criteria_type: Type of criteria being extracted
        search_terms: List of terms to search for
        
    Returns:
        List of extracted sections with metadata
    """
    sections = []
    processed_terms = set()  # Avoid duplicate processing
    
    for term in search_terms:
        term_lower = term.lower()
        if term_lower in processed_terms:
            continue
        processed_terms.add(term_lower)
        
        for filename, content in file_texts.items():
            if term_lower in content.lower():
                extracted_text = extract_section_with_context(content, term)
                if extracted_text and len(extracted_text.strip()) > 20:
                    sections.append({
                        "text": extracted_text,
                        "source": filename,
                        "keyword": term,
                        "criteria_type": criteria_type
                    })
    
    # Remove duplicate sections based on text similarity
    unique_sections = []
    seen_texts = set()
    
    for section in sections:
        # Use first 100 characters as uniqueness key
        text_key = section["text"][:100].lower().strip()
        if text_key not in seen_texts:
            seen_texts.add(text_key)
            unique_sections.append(section)
    
    return unique_sections

def extract_specific_criteria(file_texts: Dict[str, str]) -> Dict[str, List[Dict[str, str]]]:
    """
    Optimized function to extract specific criteria mentioned in tender documents.
    
    Args:
        file_texts: Dictionary mapping file names to their text content
        
    Returns:
        Dictionary with specific criteria types and their extracted text chunks
    """
    if not file_texts:
        return {}
    
    # Pre-filter files that are too small
    valid_files = {k: v for k, v in file_texts.items() if len(v.strip()) > 100}
    if not valid_files:
        return {}
    
    # Define search terms for each specific criteria (optimized order - most common first)
    criteria_search_terms = {
        "turnover": ["turnover", "annual turnover", "average annual turnover", "financial turnover", "revenue"],
        "emd_submission": ["earnest money deposit", "emd", "bid security", "mode of emd", "emd submission"],
        "completion_period": ["completion period", "contract period", "time of completion", "project timeline"],
        "performance_security": ["performance security", "performance guarantee", "performance bond"],
        "security_deposit": ["security deposit", "retention money", "retention amount", "withheld amount"],
        "defect_liability": ["defect liability", "defect liability period", "maintenance period", "warranty period"],
        "mobilization_advance": ["mobilization advance", "mobilisation advance", "advance payment"],
        "solvency_working_capital": ["solvency", "working capital", "bank solvency", "credit facility"],
        "liquid_asset": ["liquid asset", "cash flow", "liquidity", "liquid fund"],
        "price_variation": ["price variation", "price adjustment", "escalation clause", "price escalation"],
        "incentive_bonus": ["incentive", "bonus clause", "early completion bonus", "performance bonus"]
    }
    
    specific_criteria = {}
    combined_text = " ".join(valid_files.values()).lower()
    
    # Process only criteria that have matching terms in the combined text
    for criteria_type, search_terms in criteria_search_terms.items():
        # Quick check if any search term exists in combined text
        if any(term.lower() in combined_text for term in search_terms):
            sections = _extract_criteria_sections(combined_text, valid_files, criteria_type, search_terms)
            if sections:  # Only add non-empty results
                specific_criteria[criteria_type] = sections
    
    return specific_criteria

def chunk_tender_documents(file_texts: Dict[str, str]) -> Dict[str, Any]:
    """
    Optimized main function to chunk tender documents and extract relevant information.
    
    Args:
        file_texts: Dictionary mapping file names to their text content
        
    Returns:
        Dictionary with categorized chunks and specific criteria extractions
    """
    if not file_texts:
        return {
            "categorized_chunks": {},
            "specific_criteria": {},
            "metadata": {
                "total_files": 0,
                "total_text_length": 0,
                "processed_at": datetime.now().isoformat(),
                "processing_status": "no_files_provided"
            }
        }
    
    # Pre-calculate metadata
    total_text_length = sum(len(text) for text in file_texts.values())
    
    # Process chunks and criteria in parallel conceptually
    categorized_chunks = chunk_by_criteria(file_texts)
    specific_criteria = extract_specific_criteria(file_texts)
    
    # Calculate processing statistics
    total_chunks = sum(len(chunks) for chunks in categorized_chunks.values())
    total_criteria = sum(len(criteria) for criteria in specific_criteria.values())
    
    result = {
        "categorized_chunks": categorized_chunks,
        "specific_criteria": specific_criteria,
        "metadata": {
            "total_files": len(file_texts),
            "total_text_length": total_text_length,
            "total_chunks": total_chunks,
            "total_criteria_sections": total_criteria,
            "categories_found": list(categorized_chunks.keys()),
            "criteria_types_found": list(specific_criteria.keys()),
            "processed_at": datetime.now().isoformat(),
            "processing_status": "completed"
        }
    }
    
    return result

# Additional utility functions for better performance monitoring
def get_processing_stats(result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get detailed statistics about the processing results.
    
    Args:
        result: Result from chunk_tender_documents
        
    Returns:
        Detailed statistics dictionary
    """
    categorized = result.get("categorized_chunks", {})
    criteria = result.get("specific_criteria", {})
    
    return {
        "chunk_distribution": {cat: len(chunks) for cat, chunks in categorized.items()},
        "criteria_distribution": {crit: len(sections) for crit, sections in criteria.items()},
        "largest_category": max(categorized.items(), key=lambda x: len(x[1]))[0] if categorized else None,
        "most_common_criteria": max(criteria.items(), key=lambda x: len(x[1]))[0] if criteria else None,
        "processing_efficiency": {
            "chunks_per_file": result["metadata"]["total_chunks"] / max(1, result["metadata"]["total_files"]),
            "criteria_per_file": result["metadata"]["total_criteria_sections"] / max(1, result["metadata"]["total_files"])
        }
    }