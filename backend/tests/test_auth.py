"""
Tests for JWT Authentication
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.api.auth import (
    hash_password, verify_password, create_token, decode_token
)
from datetime import timedelta


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "SecurePass123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
    
    def test_wrong_password(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False
    
    def test_different_hashes(self):
        """Same password should produce different hashes (random salt)"""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2  # Different salts
        assert verify_password("same_password", h1) is True
        assert verify_password("same_password", h2) is True
    
    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("not_empty", hashed) is False


class TestJWTToken:
    def test_create_and_decode(self):
        payload = {"sub": "user-123", "email": "test@test.com", "role": "clerk"}
        token = create_token(payload, timedelta(hours=1))
        
        decoded = decode_token(token)
        assert decoded is not None
        assert decoded["sub"] == "user-123"
        assert decoded["email"] == "test@test.com"
        assert decoded["role"] == "clerk"
    
    def test_token_expiry(self):
        payload = {"sub": "user-123"}
        token = create_token(payload, timedelta(seconds=-1))  # Already expired
        
        decoded = decode_token(token)
        assert decoded is None
    
    def test_token_tampering(self):
        payload = {"sub": "user-123"}
        token = create_token(payload, timedelta(hours=1))
        
        # Tamper with payload
        parts = token.split('.')
        parts[1] = parts[1][:-1] + ('A' if parts[1][-1] != 'A' else 'B')
        tampered = '.'.join(parts)
        
        decoded = decode_token(tampered)
        assert decoded is None
    
    def test_invalid_token(self):
        assert decode_token("not.a.token") is None
        assert decode_token("") is None
        assert decode_token("abc.def") is None
    
    def test_token_contains_issuer(self):
        token = create_token({"sub": "u1"}, timedelta(hours=1))
        decoded = decode_token(token)
        assert decoded["iss"] == "reconet"
