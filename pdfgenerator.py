"""
PDFGenerator class for creating PDF documents using reportlab.
"""

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import black, white
from PIL import Image, ImageDraw, ImageFont
import io
import os


class PDFGenerator:
    """
    A class for generating PDF documents using reportlab.
    """
    
    def __init__(self, badge_width=75.0, badge_height=30.0, x_offset=0.0, y_offset=0.0):
        """
        Initialize the PDFGenerator.
        
        Args:
            badge_width (float): Width of badges in mm
            badge_height (float): Height of badges in mm
            x_offset (float): X-axis offset for badge positioning in mm
            y_offset (float): Y-axis offset for badge positioning in mm
        """
        # A4 page dimensions in mm
        self.page_width = 210.0
        self.page_height = 297.0
        
        # Badge dimensions in mm
        self.badge_width = badge_width
        self.badge_height = badge_height

        # PDF offset values for laser printer compensation
        self.x_offset = x_offset
        self.y_offset = y_offset
        
        # Track background image warnings to avoid duplicates
        self.background_warnings_shown = set()
        
        # Column positions with proper spacing to avoid overlap
        # Leave margins on left and right, and ensure badges don't overlap
        left_margin = 20.0  # mm from left edge
        right_margin = 20.0  # mm from right edge
        available_width = self.page_width - left_margin - right_margin
        gap_between_columns = 15.0  # mm gap between columns
        
        # Calculate column positions to center the badges and avoid overlap
        total_badges_width = (self.badge_width * 2) + gap_between_columns
        start_x = left_margin + (available_width - total_badges_width) / 2
        
        self.column1_x = start_x + (self.badge_width / 2)
        self.column2_x = start_x + self.badge_width + gap_between_columns + (self.badge_width / 2)
        
        # Start position from top of page
        self.start_y = self.page_height - 20  # 20mm margin from top
        
        # Default font settings
        self.default_font = "arial.ttf"  # Use .ttf extension for Windows
        self.default_font_size = 12
        self.text_line_height = 8  # mm between text lines
        
        # Registration mark settings
        self.registration_mark_size = 5.0  # mm
        lknobx = (self.page_width / 2) - (self.page_width / 3)
        rknobx = (self.page_width / 2) + (self.page_width / 3)
       
        self.registration_mark_positions = [
            (self.page_width / 2, self.page_height - 10),  # Top center
            (lknobx, 10),                     # Bottom left
            (rknobx, 10)                # Bottom right
        ]

    def create_badge_image(self, text_config, background_image_path=None, draw_border=False, border_radius=2.0, background_opacity=1.0):
        """
        Create a badge image with text and optional background.
        
        Args:
            text_config (list): List of text configuration dictionaries for each line.
                               Each dict can contain:
                               - 'text': The text to display
                               - 'y_position': Vertical position in mm from top of badge
                               - 'font_name': Font name (optional, uses default if not specified)
                               - 'font_size': Font size in points (optional, uses default if not specified)
            background_image_path (str, optional): Path to background image
            draw_border (bool): Whether to draw a rounded rectangle border around the badge
            border_radius (float): Border radius in mm
            background_opacity (float): Opacity of background image (0.0 to 1.0)
            
        Returns:
            PIL.Image: The created badge image
        """
        # Use higher DPI for quality while maintaining correct font sizes
        # We'll scale the font sizes proportionally to the DPI increase
        dpi = 300  # High quality rendering
        mm_to_pixels = dpi / 25.4
        
        img_width = int(self.badge_width * mm_to_pixels)
        img_height = int(self.badge_height * mm_to_pixels)
        
        # Create base image
        img = Image.new('RGB', (img_width, img_height), (255, 255, 255))
        
        # Add background image if provided
        if background_image_path and os.path.exists(background_image_path):
            try:
                bg_img = Image.open(background_image_path)
                
                # Check if background image dimensions match badge dimensions
                bg_width, bg_height = bg_img.size
                optimal_width = int(self.badge_width * mm_to_pixels)
                optimal_height = int(self.badge_height * mm_to_pixels)
                
                # Only show size mismatch warning once per background image
                if (bg_width != optimal_width or bg_height != optimal_height) and background_image_path not in self.background_warnings_shown:
                    print(f"Warning: Background image size mismatch!")
                    print(f"  Current: {bg_width} × {bg_height} pixels")
                    print(f"  Optimal: {optimal_width} × {optimal_height} pixels")
                    print(f"  Optimal size in mm: {self.badge_width:.1f} × {self.badge_height:.1f}mm")
                    print(f"  For best results, resize your background image to {optimal_width} × {optimal_height} pixels")
                    self.background_warnings_shown.add(background_image_path)
                
                # Resize background image to fit badge
                bg_img = bg_img.resize((img_width, img_height))
                
                # Apply opacity if less than 1.0
                if background_opacity < 1.0:
                    # Create a copy of the background image
                    bg_img_with_alpha = bg_img.copy()
                    
                    # Convert to RGBA if not already
                    if bg_img_with_alpha.mode != 'RGBA':
                        bg_img_with_alpha = bg_img_with_alpha.convert('RGBA')
                    
                    # Apply opacity
                    alpha_data = bg_img_with_alpha.getdata()
                    new_alpha_data = []
                    for pixel in alpha_data:
                        r, g, b, a = pixel
                        new_alpha = int(a * background_opacity)
                        new_alpha_data.append((r, g, b, new_alpha))
                    
                    bg_img_with_alpha.putdata(new_alpha_data)
                    
                    # Composite the background image onto the base image
                    img = Image.alpha_composite(img.convert('RGBA'), bg_img_with_alpha).convert('RGB')
                else:
                    # No opacity, just paste the background image
                    img.paste(bg_img, (0, 0))
                    
            except Exception as e:
                print(f"Warning: Could not load background image '{background_image_path}': {e}")
                print("Using white background instead")
        
        draw = ImageDraw.Draw(img)
        
        # Draw each text line with individual settings
        for line_config in text_config:
            text = line_config.get('text', '')
            if not text:
                continue
                
            # Get individual line settings or use defaults
            font_name = line_config.get('font_name', self.default_font)
            font_size_points = line_config.get('font_size', self.default_font_size)
            y_position_mm = line_config.get('y_position', self.badge_height / 2)  # Default to center
            
            # Scale font size proportionally to DPI: points * (dpi/72)
            # This maintains correct font sizes while using high DPI for quality
            font_size_pixels = int(font_size_points * (dpi / 72))
            
            # Try to load font, fall back to default if not available
            try:
                font = ImageFont.truetype(font_name, font_size_pixels)
            except Exception as e:
                font = ImageFont.load_default()
            
            # Convert y position to pixels
            y_pos = int(y_position_mm * mm_to_pixels)
            
            # Center text horizontally
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            x_pos = (img_width - text_width) // 2
            
            # Draw the text
            draw.text((x_pos, y_pos), text, fill=(0, 0, 0), font=font)
        
        # Draw border if requested
        if draw_border:
            border_radius_pixels = int(border_radius * mm_to_pixels)
            # Draw rounded rectangle border (2 pixels inside the image edges)
            padding = 2
            draw.rounded_rectangle(
                [padding, padding, img_width - 1 - padding, img_height - 1 - padding],
                radius=border_radius_pixels,
                fill=None,
                outline=(0, 0, 0),
                width=2
            )
        
        # Flip image horizontally for printing
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
        
        return img

    def add_badge_to_pdf(self, canvas_obj, badge_image, x, y):
        """
        Add a badge image to the PDF at the specified position.
        
        Args:
            canvas_obj: ReportLab canvas object
            badge_image (PIL.Image): Badge image to add
            x (float): X position in mm (left edge)
            y (float): Y position in mm (bottom edge)
            
        Returns:
            tuple: (center_x, center_y) in mm from page origin
        """
        # Convert badge image to bytes and save to temporary file
        img_buffer = io.BytesIO()
        badge_image.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        
        # Create a temporary file for reportlab
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_file.write(img_buffer.getvalue())
            tmp_filename = tmp_file.name
        
        try:
            # Add image to PDF
            canvas_obj.drawImage(tmp_filename, (x + self.x_offset) * mm, (y + self.y_offset) * mm, 
                               self.badge_width * mm, self.badge_height * mm)
        finally:
            # Clean up temporary file
            try:
                os.unlink(tmp_filename)
            except:
                pass
        
        # Calculate and return the center point of the badge on the page
        center_x = x + (self.badge_width / 2)
        center_y = y + (self.badge_height / 2)
        return (center_x, center_y)

    def add_registration_marks(self, canvas_obj):
        """
        Add registration marks to the PDF.
        
        Args:
            canvas_obj: ReportLab canvas object
        """
        canvas_obj.setFillColor(black)
        
        for x, y in self.registration_mark_positions:
            # Draw filled circle
            radius = self.registration_mark_size / 2
            canvas_obj.circle(x * mm, y * mm, radius * mm, fill=1)

    def create_badge_page(self, output_path, badges_data):
        """
        Create a PDF page with badges arranged in two columns.
        
        Args:
            output_path (str): Path to save the PDF
            badges_data (list): List of badge data dictionaries
        """
        c = canvas.Canvas(output_path, pagesize=A4)
        
        # Add registration marks
        self.add_registration_marks(c)
        
        # Calculate how many badges can fit on a single page
        # Leave margins: 20mm top, 30mm bottom = 50mm total margins
        available_height = self.page_height - 50  # mm
        max_rows = int((available_height + 10) / (self.badge_height + 10))  # +10 for gap
        max_badges = max_rows * 2
        
        # Limit badges to what fits on one page
        if len(badges_data) > max_badges:
            print(f"Warning: Only {max_badges} badges can fit on a single page for 3D printing.")
            print(f"  You provided {len(badges_data)} badges.")
            print(f"  Last badge that will fit: '{badges_data[max_badges-1].get('text_config', [{}])[0].get('text', 'Unknown')}'")
            print(f"  Badges {max_badges+1}-{len(badges_data)} will be skipped.")
            badges_data = badges_data[:max_badges]
        
        # Calculate total height for the badges we can fit
        rows_needed = (len(badges_data) + 1) // 2  # Round up for odd number of badges
        total_badges_height = 0
        if rows_needed > 0:
            total_badges_height = (rows_needed * self.badge_height) + ((rows_needed - 1) * 10)  # 10mm gap between rows
        
        # STLs tend to be centered on the bed, so we need to center the badges
        page_center_y = self.page_height / 2
        first_badge_center_y = page_center_y - (total_badges_height / 2)
        current_y = self.page_height - (first_badge_center_y + (self.badge_height / 2))
        

        
        badges_per_column = 0
        badge_centers = []  # Store center points of all badges
        
        for i, badge_data in enumerate(badges_data):
            # Determine column
            if i % 2 == 0:  # Even indices go in first column
                x = self.column1_x - (self.badge_width / 2)
                badges_per_column += 1
            else:  # Odd indices go in second column
                x = self.column2_x - (self.badge_width / 2)
            

            

            
            # Create badge image
            badge_img = self.create_badge_image(
                text_config=badge_data.get('text_config', []),
                background_image_path=badge_data.get('background_image'),
                draw_border=badge_data.get('draw_border', False),
                border_radius=badge_data.get('border_radius', 2.0),
                background_opacity=badge_data.get('background_opacity', 1.0)
            )
            
            # Add badge to PDF and get its center point
            center_point = self.add_badge_to_pdf(c, badge_img, x, current_y)
            badge_centers.append(center_point)
            
            # Move to next row if we've filled both columns
            if i % 2 == 1:  # After placing in second column
                old_y = current_y
                current_y -= (self.badge_height + 10)  # 10mm gap between rows
                

        
        c.save()
        

        
        return badge_centers

