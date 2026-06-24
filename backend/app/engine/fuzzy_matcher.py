"""
Fuzzy Transaction Matching using Splink

Handles the hard cases that exact matching can't:
- Fuzzy reference matching ("INV-2026-0089" vs "Invoice 2026-0089")
- Date tolerance matching (1-3 day lag)
- Amount tolerance matching (small differences)
- Learning from user corrections

Uses Splink for probabilistic record linkage.

English is the primary language for bank statements.
Amharic OCR is only used for edge cases (customer descriptions, letter numbers).
"""

import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re


@dataclass
class FuzzyMatchResult:
    """Result of fuzzy matching"""
    bank_id: str
    gl_id: str
    match_probability: float
    match_score: float
    match_type: str
    explanation: str
    details: Dict


class FuzzyMatcher:
    """
    Fuzzy transaction matching using Splink.
    
    Falls back to simple fuzzy matching if Splink is not available.
    
    Usage:
        matcher = FuzzyMatcher()
        results = matcher.match(bank_transactions, gl_entries)
    """
    
    def __init__(self, use_splink: bool = True):
        self.use_splink = use_splink
        self._splink_available = False
        
        if use_splink:
            try:
                import splink
                self._splink_available = True
            except ImportError:
                self._splink_available = False
    
    def match(
        self,
        bank_transactions: List[Dict],
        gl_entries: List[Dict],
        amount_tolerance: float = 1.0,
        date_tolerance_days: int = 3,
    ) -> List[FuzzyMatchResult]:
        """
        Match bank transactions to GL entries using fuzzy matching.
        
        Args:
            bank_transactions: List of dicts with id, date, amount, reference, description
            gl_entries: List of dicts with id, date, amount, reference, description
            amount_tolerance: Maximum amount difference for matching
            date_tolerance_days: Maximum date difference in days
        
        Returns:
            List of FuzzyMatchResult
        """
        if not bank_transactions or not gl_entries:
            return []
        
        # Try Splink first
        if self._splink_available:
            try:
                return self._match_with_splink(
                    bank_transactions, gl_entries,
                    amount_tolerance, date_tolerance_days
                )
            except Exception:
                # Fall back to simple fuzzy matching
                pass
        
        # Simple fuzzy matching fallback
        return self._match_simple_fuzzy(
            bank_transactions, gl_entries,
            amount_tolerance, date_tolerance_days
        )
    
    def _match_with_splink(
        self,
        bank_transactions: List[Dict],
        gl_entries: List[Dict],
        amount_tolerance: float,
        date_tolerance_days: int,
    ) -> List[FuzzyMatchResult]:
        """Match using Splink probabilistic record linkage"""
        import splink.duckdb.blocking_rule_library as brl
        import splink.duckdb.comparison_library as cl
        import splink.duckdb.comparison_template_library as ctl
        from splink.duckdb.linker import DuckDBLinker
        
        # Prepare data for Splink
        bank_df = pd.DataFrame(bank_transactions)
        gl_df = pd.DataFrame(gl_entries)
        
        # Add source column
        bank_df['source'] = 'bank'
        gl_df['source'] = 'gl'
        
        # Normalize columns
        bank_df = bank_df.rename(columns={
            'id': 'unique_id',
            'amount': 'amount',
            'reference': 'reference',
            'description': 'description',
            'date': 'date',
        })
        gl_df = gl_df.rename(columns={
            'id': 'unique_id',
            'amount': 'amount',
            'reference': 'reference',
            'description': 'description',
            'date': 'date',
        })
        
        # Combine datasets
        df = pd.concat([bank_df, gl_df], ignore_index=True)
        
        # Convert dates to strings for Splink
        df['date_str'] = df['date'].astype(str)
        
        # Define Splink settings
        settings = {
            "link_type": "link_and_dedupe",
            "comparisons": [
                cl.exact_match("amount", term_frequency_adjustments=True),
                cl.levenshtein_at_thresholds("reference", [1, 2, 3]),
                cl.levenshtein_at_thresholds("description", [3, 5, 10]),
                cl.exact_match("date_str"),
            ],
            "blocking_rules_to_generate_predictions": [
                brl.exact_match_rule("amount"),
                brl.exact_match_rule("date_str"),
            ],
            "retain_matching_columns": True,
            "retain_intermediate_calculation_columns": True,
        }
        
        # Create linker
        linker = DuckDBLinker(df, settings)
        
        # Estimate parameters
        linker.estimate_u_using_random_sampling(max_pairs=1e6)
        
        # Match
        results = linker.predict(threshold_match_probability=0.5)
        
        # Convert results to FuzzyMatchResult
        matches = []
        for _, row in results.iterrows():
            if row['source_l'] == 'bank' and row['source_r'] == 'gl':
                match_type = self._classify_match_type(row)
                matches.append(FuzzyMatchResult(
                    bank_id=row['unique_id_l'],
                    gl_id=row['unique_id_r'],
                    match_probability=row['match_probability'],
                    match_score=row.get('match_weight', 0),
                    match_type=match_type,
                    explanation=self._generate_explanation(row),
                    details={
                        'amount': row.get('amount_l', 0),
                        'reference_l': row.get('reference_l', ''),
                        'reference_r': row.get('reference_r', ''),
                        'date_l': row.get('date_str_l', ''),
                        'date_r': row.get('date_str_r', ''),
                    }
                ))
        
        return matches
    
    def _match_simple_fuzzy(
        self,
        bank_transactions: List[Dict],
        gl_entries: List[Dict],
        amount_tolerance: float,
        date_tolerance_days: int,
    ) -> List[FuzzyMatchResult]:
        """Simple fuzzy matching without Splink"""
        matches = []
        used_gl_ids = set()
        
        for bank in bank_transactions:
            best_match = None
            best_score = 0
            
            for gl in gl_entries:
                if gl['id'] in used_gl_ids:
                    continue
                
                score = self._calculate_match_score(bank, gl, amount_tolerance, date_tolerance_days)
                
                if score > best_score and score > 0.5:
                    best_score = score
                    best_match = gl
            
            if best_match:
                used_gl_ids.add(best_match['id'])
                match_type = self._classify_simple_match(bank, best_match)
                matches.append(FuzzyMatchResult(
                    bank_id=bank['id'],
                    gl_id=best_match['id'],
                    match_probability=best_score,
                    match_score=best_score,
                    match_type=match_type,
                    explanation=self._generate_simple_explanation(bank, best_match, best_score),
                    details={
                        'amount': bank.get('amount', 0),
                        'reference_l': bank.get('reference', ''),
                        'reference_r': best_match.get('reference', ''),
                        'date_l': str(bank.get('date', '')),
                        'date_r': str(best_match.get('date', '')),
                    }
                ))
        
        return matches
    
    def _calculate_match_score(
        self,
        bank: Dict,
        gl: Dict,
        amount_tolerance: float,
        date_tolerance_days: int,
    ) -> float:
        """Calculate match score between two transactions"""
        score = 0.0
        weights = {
            'amount': 0.4,
            'date': 0.25,
            'reference': 0.2,
            'description': 0.15,
        }
        
        # Amount match
        bank_amount = abs(bank.get('amount', 0))
        gl_amount = abs(gl.get('amount', 0))
        amount_diff = abs(bank_amount - gl_amount)
        
        if amount_diff <= amount_tolerance:
            score += weights['amount'] * 1.0
        elif amount_diff <= amount_tolerance * 10:
            score += weights['amount'] * (1.0 - amount_diff / (amount_tolerance * 10))
        
        # Date match
        bank_date = bank.get('date')
        gl_date = gl.get('date')
        if bank_date and gl_date:
            try:
                from datetime import datetime
                if isinstance(bank_date, str):
                    bank_date = datetime.strptime(bank_date, '%Y-%m-%d').date()
                if isinstance(gl_date, str):
                    gl_date = datetime.strptime(gl_date, '%Y-%m-%d').date()
                
                date_diff = abs((bank_date - gl_date).days)
                if date_diff == 0:
                    score += weights['date'] * 1.0
                elif date_diff <= date_tolerance_days:
                    score += weights['date'] * (1.0 - date_diff / (date_tolerance_days + 1))
            except (ValueError, TypeError):
                pass
        
        # Reference match (fuzzy)
        bank_ref = (bank.get('reference') or '').upper().strip()
        gl_ref = (gl.get('reference') or '').upper().strip()
        
        if bank_ref and gl_ref:
            if bank_ref == gl_ref:
                score += weights['reference'] * 1.0
            elif bank_ref in gl_ref or gl_ref in bank_ref:
                score += weights['reference'] * 0.8
            else:
                # Levenshtein-like similarity
                similarity = self._string_similarity(bank_ref, gl_ref)
                score += weights['reference'] * similarity
        
        # Description match (fuzzy)
        bank_desc = (bank.get('description') or '').upper().strip()
        gl_desc = (gl.get('description') or '').upper().strip()
        
        if bank_desc and gl_desc:
            # Check for common words
            bank_words = set(bank_desc.split())
            gl_words = set(gl_desc.split())
            common_words = bank_words & gl_words
            if common_words:
                score += weights['description'] * (len(common_words) / max(len(bank_words), len(gl_words)))
        
        return score
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate string similarity (0-1)"""
        if not s1 or not s2:
            return 0.0
        
        # Simple character-based similarity
        common = sum(1 for a, b in zip(s1, s2) if a == b)
        max_len = max(len(s1), len(s2))
        
        return common / max_len if max_len > 0 else 0.0
    
    def _classify_match_type(self, row) -> str:
        """Classify match type from Splink results"""
        amount_diff = abs(row.get('amount_l', 0) - row.get('amount_r', 0))
        ref_l = (row.get('reference_l') or '').upper()
        ref_r = (row.get('reference_r') or '').upper()
        
        if amount_diff < 0.01 and ref_l == ref_r:
            return 'exact'
        elif amount_diff < 0.01:
            return 'amount_match'
        elif ref_l in ref_r or ref_r in ref_l:
            return 'reference_match'
        else:
            return 'fuzzy'
    
    def _classify_simple_match(self, bank: Dict, gl: Dict) -> str:
        """Classify match type from simple matching"""
        amount_diff = abs(abs(bank.get('amount', 0)) - abs(gl.get('amount', 0)))
        ref_l = (bank.get('reference') or '').upper()
        ref_r = (gl.get('reference') or '').upper()
        
        if amount_diff < 0.01 and ref_l == ref_r:
            return 'exact'
        elif amount_diff < 0.01:
            return 'amount_match'
        elif ref_l in ref_r or ref_r in ref_l:
            return 'reference_match'
        else:
            return 'fuzzy'
    
    def _generate_explanation(self, row) -> str:
        """Generate explanation for Splink match"""
        amount_l = row.get('amount_l', 0)
        amount_r = row.get('amount_r', 0)
        ref_l = row.get('reference_l', '')
        ref_r = row.get('reference_r', '')
        prob = row.get('match_probability', 0)
        
        parts = []
        
        if abs(amount_l - amount_r) < 0.01:
            parts.append(f"Amount ETB {amount_l:,.2f} matches exactly")
        else:
            parts.append(f"Amount ETB {amount_l:,.2f} vs ETB {amount_r:,.2f}")
        
        if ref_l and ref_r:
            if ref_l == ref_r:
                parts.append(f"Reference '{ref_l}' matches exactly")
            elif ref_l in ref_r or ref_r in ref_l:
                parts.append(f"Reference '{ref_l}' partially matches '{ref_r}'")
        
        parts.append(f"Match probability: {prob:.1%}")
        
        return " · ".join(parts)
    
    def _generate_simple_explanation(self, bank: Dict, gl: Dict, score: float) -> str:
        """Generate explanation for simple match"""
        amount = abs(bank.get('amount', 0))
        ref_l = bank.get('reference', '')
        ref_r = gl.get('reference', '')
        
        parts = []
        parts.append(f"Amount ETB {amount:,.2f}")
        
        if ref_l and ref_r:
            if ref_l == ref_r:
                parts.append(f"Reference '{ref_l}' matches")
            elif ref_l in ref_r or ref_r in ref_l:
                parts.append(f"Reference '{ref_l}' ~ '{ref_r}'")
        
        parts.append(f"Fuzzy score: {score:.1%}")
        
        return " · ".join(parts)


def fuzzy_match_transactions(
    bank_transactions: List[Dict],
    gl_entries: List[Dict],
    amount_tolerance: float = 1.0,
    date_tolerance_days: int = 3,
) -> List[Dict]:
    """
    Convenience function for fuzzy matching.
    
    Returns list of match dicts for API response.
    """
    matcher = FuzzyMatcher()
    results = matcher.match(
        bank_transactions, gl_entries,
        amount_tolerance, date_tolerance_days
    )
    
    return [
        {
            'bank_id': r.bank_id,
            'gl_id': r.gl_id,
            'match_probability': r.match_probability,
            'match_score': r.match_score,
            'match_type': r.match_type,
            'explanation': r.explanation,
            'details': r.details,
        }
        for r in results
    ]
