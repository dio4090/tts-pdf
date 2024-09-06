import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import PyPDF2
import boto3
import os
from dotenv import load_dotenv
import tempfile
from botocore.exceptions import BotoCoreError, ClientError
from tracker import PollyUsageTracker
from text_preprocessor_pt_br import preprocess_text_pt_br, split_text
from text_preprocessor_en_us import preprocess_text_en_us_extended, split_text
import pygame

# Carrega o conteúdo do arquivo .env
load_dotenv()

# Acessa as variáveis de ambiente
AWS_KEY = os.getenv("ACCESS_KEY_ID")
AWS_SECRET = os.getenv("SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-west-2")

LANGUAGES = {
    "Portuguese": "pt-BR",
    "English": "en-US"
}

TEST_TEXTS = {
    "Portuguese": "Este é um teste da voz selecionada em português.",
    "English": "This is a test of the selected voice in English."
}

def get_voice_capabilities():
    polly_client = boto3.Session(
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
        region_name=AWS_REGION
    ).client('polly')

    voices = {}
    for lang_name, lang_code in LANGUAGES.items():
        try:
            response = polly_client.describe_voices(LanguageCode=lang_code)
            for voice in response['Voices']:
                voices[voice['Id']] = {
                    'language': lang_name,
                    'gender': voice['Gender'],
                    'engine': voice['SupportedEngines']
                }
        except (BotoCoreError, ClientError) as error:
            print(f"Erro ao obter vozes para {lang_name}: {error}")
    
    return voices

def extract_text_from_pdf(pdf_path, start_page=None, end_page=None):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        total_pages = len(reader.pages)
        
        # Adjust page range if not specified or out of bounds
        start_page = max(1, min(start_page or 1, total_pages))
        end_page = min(end_page or total_pages, total_pages)
        
        text = ''
        for page_num in range(start_page - 1, end_page):
            text += reader.pages[page_num].extract_text()
    return text

def text_to_speech(text, output_file, voice_id, language_code):
    polly_client = boto3.Session(
        aws_access_key_id=AWS_KEY,
        aws_secret_access_key=AWS_SECRET,
        region_name=AWS_REGION
    ).client('polly')

    try:
        # Dividir o texto em partes menores
        text_parts = split_text(text)
        
        # Sintetizar cada parte do texto
        audio_parts = []
        for part in text_parts:
            try:
                # Tenta primeiro com o motor neural
                response = polly_client.synthesize_speech(
                    Text=part,
                    TextType="text",
                    OutputFormat="mp3",
                    VoiceId=voice_id,
                    LanguageCode=language_code,
                    Engine="neural",
                    SampleRate="24000",
                    # Adicione configurações para melhorar a qualidade da fala
                    SpeechMarkTypes=["word"],
                    # Ajuste a velocidade da fala (1.0 é a velocidade normal)
                    VoiceSettings={"EngineSettings": {"SpeechRatePercentage": "100"}}
                )
                audio_parts.append(response['AudioStream'].read())
            except ClientError as e:
                if 'UnsupportedEngine' in str(e):
                    # Se falhar com neural, tenta com standard
                    response = polly_client.synthesize_speech(
                        Text=part,
                        TextType="text",
                        OutputFormat="mp3",
                        VoiceId=voice_id,
                        LanguageCode=language_code,
                        Engine="standard",
                        SampleRate="24000"
                    )
                    audio_parts.append(response['AudioStream'].read())
                else:
                    raise

        # Combinar todas as partes de áudio
        with open(output_file, 'wb') as file:
            for part in audio_parts:
                file.write(part)

    except (BotoCoreError, ClientError) as error:
        raise Exception(f"Falha ao sintetizar fala: {error}")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("PDF to Speech Converter")
        self.geometry("980x620")

        self.usage_tracker = PollyUsageTracker()
        self.usage_tracker.load_from_file()  # Load previous usage data if available

        # Initialize voice_capabilities
        self.voice_capabilities = {}

        # Fetch voice capabilities from Amazon Polly
        try:
            self.voice_capabilities = get_voice_capabilities()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load voice capabilities: {str(e)}")

        # Create the main screen
        self.create_main_screen()

        # Create admin screen
        self.create_admin_screen()

        # Update voice options with the fetched data
        self.update_voice_options()

        # Inicialize o pygame mixer
        pygame.mixer.init()

    def create_admin_screen(self):
        self.admin_frame = ctk.CTkFrame(self)
        self.admin_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.admin_frame.grid_columnconfigure(0, weight=1)

        self.admin_label = ctk.CTkLabel(self.admin_frame, text="Admin Panel - Polly Usage")
        self.admin_label.grid(row=0, column=0, padx=10, pady=10)

        self.log_text = ctk.CTkTextbox(self.admin_frame, width=300, height=400)
        self.log_text.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")

        self.refresh_button = ctk.CTkButton(self.admin_frame, text="Refresh Log", command=self.refresh_log)
        self.refresh_button.grid(row=2, column=0, padx=10, pady=10)

        self.save_log_button = ctk.CTkButton(self.admin_frame, text="Save Log", command=self.save_log)
        self.save_log_button.grid(row=3, column=0, padx=10, pady=10)

        self.refresh_log()  # Initial log display

    def refresh_log(self):
        self.log_text.delete("1.0", tk.END)
        summary = self.usage_tracker.get_summary()
        log_entries = self.usage_tracker.get_log()

        summary_text = f"Total Characters: {summary['total_characters']}\n"
        summary_text += f"Total Requests: {summary['total_requests']}\n"
        summary_text += f"Avg. Characters/Request: {summary['average_characters_per_request']:.2f}\n\n"
        
        self.log_text.insert(tk.END, summary_text)

        for entry in log_entries:
            entry_text = f"{entry['timestamp']} - {entry['characters']} chars, "
            entry_text += f"Voice: {entry['voice_id']}, Engine: {entry['engine']}\n"
            self.log_text.insert(tk.END, entry_text)

    def save_log(self):
        self.usage_tracker.save_to_file()
        messagebox.showinfo("Log Saved", "The usage log has been saved successfully.")

    def create_main_screen(self):
        # Initialize variables
        self.pdf_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.language = tk.StringVar(value="Portuguese")
        self.voice_id = tk.StringVar()

        # Create main frame
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")

        # PDF Selection
        self.pdf_label = ctk.CTkLabel(self.main_frame, text="Select PDF:")
        self.pdf_label.grid(row=0, column=0, padx=10, pady=(10, 0), sticky="w")

        self.pdf_entry = ctk.CTkEntry(self.main_frame, textvariable=self.pdf_path, width=400)
        self.pdf_entry.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.pdf_button = ctk.CTkButton(self.main_frame, text="Browse", command=self.browse_pdf)
        self.pdf_button.grid(row=1, column=1, padx=10, pady=(0, 10))

        # Page Range Selection (moved up)
        self.page_range_label = ctk.CTkLabel(self.main_frame, text="Page Range (optional):")
        self.page_range_label.grid(row=2, column=0, padx=10, pady=(10, 0), sticky="w")

        self.page_range_frame = ctk.CTkFrame(self.main_frame)
        self.page_range_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")

        self.start_page_label = ctk.CTkLabel(self.page_range_frame, text="Start:")
        self.start_page_label.grid(row=0, column=0, padx=(0, 5), pady=5)
        self.start_page_entry = ctk.CTkEntry(self.page_range_frame, width=50)
        self.start_page_entry.grid(row=0, column=1, padx=5, pady=5)

        self.end_page_label = ctk.CTkLabel(self.page_range_frame, text="End:")
        self.end_page_label.grid(row=0, column=2, padx=(10, 5), pady=5)
        self.end_page_entry = ctk.CTkEntry(self.page_range_frame, width=50)
        self.end_page_entry.grid(row=0, column=3, padx=5, pady=5)

        # Output Selection
        self.output_label = ctk.CTkLabel(self.main_frame, text="Output File:")
        self.output_label.grid(row=4, column=0, padx=10, pady=(10, 0), sticky="w")

        self.output_entry = ctk.CTkEntry(self.main_frame, textvariable=self.output_path, width=400)
        self.output_entry.grid(row=5, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.output_button = ctk.CTkButton(self.main_frame, text="Browse", command=self.browse_output)
        self.output_button.grid(row=5, column=1, padx=10, pady=(0, 10))

        # Language Selection
        self.language_label = ctk.CTkLabel(self.main_frame, text="Select Language:")
        self.language_label.grid(row=6, column=0, padx=10, pady=(10, 0), sticky="w")

        self.language_menu = ctk.CTkOptionMenu(
            self.main_frame, 
            values=list(LANGUAGES.keys()), 
            variable=self.language,
            command=self.update_voice_options
        )
        self.language_menu.grid(row=7, column=0, padx=10, pady=(0, 10), sticky="ew")

        # Voice Selection
        self.voice_label = ctk.CTkLabel(self.main_frame, text="Select Voice:")
        self.voice_label.grid(row=8, column=0, padx=10, pady=(10, 0), sticky="w")

        self.voice_menu = ctk.CTkOptionMenu(self.main_frame, values=[], variable=self.voice_id)
        self.voice_menu.grid(row=9, column=0, padx=10, pady=(0, 10), sticky="ew")

        self.test_voice_button = ctk.CTkButton(self.main_frame, text="Test Voice", command=self.test_voice)
        self.test_voice_button.grid(row=9, column=1, padx=10, pady=(0, 10))

        # Convert Button
        self.convert_button = ctk.CTkButton(self.main_frame, text="Convert", command=self.convert)
        self.convert_button.grid(row=10, column=0, columnspan=2, padx=10, pady=20)

        # Play Button
        self.play_button = ctk.CTkButton(self.main_frame, text="Play", command=self.play_audio)
        self.play_button.grid(row=11, column=0, columnspan=2, padx=10, pady=10)

        # Stop Button
        self.stop_button = ctk.CTkButton(self.main_frame, text="Stop", command=self.stop_audio)
        self.stop_button.grid(row=12, column=0, columnspan=2, padx=10, pady=20)

        # Initialize voice options
        self.update_voice_options()

    def play_audio(self):
        output_file = self.output_path.get()
        if not output_file:
            messagebox.showerror("Error", "Please select an output file first.")
            return
        
        if not os.path.exists(output_file):
            messagebox.showerror("Error", "The output file does not exist. Please convert a PDF first.")
            return

        try:
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.play()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to play audio: {str(e)}")

    def stop_audio(self):
        output_file = self.output_path.get()
        if not output_file:
            messagebox.showerror("Error", "Please select an output file first.")
            return
        
        if not os.path.exists(output_file):
            messagebox.showerror("Error", "The output file does not exist. Please convert a PDF first.")
            return

        try:
            pygame.mixer.music.load(output_file)
            pygame.mixer.music.stop()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop audio: {str(e)}")

    def update_voice_options(self, *args):
        selected_language = self.language.get()
        voices = []
        if self.voice_capabilities:
            voices = [v for v, data in self.voice_capabilities.items() if data['language'] == selected_language]
        
        if voices:
            self.voice_menu.configure(values=voices)
            self.voice_id.set(voices[0])
        else:
            self.voice_menu.configure(values=["No voices available"])
            self.voice_id.set("")

    def browse_pdf(self):
        filename = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        self.pdf_path.set(filename)

    def browse_output(self):
        filename = filedialog.asksaveasfilename(defaultextension=".mp3", filetypes=[("MP3 files", "*.mp3")])
        self.output_path.set(filename)

    def test_voice(self):
        voice_id = self.voice_id.get()
        if not voice_id:
            messagebox.showerror("Error", "Please select a voice first.")
            return

        selected_language = self.language.get()
        test_text = TEST_TEXTS[selected_language]

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            try:
                text_to_speech(test_text, temp_file.name, voice_id, selected_language)
                os.system(f"xdg-open {temp_file.name}")  # This will open the default audio player
            except Exception as e:
                messagebox.showerror("Error", f"Failed to test voice: {str(e)}")
            finally:
                # Schedule file deletion after a delay to allow playing
                self.after(10000, lambda: os.unlink(temp_file.name))

    def convert(self):
        pdf_path = self.pdf_path.get()
        output_file = self.output_path.get()
        voice_id = self.voice_id.get()
        selected_language = self.language.get()

        if not pdf_path or not output_file:
            messagebox.showerror("Error", "Please select both input PDF and output file.")
            return

        try:
            # Get page range
            start_page = int(self.start_page_entry.get()) if self.start_page_entry.get() else None
            end_page = int(self.end_page_entry.get()) if self.end_page_entry.get() else None

            # Extract text from PDF
            text = extract_text_from_pdf(pdf_path, start_page, end_page)

            # Verify language and voice selection
            if selected_language not in LANGUAGES:
                raise ValueError(f"Invalid language selected: {selected_language}")
            
            language_code = LANGUAGES[selected_language]
            
            if voice_id not in self.voice_capabilities or self.voice_capabilities[voice_id]['language'] != selected_language:
                raise ValueError(f"Invalid voice selected for {selected_language}: {voice_id}")

            # Pre-process text based on selected language
            if language_code == 'pt-BR':
                processed_text = preprocess_text_pt_br(text)
            elif language_code == 'en-US':
                processed_text = preprocess_text_en_us_extended(text)
            else:
                raise ValueError(f"Unsupported language code: {language_code}")

            # Convert text to speech
            text_to_speech(processed_text, output_file, voice_id, language_code)
            
            messagebox.showinfo("Success", "Conversion completed successfully!")
            
            # Update usage tracker
            self.usage_tracker.add_entry(len(processed_text), voice_id)
            self.refresh_log()
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {str(e)}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
