import re
from num2words import num2words
import os
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

# Configurações ajustáveis
PAUSE_LONG = os.getenv('PAUSE_LONG', '1s')
PAUSE_SHORT = os.getenv('PAUSE_SHORT', '500ms')
PROSODY_RATE = os.getenv('PROSODY_RATE', 'medium')
EMPHASIS_LEVEL = os.getenv('EMPHASIS_LEVEL', 'strong')
MAX_TEXT_LENGTH = int(os.getenv('MAX_TEXT_LENGTH', '3000'))

# Lista de palavras-chave para ênfase
KEYWORDS = os.getenv('KEYWORDS', 'importante,atenção,observe,veículos').split(',')

# Trechos específicos para ajuste de velocidade
SLOW_RATE_PHRASES = os.getenv('SLOW_RATE_PHRASES', 'Fundos de Tijolo,Fundos de Papel,Fundos Híbridos,Fundos de Desenvolvimento').split(',')

def preprocess_text_pt_br(text):
    # Converter números para palavras
    text = re.sub(r'\b\d+\b', lambda m: num2words(int(m.group()), lang='pt_BR'), text)
    
    # Adicionar pausas após pontuação
    text = re.sub(r'([.!?])(\s|$)', f'\\1 \\2', text)
    text = re.sub(r'(,|;)(\s|$)', f'\\1 \\2', text)
    
    # Adicionar ênfase em palavras-chave (sem usar tags SSML)
    for keyword in KEYWORDS:
        text = re.sub(rf'\b{keyword}\b', f'{keyword}', text, flags=re.IGNORECASE)
    
    # Ajustar velocidade para trechos específicos (sem usar tags SSML)
    for phrase in SLOW_RATE_PHRASES:
        text = re.sub(rf'\b({phrase})\b', r'\1', text)
    
    # Remover caracteres especiais e formatar o texto
    text = re.sub(r'[^\w\s.,?!]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text

def split_text(text, max_length=MAX_TEXT_LENGTH):
    # Dividir o texto em partes menores
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