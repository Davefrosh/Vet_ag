import base64
import tempfile
import os
import time
import cv2
from io import BytesIO
from PIL import Image
from openai import OpenAI
import assemblyai as aai


class MediaProcessor:
    def __init__(self, openai_api_key, assemblyai_api_key=None):
        self.client = OpenAI(api_key=openai_api_key)
        if assemblyai_api_key:
            aai.settings.api_key = assemblyai_api_key
            self.transcriber = aai.Transcriber()
        else:
            self.transcriber = None
    
    def _optimize_image(self, image_file, max_dimension=2048, quality=85):
        image_file.seek(0)
        img = Image.open(image_file)
        
        if img.mode in ('RGBA', 'P', 'LA'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        width, height = img.size
        if width > max_dimension or height > max_dimension:
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            img = img.resize((new_width, new_height), Image.LANCZOS)
        
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=quality, optimize=True)
        buffer.seek(0)
        return base64.b64encode(buffer.read()).decode('utf-8')
    
    def analyze_image(self, image_file):
        image_data = self._optimize_image(image_file)
        
        prompt = """
        CRITICAL FORENSIC ANALYSIS:
        Analyze this advertisement image to identify the SPECIFIC PRODUCT being advertised.
        
        Provide a structured report with:
        1. BRAND IDENTIFICATION: Exact brand names, logos, and product names visible.
        2. PRODUCT VISIBILITY: Describe the packaging, colors, and placement.
        3. TEXT ANALYSIS: Transcribe all text overlays, captions, and disclaimers exactly.
        4. VISUAL ELEMENTS: Describe the setting, people (e.g. influencers), and their actions.
        """
        
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
        ]
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": content}],
                max_tokens=1000,
                temperature=0
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"Visual analysis failed: {str(e)}"

    def analyze_visuals(self, frames):
        total_frames = len(frames)
        if total_frames > 4:
            step = total_frames // 4
            selected_frames = frames[::step][:4]
        else:
            selected_frames = frames

        prompt = """
        CRITICAL FORENSIC ANALYSIS:
        Analyze these video frames to identify the SPECIFIC PRODUCT being advertised.
        
        Provide a structured report with:
        1. BRAND IDENTIFICATION: Exact brand names, logos, and product names visible (e.g., "Honeywell Semolina", "Indomie"). 
        2. PRODUCT VISIBILITY: Describe the packaging, colors, and where it appears.
        3. ON-SCREEN TEXT: Transcribe all text overlays, captions, and disclaimers exactly.
        4. SCENE & ACTION: Describe who is in the video (e.g., "Celebrity Influencer") and what they are doing with the product.
        
        If you see a product but can't read the text perfectly, describe its visual features in detail.
        """

        content = [{"type": "text", "text": prompt}]
        
        for frame in selected_frames:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{frame}"}
            })
            
        max_retries = 3
        retry_delay = 5
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": content}],
                    max_tokens=1000,
                    temperature=0
                )
                return response.choices[0].message.content
            except Exception as e:
                if "rate_limit_exceeded" in str(e) or "429" in str(e):
                    if attempt < max_retries - 1:
                        sleep_time = retry_delay * (2 ** attempt)
                        time.sleep(sleep_time)
                        continue
                return "Visual analysis could not be completed due to technical issues."

    def _transcribe_with_assemblyai(self, audio_path):
        if not self.transcriber:
            raise Exception("AssemblyAI is not configured. Please provide an API key.")
        
        try:
            transcript = self.transcriber.transcribe(audio_path)
            
            if transcript.status == aai.TranscriptStatus.error:
                raise Exception(f"Transcription failed: {transcript.error}")
            
            return transcript.text or "[No speech detected in audio]"
            
        except Exception as e:
            raise Exception(f"Audio transcription failed: {str(e)}")
    
    def process_audio(self, audio_file):
        audio_file.seek(0)
        file_extension = audio_file.name.split('.')[-1].lower()
        tmp_path = None
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as tmp_file:
                tmp_path = tmp_file.name
                chunk_size = 8 * 1024 * 1024
                while True:
                    chunk = audio_file.read(chunk_size)
                    if not chunk:
                        break
                    tmp_file.write(chunk)
            
            transcript = self._transcribe_with_assemblyai(tmp_path)
            return transcript
            
        except Exception as e:
            error_msg = str(e)
            raise Exception(f"Vetting analysis wasn't carried out: {error_msg}")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except PermissionError:
                    pass
    
    def process_video(self, video_file):
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
                tmp_path = tmp_file.name
                video_file.seek(0)
                chunk_size = 8 * 1024 * 1024
                while True:
                    chunk = video_file.read(chunk_size)
                    if not chunk:
                        break
                    tmp_file.write(chunk)
            
            frames = self.extract_frames(tmp_path)
            audio_transcript = self.extract_and_transcribe_audio(tmp_path)
            visual_analysis = self.analyze_visuals(frames)
            
            return frames, audio_transcript, visual_analysis
        finally:
            time.sleep(0.5)
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except PermissionError:
                    pass
    
    def extract_frames(self, video_path, max_frames=20):
        frames_base64 = []
        video = cv2.VideoCapture(video_path)
        
        if not video.isOpened():
            raise Exception("Failed to open video file")
        
        total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = video.get(cv2.CAP_PROP_FPS)
        
        if total_frames == 0 or fps == 0:
            raise Exception("Could not determine video properties")
        
        duration_seconds = total_frames / fps
        
        if duration_seconds <= 10:
            interval_seconds = 1
        elif duration_seconds <= 30:
            interval_seconds = 2
        elif duration_seconds <= 60:
            interval_seconds = 3
        else:
            interval_seconds = duration_seconds / max_frames
        
        frame_interval = int(fps * interval_seconds)
        frame_count = 0
        
        while True:
            ret, frame = video.read()
            if not ret:
                break
                
            if frame_count % frame_interval == 0:
                height, width = frame.shape[:2]
                max_dimension = 1024
                if width > max_dimension or height > max_dimension:
                    scale = max_dimension / max(width, height)
                    new_width = int(width * scale)
                    new_height = int(height * scale)
                    frame = cv2.resize(frame, (new_width, new_height))

                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
                frames_base64.append(frame_base64)
                
                if len(frames_base64) >= max_frames:
                    break
            
            frame_count += 1
        
        video.release()
        
        if not frames_base64:
            raise Exception("No frames could be extracted from video")
            
        return frames_base64
    
    def extract_and_transcribe_audio(self, video_path):
        # Lazy import with version compatibility (moviepy 1.x vs 2.x)
        try:
            from moviepy import VideoFileClip
            moviepy_v2 = True
        except ImportError:
            from moviepy.editor import VideoFileClip
            moviepy_v2 = False
        
        audio_path = None
        video = None
        try:
            with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as audio_file:
                audio_path = audio_file.name
            
            video = VideoFileClip(video_path)
            
            if video.audio is None:
                video.close()
                return "[No audio track found in video]"
            
            # moviepy 2.x removed verbose parameter
            if moviepy_v2:
                video.audio.write_audiofile(audio_path, logger=None)
            else:
                video.audio.write_audiofile(audio_path, logger=None, verbose=False)
            video.close()
            video = None
            
            time.sleep(0.3)
            transcript = self._transcribe_with_assemblyai(audio_path)
            return transcript
            
        except Exception as e:
            return f"[Audio extraction failed: {str(e)}]"
        finally:
            if video is not None:
                try:
                    video.close()
                except:
                    pass
            time.sleep(0.3)
            if audio_path and os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                except PermissionError:
                    pass
