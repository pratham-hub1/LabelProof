import pytest
from src.gauntlet.readability import compute_readability

def test_compute_readability():
    config = {"min_word_count": 3, "min_mean_confidence": 0.65}
    
    # Word count too low
    word_index = [
        {"word": "A", "confidence": 0.9},
        {"word": "B", "confidence": 0.9}
    ]
    assert not compute_readability(word_index, config)
    
    # Word count met, confidence met
    word_index = [
        {"word": "A", "confidence": 0.9},
        {"word": "B", "confidence": 0.8},
        {"word": "C", "confidence": 0.7}
    ]
    assert compute_readability(word_index, config)
    
    # Word count met, confidence too low
    word_index = [
        {"word": "A", "confidence": 0.9},
        {"word": "B", "confidence": 0.5},
        {"word": "C", "confidence": 0.4}
    ]
    assert not compute_readability(word_index, config)
    
    # Empty word index
    assert not compute_readability([], config)
    assert not compute_readability(None, config)
