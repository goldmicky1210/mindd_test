"""
Evaluation question sets.  Each question includes:
  - question      : the investor question
  - expected_keywords : words/phrases that MUST appear in a correct answer
  - expected_source   : file type that should be retrieved ("excel" | "pdf" | "text" | any)
  - category          : classification for reporting
"""

QUESTION_SETS: dict[str, list[dict]] = {
    "default": [
        {
            "question": "What is the company's current monthly burn rate?",
            "expected_keywords": ["burn", "monthly"],
            "expected_source": "excel",
            "category": "financial_metrics",
        },
        {
            "question": "How many months of runway does the company have?",
            "expected_keywords": ["runway", "months"],
            "expected_source": "excel",
            "category": "financial_metrics",
        },
        {
            "question": "What is the company's current ARR or annual recurring revenue?",
            "expected_keywords": ["arr", "annual recurring revenue", "revenue"],
            "expected_source": "excel",
            "category": "financial_metrics",
        },
        {
            "question": "What is the projected revenue growth for 2026?",
            "expected_keywords": ["growth", "revenue", "2026"],
            "expected_source": "excel",
            "category": "financial_projections",
        },
        {
            "question": "What are the key risks mentioned in the pitch deck?",
            "expected_keywords": ["risk"],
            "expected_source": "pdf",
            "category": "qualitative",
        },
        {
            "question": "What assumptions drive the revenue model?",
            "expected_keywords": ["assumption", "revenue", "growth"],
            "expected_source": "any",
            "category": "financial_model",
        },
        {
            "question": "What is the company's gross margin?",
            "expected_keywords": ["gross margin", "margin"],
            "expected_source": "excel",
            "category": "financial_metrics",
        },
        {
            "question": "What is the company's current MRR?",
            "expected_keywords": ["mrr", "monthly recurring revenue"],
            "expected_source": "excel",
            "category": "financial_metrics",
        },
        {
            "question": "What is the company's business model and target market?",
            "expected_keywords": ["business", "market", "customer"],
            "expected_source": "pdf",
            "category": "qualitative",
        },
        {
            "question": "What is the company's total headcount and team composition?",
            "expected_keywords": ["team", "headcount", "employee"],
            "expected_source": "any",
            "category": "qualitative",
        },
        {
            "question": "What are the main expenses and cost drivers?",
            "expected_keywords": ["expense", "cost", "salary", "burn"],
            "expected_source": "excel",
            "category": "financial_metrics",
        },
        {
            "question": "What is the company's cash position?",
            "expected_keywords": ["cash", "balance"],
            "expected_source": "excel",
            "category": "financial_metrics",
        },
    ],
}
