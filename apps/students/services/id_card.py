from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from django.conf import settings
from django.utils import timezone
import os

class IDCardGenerator:
    """Service to generate student ID Card."""

    def __init__(self, student):
        self.student = student
        # Standard ID Card size: 85.6mm x 54mm.
        # At 300 DPI: ~1011 x 638 pixels.
        self.width = 1011
        self.height = 638
        self.background_color = (255, 255, 255)
        # Université Attawoune colors (assuming Blue/Gold theme)
        self.primary_color = (29, 78, 216) # Blue-700
        self.accent_color = (234, 179, 8) # Yellow-500
        self.text_color = (31, 41, 55) # Gray-800
        
    def generate(self) -> BytesIO:
        """Generate ID Card image and return bytes."""
        # Create base image
        img = Image.new('RGB', (self.width, self.height), self.background_color)
        draw = ImageDraw.Draw(img)
        
        # Draw Background Design
        self._draw_background(draw)
        
        # Load fonts (fallback to default if ttf not found)
        # In a real deployed app, we should ship TTF fonts.
        # Using default limited font for safety, but trying to load standard system fonts if possible
        try:
            # Try to use a nice font if available (e.g., Arial on generic system)
            # Or use Django static file if we had one.
            # Using default PIL font for now to guarantee no crash, but scaling it is hard.
            # PIL default font is tinybitmap.
            # We MUST try to load a font.
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60, index=0)
            subtitle_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 32, index=0)
            label_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28, index=0)
            value_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36, index=1) # Boldish?
        except IOError:
             # Fallback logic for Linux/Container (e.g. DejaVuSans)
            try:
                title_font = ImageFont.truetype("DejaVuSans.ttf", 60)
                subtitle_font = ImageFont.truetype("DejaVuSans.ttf", 32)
                label_font = ImageFont.truetype("DejaVuSans.ttf", 28)
                value_font = ImageFont.truetype("DejaVuSans.ttf", 36)
            except IOError:
                # Absolute fallback
                title_font = ImageFont.load_default()
                subtitle_font = ImageFont.load_default()
                label_font = ImageFont.load_default()
                value_font = ImageFont.load_default()
        
        # Header
        draw.rectangle([(0, 0), (self.width, 140)], fill=self.primary_color)
        draw.text((self.width // 2, 50), "UNIVERSITÉ ATTAWOUNE", font=title_font, fill=(255, 255, 255), anchor="mm")
        draw.text((self.width // 2, 100), "CARTE D'ÉTUDIANT", font=subtitle_font, fill=(255, 255, 255), anchor="mm")
        
        # Footer
        draw.rectangle([(0, self.height - 60), (self.width, self.height)], fill=self.primary_color)
        year = timezone.now().year
        # Or use enrollment academic year if possible. assuming current year validity.
        validity = f"Année Académique: {year}-{year+1}"
        draw.text((self.width // 2, self.height - 30), validity, font=subtitle_font, fill=(255, 255, 255), anchor="mm")

        # Photo Area (Left side)
        photo_x, photo_y = 50, 180
        photo_w, photo_h = 280, 350
        
        # Draw placeholder or photo
        if self.student.photo:
            try:
                photo_path = self.student.photo.path
                photo_img = Image.open(photo_path)
                # Resize and Crop to fill box
                photo_img = self._resize_and_crop(photo_img, (photo_w, photo_h))
                img.paste(photo_img, (photo_x, photo_y))
            except Exception as e:
                print(f"Error loading photo: {e}")
                self._draw_photo_placeholder(draw, photo_x, photo_y, photo_w, photo_h)
        else:
            self._draw_photo_placeholder(draw, photo_x, photo_y, photo_w, photo_h)
            
        # Draw Border around photo
        draw.rectangle([(photo_x, photo_y), (photo_x + photo_w, photo_y + photo_h)], outline=self.primary_color, width=3)
        
        # Text Details Area (Right side)
        text_x = 380
        start_y = 200
        line_height = 80
        
        # Name
        draw.text((text_x, start_y), "Nom & Prénom:", font=label_font, fill=self.text_color)
        draw.text((text_x, start_y + 35), self.student.user.get_full_name().upper(), font=value_font, fill=self.primary_color)
        
        # Matricule
        draw.text((text_x, start_y + line_height), "Matricule:", font=label_font, fill=self.text_color)
        draw.text((text_x, start_y + line_height + 35), self.student.student_id, font=value_font, fill=self.text_color)
        
        # Program
        draw.text((text_x, start_y + line_height * 2), "Filière:", font=label_font, fill=self.text_color)
        draw.text((text_x, start_y + line_height * 2 + 35), self.student.program.name, font=value_font, fill=self.text_color)
        
        # Level
        draw.text((text_x, start_y + line_height * 3), "Niveau:", font=label_font, fill=self.text_color)
        if self.student.current_level:
            draw.text((text_x, start_y + line_height * 3 + 35), self.student.current_level.get_name_display(), font=value_font, fill=self.text_color)
            
        # Output
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer

    def _draw_background(self, draw):
        """Draw decorative background elements."""
        # Simple curve or accent
        draw.rectangle([(0, 140), (self.width, 150)], fill=self.accent_color)
        
    def _draw_photo_placeholder(self, draw, x, y, w, h):
        """Draw a placeholder if no photo."""
        draw.rectangle([(x, y), (x + w, y + h)], fill=(229, 231, 235)) # Gray-200
        draw.text((x + w//2, y + h//2), "NO PHOTO", fill=(156, 163, 175), anchor="mm")

    def _resize_and_crop(self, img, size):
        """Resize and central crop image to fit size."""
        img_ratio = img.width / img.height
        target_ratio = size[0] / size[1]
        
        if target_ratio > img_ratio:
            # Target is wider, resize by width
            scale = size[0] / img.width
        else:
            scale = size[1] / img.height
            
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.Resampling.LANCZOS)
        
        # Center crop
        left = (img.width - size[0]) / 2
        top = (img.height - size[1]) / 2
        right = (img.width + size[0]) / 2
        bottom = (img.height + size[1]) / 2
        
        return img.crop((left, top, right, bottom))
