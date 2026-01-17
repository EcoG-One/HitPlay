#!/usr/bin/env python3
"""
Script to generate flashcards array from audio files in the music folder.
Extracts metadata (artist, title, year) from audio files and creates flashcard entries.
"""

import os
import json
import random
from pathlib import Path
from mutagen.flac import FLAC
from mutagen.easyid3 import EasyID3
from mutagen.wave import WAVE

# Unicode emoji list for randomization
EMOJIS = [
    "🎵", "🎶", "🎤", "🎧", "🎸", "🎹", "🎺", "🎷", "🥁", "🎼",
    "👑", "⭐", "🌟", "✨", "💫", "🔥", "❤️", "💯", "🎉", "🎊",
    "🕺", "💃", "🙌", "👏", "✌️", "🤘", "🎯", "🏆", "🥇", "🌈",
    "☀️", "🌙", "⚡", "🌊", "🌸", "🦋", "🐝", "🎭", "🎪", "🎨"
]

def get_audio_metadata(file_path):
    """
    Extract artist, title, and year from audio file metadata.
    Returns a tuple of (artist, title, year) or None if extraction fails.
    """
    try:
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == '.flac':
            audio = FLAC(file_path)
            artist = ' & '.join(audio.get('artist', ['Unknown Artist']))
            title = audio.get('title', ['Unknown Title'])[0]
            year = audio.get('date', [''])[0].split('-')[0]  # Extract year from date
        elif ext in ['.mp3']:
            audio = EasyID3(file_path)
            artist = ' & '.join(audio.get('artist', ['Unknown Artist']))
            title = audio.get('title', ['Unknown Title'])[0]
            year = audio.get('date', [''])[0].split('-')[0]
        elif ext in ['.wav']:
            audio = WAVE(file_path)
            # WAV files may not have standard metadata
            artist = 'Unknown Artist'
            title = 'Unknown Title'
            year = ''
        else:
            return None
        
        # Clean up year (make sure it's 4 digits or empty)
        if year and not year.isdigit():
            year = ''
        
        return (artist.strip(), title.strip(), year.strip())
    except Exception as e:
        print(f"Warning: Could not read metadata from {file_path}: {e}")
        return None

def generate_flashcards(music_folder):
    """
    Scan music folder and generate flashcard entries.
    """
    flashcards = []
    
    # Supported audio formats
    supported_formats = {'.flac', '.mp3', '.wav', '.m4a', '.ogg'}
    
    # Get all audio files in the music folder
    audio_files = []
    for filename in os.listdir(music_folder):
        file_path = os.path.join(music_folder, filename)
        if os.path.isfile(file_path):
            _, ext = os.path.splitext(filename)
            if ext.lower() in supported_formats:
                audio_files.append((filename, file_path))
    
    # Sort files alphabetically for consistency
    audio_files.sort()
    
    # Generate flashcard entries
    for filename, file_path in audio_files:
        metadata = get_audio_metadata(file_path)
        
        if metadata:
            artist, title, year = metadata
            # Build definition string
            if year:
                definition = f"{artist} - {title} - {year}"
            else:
                definition = f"{artist} - {title}"
        else:
            # Fallback to filename if metadata extraction fails
            definition = os.path.splitext(filename)[0]
        
        # Use relative path as term
        relative_path = f"music/{filename}"
        
        # Random emoji
        emoji = random.choice(EMOJIS)
        
        flashcards.append({
            "term": relative_path,
            "definition": definition,
            "emoji": emoji
        })
        
        print(f"✓ {filename}")
        print(f"  Definition: {definition}")
        print(f"  Emoji: {emoji}\n")
    
    return flashcards

def format_flashcards_js(flashcards):
    """
    Format flashcards array as JavaScript code.
    """
    lines = ["    const flashcards = ["]
    
    for i, card in enumerate(flashcards):
        term_escaped = card['term'].replace('"', '\\"')
        def_escaped = card['definition'].replace('"', '\\"')
        
        comma = "," if i < len(flashcards) - 1 else ""
        lines.append(f'      {{ term: "{term_escaped}", definition: "{def_escaped}", emoji: "{card["emoji"]}" }}{comma}')
    
    lines.append("    ];")
    return "\n".join(lines)

def main():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    music_folder = os.path.join(script_dir, "music")
    html_file = os.path.join(script_dir, "HitPlay.html")
    
    if not os.path.exists(music_folder):
        print(f"Error: Music folder not found at {music_folder}")
        return
    
    print(f"Scanning music folder: {music_folder}\n")
    
    # Generate flashcards
    flashcards = generate_flashcards(music_folder)
    
    if not flashcards:
        print("No audio files found in music folder!")
        return
    
    print(f"\n{'='*60}")
    print(f"Generated {len(flashcards)} flashcard entries")
    print(f"{'='*60}\n")
    
    # Format as JavaScript
    js_code = format_flashcards_js(flashcards)
    
    print("JavaScript array to insert at line 136 of HitPlay.html:\n")
    print(js_code)
    print("\n")
    
    # Also generate JSON for reference
    print("JSON representation (for reference):\n")
    print(json.dumps(flashcards, indent=2))

if __name__ == "__main__":
    main()
