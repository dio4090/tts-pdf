import re
from num2words import num2words
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Adjustable settings
PAUSE_LONG = os.getenv('PAUSE_LONG', '1s')
PAUSE_SHORT = os.getenv('PAUSE_SHORT', '500ms')
PROSODY_RATE = os.getenv('PROSODY_RATE', 'medium')
EMPHASIS_LEVEL = os.getenv('EMPHASIS_LEVEL', 'strong')
MAX_TEXT_LENGTH = int(os.getenv('MAX_TEXT_LENGTH', '3000'))

# List of keywords for emphasis
KEYWORDS = os.getenv('KEYWORDS_EN', 'important,attention,note,vehicles').split(',')

# Specific phrases for speed adjustment
SLOW_RATE_PHRASES = os.getenv('SLOW_RATE_PHRASES_EN', 'Brick Funds,Paper Funds,Hybrid Funds,Development Funds').split(',')

def preprocess_text_en_us(text):
    # Convert numbers to words
    text = re.sub(r'\b\d+\b', lambda m: num2words(int(m.group()), lang='en'), text)
    
    # Add pauses after punctuation
    text = re.sub(r'([.!?])(\s|$)', f'\\1 \\2', text)
    text = re.sub(r'(,|;)(\s|$)', f'\\1 \\2', text)
    
    # Add emphasis to keywords (without using SSML tags)
    for keyword in KEYWORDS:
        text = re.sub(rf'\b{keyword}\b', f'{keyword}', text, flags=re.IGNORECASE)
    
    # Adjust speed for specific phrases (without using SSML tags)
    for phrase in SLOW_RATE_PHRASES:
        text = re.sub(rf'\b({phrase})\b', r'\1', text)
    
    # Remove special characters and format the text
    text = re.sub(r'[^\w\s.,?!]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def split_text(text, max_length=MAX_TEXT_LENGTH):
    # Split the text into smaller parts
    sentences = re.split(r'(?<=[.!?])\s+', text)
    parts = []
    current_part = ""
    
    for sentence in sentences:
        if len(current_part) + len(sentence) < max_length:
            current_part += sentence + " "
        else:
            parts.append(current_part.strip())
            current_part = sentence + " "
    
    if current_part:
        parts.append(current_part.strip())
    
    return parts

# Additional English-specific preprocessing functions can be added here

def expand_contractions(text):
    """
    Expand common English contractions.
    """
    contractions = {
        "ain't": "is not",
        "aren't": "are not",
        "can't": "cannot",
        "couldn't": "could not",
        "didn't": "did not",
        "doesn't": "does not",
        "don't": "do not",
        "hadn't": "had not",
        "hasn't": "has not",
        "haven't": "have not",
        "he'd": "he would",
        "he'll": "he will",
        "he's": "he is",
        "I'd": "I would",
        "I'll": "I will",
        "I'm": "I am",
        "I've": "I have",
        "isn't": "is not",
        "it's": "it is",
        "let's": "let us",
        "mightn't": "might not",
        "mustn't": "must not",
        "shan't": "shall not",
        "she'd": "she would",
        "she'll": "she will",
        "she's": "she is",
        "shouldn't": "should not",
        "that's": "that is",
        "there's": "there is",
        "they'd": "they would",
        "they'll": "they will",
        "they're": "they are",
        "they've": "they have",
        "we'd": "we would",
        "we're": "we are",
        "we've": "we have",
        "weren't": "were not",
        "what'll": "what will",
        "what're": "what are",
        "what's": "what is",
        "what've": "what have",
        "where's": "where is",
        "who'd": "who would",
        "who'll": "who will",
        "who're": "who are",
        "who's": "who is",
        "who've": "who have",
        "won't": "will not",
        "wouldn't": "would not",
        "you'd": "you would",
        "you'll": "you will",
        "you're": "you are",
        "you've": "you have"
    }
    
    pattern = re.compile(r'\b(' + '|'.join(contractions.keys()) + r')\b', flags=re.IGNORECASE)
    return pattern.sub(lambda x: contractions[x.group().lower()], text)

def preprocess_text_en_us_extended(text):
    # Expand contractions first
    text = expand_contractions(text)
    
    # Then apply the standard preprocessing
    return preprocess_text_en_us(text)