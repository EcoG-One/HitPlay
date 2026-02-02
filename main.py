#!/usr/bin/env python3
"""
Script to generate flashcards array from audio files in the music folder.
Extracts metadata (artist, title, year) from audio files and creates flashcard entries.
"""
import webbrowser
import threading
import re
from PySide6.QtCore import QObject, Qt, QMetaObject, Signal, Slot
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog, QMessageBox
import argparse
import json
import os
import sys
import random
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import pygetwindow as gw
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, urlencode
from urllib.request import Request, urlopen
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

MUSICBRAINZ_RECORDING_URL = "https://musicbrainz.org/ws/2/recording/"
MUSICBRAINZ_USER_AGENT = "HitPlay/1.0 (ecog@outlook.de)"
WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
WIKIPEDIA_USER_AGENT = "HitPlay/1.0 (ecog@outlook.de)"


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        QMessageBox.warning(window, "Error!", str(e))
    return default


def save_json(path: Path, obj):
    try:
        path.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    except Exception as e:
        QMessageBox.warning(window, "Error!", str(e))


def select_directory_dialog():
    selected_directory = None
    file_dialog = QFileDialog()
    file_dialog.setWindowTitle("Select Directory")
    file_dialog.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    file_dialog.setWindowModality(Qt.ApplicationModal)
    file_dialog.setFileMode(QFileDialog.FileMode.Directory)
    file_dialog.setViewMode(QFileDialog.ViewMode.List)
    browser = gw.getActiveWindow()
    browser.minimize()
    window.show()
    launcher = gw.getWindowsWithTitle("HitPlayLauncher")[0]
    launcher.maximize()
    if file_dialog.exec():
        selected_directory = file_dialog.selectedFiles()[0]
    else:
        QMessageBox.information(
            window, "Info!", "You cancelled the directory selection."
        )
    window.hide()
    browser.restore()
    return selected_directory


def _extract_year(date_str):
    if not date_str:
        return ""
    year = date_str.split("-")[0]
    if len(year) == 4 and year.isdigit():
        return year
    return ""


def _extract_year_from_text(text):
    if not text:
        return ""
    match = re.search(r"\b(19[0-9]{2}|20[0-9]{2})\b", str(text))
    return match.group(0) if match else ""


def _extract_earliest_year_from_text(text):
    if not text:
        return ""
    years = re.findall(r"\b(19[0-9]{2}|20[0-9]{2})\b", str(text))
    return min(years) if years else ""

def _strip_title_parenthetical_terms(title):
    if not title:
        return title
    terms = r"remix|remastered|anniversary|version|live|single|album|stereo|mono|edition"
    pattern = re.compile(rf"\s*\([^)]*\b(?:{terms})\b[^)]*\)\s*", re.IGNORECASE)
    cleaned = re.sub(pattern, " ", title)
    return re.sub(r"\s{2,}", " ", cleaned).strip()


def fetch_wikipedia_released_year(artist, title):
    if not artist or not title:
        return ""

    def _opensearch(query):
        params = {
            "action": "opensearch",
            "search": query,
            "limit": 10,
            "namespace": 0,
            "format": "json",
        }
        url = f"{WIKIPEDIA_API_URL}?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": WIKIPEDIA_USER_AGENT})
        with urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data if data and len(data) >= 2 else ["", []]

    search_term = title
    try:
        data = _opensearch(search_term)
        titles = data[1]
        if not titles:
            return ""
        if len(titles) > 1:
            data = _opensearch(f"{title} (song)")
            titles = data[1]
        if len(titles) > 1:
            data = _opensearch(f"{title} ({artist} song)")
            titles = data[1]
        if not titles:
            return ""
        page_title = titles[0]

        params = {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": page_title,
            "format": "json",
        }
        url = f"{WIKIPEDIA_API_URL}?{urlencode(params)}"
        request = Request(url, headers={"User-Agent": WIKIPEDIA_USER_AGENT})
        with urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))

        pages = data.get("query", {}).get("pages", {})
        page = next(iter(pages.values()), {})
        revisions = page.get("revisions", [])
        if not revisions:
            return ""
        wikitext = revisions[0].get("slots", {}).get("main", {}).get("*", "")
        if not wikitext:
            return ""

        match = re.search(
            r"^\s*\|\s*released\s*=\s*(.+?)(?=^\s*\|\s*|\n}}\s*$)",
            wikitext,
            re.MULTILINE | re.DOTALL,
        )
        if not match:
            return ""
        released_text = match.group(1)
        return _extract_earliest_year_from_text(released_text)

    except Exception as e:
        print(f"Warning: Wikipedia lookup failed for {artist} - {title}: {e}")
        return ""


def fetch_musicbrainz_year(artist, title):
    if not artist or not title:
        return ""
    query = (
        f'artist:"{artist}" AND recording:"{title}" AND NOT release-group:compilation'
    )
    url = f"{MUSICBRAINZ_RECORDING_URL}?query={quote(query)}&fmt=json&inc=releases"
    time.sleep(1)  # To respect MusicBrainz rate limiting
    for attempt in range(2):
        try:
            request = Request(url, headers={"User-Agent": MUSICBRAINZ_USER_AGENT})
            with urlopen(request, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
            break
        except Exception as e:
            is_reset = (
                getattr(e, "winerror", None) == 10054
                or "[WinError 10054]" in str(e)
            )
            is_503 = "HTTP Error 503: Service Temporarily Unavailable" in str(e)
            if (is_reset or is_503) and attempt == 0:
                print(str(e))
                print("Retrying MusicBrainz lookup after a short delay...")
                if is_503:
                    time.sleep(1)
                else:
                    time.sleep(0.5)
                continue
            print(f"Warning: MusicBrainz lookup failed for {artist} - {title}: {e}")
            return ""

    best_year = ""
    for recording in data.get("recordings", []):
        release = recording.get("releases", [])
        if not release:
            continue
        release_group = release[0].get("release-group", [])
        secondary_types = release_group.get("secondary-types", [])
        for secondary_type in secondary_types:
            if secondary_type in ["Compilation", "Live", "Remix", "DJ-mix", "Mixtape/Street", "Demo"]:
                continue

        year = _extract_year(recording.get("first-release-date", ""))
        if not year:
            for release in recording.get("releases", []) or []:
                year = _extract_year(release.get("date", ""))
                if year:
                    break
        if year and (not best_year or year < best_year):
            best_year = year
    return best_year


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
            title = _strip_title_parenthetical_terms(
                audio.get('title', ['Unknown Title'])[0]
            )
            copyright_year = _extract_year_from_text(audio.get('copyright', [''])[0])
            date_year = _extract_year(audio.get('date', [''])[0])
            year_candidates = [y for y in [copyright_year, date_year] if y]
            year = min(year_candidates) if year_candidates else ''
        elif ext in ['.mp3', '.ogg']:
            audio = EasyID3(file_path)
            artist = ' & '.join(audio.get('artist', ['Unknown Artist']))
            title = _strip_title_parenthetical_terms(
                audio.get('title', ['Unknown Title'])[0]
            )
            copyright_year = _extract_year_from_text(audio.get('copyright', [''])[0])
            date_year = _extract_year(audio.get('date', [''])[0])
            year_candidates = [y for y in [copyright_year, date_year] if y]
            year = min(year_candidates) if year_candidates else ''
        elif ext in ['.wav']:
            audio = WAVE(file_path)
            # WAV files may not have standard metadata
            artist = os.path.basename(file_path)
            artist = os.path.splitext(artist)[1]
            title = ''
            year = ''
        else:
            return None

        wikipedia_year = fetch_wikipedia_released_year(artist.strip(), title.strip())
        if wikipedia_year:
            year = min([y for y in [year, wikipedia_year] if y])
        else:
            musicbrainz_year = fetch_musicbrainz_year(artist.strip(), title.strip())
            if musicbrainz_year:
                year = min([y for y in [year, musicbrainz_year] if y])

        # Clean up year (make sure it's 4 digits or empty)
        if year and not year.isdigit():
            year = ''

        return (artist.strip(), title.strip(), year.strip())
    except Exception as e:
        print(f"Warning: Could not read metadata from {file_path}: {e}")
        return None


def audio_url_from_filename(filename):
    return "music/" + quote(filename)


def generate_flashcards(music_folder):
    """
    Scan music folder and generate flashcard entries.
    """
    flashcards = []

    # Supported audio formats
    supported_formats = {'.flac', '.mp3', '.wav', '.ogg'}

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

        # Random emoji
        emoji = random.choice(EMOJIS)

        flashcards.append(
            {
                "term": audio_url_from_filename(filename),
                "definition": definition,
                "emoji": emoji,
            }
        )

       # print(f"✓ {filename}")
       # print(f"  Definition: {definition}")
       # print(f"  Emoji: {emoji}\n")

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

def write_flashcards_json(flashcards, output_path):
    """
    Write flashcards to a JSON file for the web client to fetch.
    """
    try:
        output_path.write_text(
            json.dumps(flashcards, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as e:
        print(f"Error writing JSON file: {e}")
        return
    print(f"Wrote JSON to {output_path}")


def make_handler(base_dir, state):
    class MusicHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(base_dir), **kwargs)

        def do_GET(self):
            request_path = urlsplit(self.path).path
            if request_path == "/change-folder":
                try:
                    runner = state.get("dialog_runner")
                    if runner:
                        event = threading.Event()
                        result = {"value": ""}

                        def on_selected(path):
                            result["value"] = path
                            event.set()

                        runner.folder_selected.connect(on_selected, Qt.QueuedConnection)
                        QMetaObject.invokeMethod(
                            runner, "choose_folder", Qt.QueuedConnection
                        )
                        event.wait(timeout=120)
                        runner.folder_selected.disconnect(on_selected)
                        new_folder = result["value"]
                    else:
                        new_folder = select_directory_dialog()
                    if new_folder:
                        state["music_dir"] = new_folder
                        state["settings"]["music_folder"] = new_folder
                        state["json_file"] = Path(new_folder) / "flashcards.json"
                        save_json(state["settings_file"], state["settings"])
                        flashcards = generate_flashcards(new_folder)
                        if flashcards:
                            write_flashcards_json(flashcards, state["json_file"])
                    self.send_response(204)
                    self.end_headers()
                except Exception as e:
                    self.send_response(500)
                    self.send_header("Content-Type", "text/plain; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(str(e).encode("utf-8"))
                return
            super().do_GET()

        def translate_path(self, path):
            request_path = urlsplit(path).path
            if request_path.startswith("/music/"):
                rel = unquote(request_path[len("/music/") :])
                return str(Path(state["music_dir"]) / rel)
            if request_path == "/flashcards.json":
                return str(state["json_file"])
            return super().translate_path(request_path)

    return MusicHandler


def serve_directory(directory, host, port, state):
    """
    Serve static files from the given directory.
    """
    handler = make_handler(directory, state)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving {directory} at http://{host}:{port}/")
    print(f"Open http://{host}:{port}/index.html")
    print(
        f"Serving music files from {state['music_dir']} at http://{host}:{port}/music/"
    )
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    def fin():
        server.shutdown()


def main():
    print(f"\n{'='*60}")
    print("WELCOME TO HiTPLAY!")
    print(f"\n{'='*60}\n")
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html_file = os.path.join(script_dir, "index.html")
    settings_file = Path(script_dir) / "settings.json"
    # default_music_folder = {"music_folder": os.path.join(script_dir, "music")}
    json_settings = load_json(settings_file, default={})

    music_folder = json_settings.get("music_folder")

    if not music_folder or not os.path.isdir(music_folder):
        music_folder = select_directory_dialog()
        if not music_folder:
            return
        json_settings["music_folder"] = music_folder
        save_json(settings_file, json_settings)

    if not os.path.exists(music_folder):
        print(f"Error: Music folder not found at {music_folder}")
        return
    json_file = Path(music_folder) / "flashcards.json"
    print(f"Using music folder: {music_folder}")

    # Generate flashcards
    if os.path.isfile(json_file):
        flashcards = load_json(json_file, default={})
        print(f"\n{'='*60}")
        print(f"Loaded {len(flashcards)} flashcard entries from {json_file}")
        print(f"\n{'='*60}")
    else:
        print(f"Scanning music folder: {music_folder}\n")
        print("This may take a few moments...")
        flashcards = generate_flashcards(music_folder)
        print(f"\n{'='*60}")
        print(f"Generated {len(flashcards)} flashcard entries")
        print(f"{'='*60}\n")

        # Format as JavaScript
        js_code = format_flashcards_js(flashcards)

        # print("JavaScript array to insert at line 136 of HitPlay.html:\n")
        # print(js_code)
        # print("\n")

        # Also generate JSON for reference
        # print("JSON representation (for reference):\n")
        # print(json.dumps(flashcards, indent=2))
        json.dumps(flashcards, indent=2)

        write_flashcards_json(flashcards, json_file)

        if not flashcards:
            print("No audio files found in music folder!")
            return

    parser = argparse.ArgumentParser(description="Generate flashcards and serve them.")
    parser.add_argument(
        "--serve", action="store_true", help="Start a local web server."
    )
    parser.add_argument(
        "--host", default="localhost", help="Server host (default: localhost)."
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Server port (default: 8000)."
    )
    args = parser.parse_args()
    webbrowser.open(f"http://{args.host}:{args.port}")
    state = {
        "music_dir": music_folder,
        "settings": json_settings,
        "settings_file": settings_file,
        "json_file": json_file,
        "dialog_runner": window.dialog_runner,
    }
    serve_directory(script_dir, args.host, args.port, state)


class AppWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.worker = None
        self.dialog_runner = DialogRunner()
        self.setWindowTitle("HitPlayLauncher")
        self.setGeometry(500, 100, 500, 400)


class DialogRunner(QObject):
    folder_selected = Signal(str)

    @Slot()
    def choose_folder(self):
        folder = select_directory_dialog() or ""
        self.folder_selected.emit(folder)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = AppWindow()
    # window.show()
    main()
    sys.exit(app.exec())
