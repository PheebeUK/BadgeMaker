#!/usr/bin/env python3

import os
import sys
import csv
import json
import argparse
from pathlib import Path

# Import our custom classes
from meshbuilder import MeshBuilder
from pdfgenerator import PDFGenerator


class BadgeMaker:
    """Main coordinator class for badge creation process"""
    
    def __init__(self, config_file=None):
        """Initialize BadgeMaker with configuration"""
        self.config = self._load_config(config_file)
        self.mesh_builder = None
        self.pdf_generator = None
        # Load offsets from config
        self.x_offset = self.config.get('pdf_offsets', {}).get('x_offset', 0.0)
        self.y_offset = self.config.get('pdf_offsets', {}).get('y_offset', 0.0)
        
        # Print offset values for debugging
        print(f"Using PDF offsets: X={self.x_offset:.2f}mm, Y={self.y_offset:.2f}mm")
        
    def _load_config(self, config_file):
        """Load configuration from JSON file or use defaults"""
        default_config = {
            "fonts": {
                "line1": {"font_name": "arial.ttf", "font_size": 16, "y_position": 8},
                "line2": {"font_name": "arial.ttf", "font_size": 14, "y_position": 15},
                "line3": {"font_name": "arial.ttf", "font_size": 12, "y_position": 22}
            },
            "badge_options": {
                "draw_border": True,
                "border_radius": 2.0,
                "background_image": None
            },
            "pdf_offsets": {
                "x_offset": 0.0,
                "y_offset": 0.0
            }
        }
        
        if config_file and os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    user_config = json.load(f)
                # Merge user config with defaults
                for section in user_config:
                    if section in default_config:
                        default_config[section].update(user_config[section])
                    else:
                        default_config[section] = user_config[section]
            except Exception as e:
                print(f"Warning: Could not load config file {config_file}: {e}")
                print("Using default configuration")
        
        return default_config
    
    def load_badge_stl(self, stl_file=None):
        """Load badge STL file or create default badge and determine dimensions"""
        self.mesh_builder = MeshBuilder()
        
        if stl_file:
            if not os.path.exists(stl_file):
                raise FileNotFoundError(f"Badge STL file not found: {stl_file}")
            
            print(f"Loading badge STL: {stl_file}")
            self.mesh_builder.load_badge_stl(stl_file)
        else:
            print("No STL file provided, creating default badge shape")
            self.mesh_builder.create_badge_mesh()
        
        # Get badge dimensions for PDF generation
        mesh_size = self.mesh_builder.get_mesh_size()
        print(f"Badge dimensions: {mesh_size['width']:.1f}mm × {mesh_size['height']:.1f}mm × {mesh_size['depth']:.1f}mm")
        
        # Initialize PDF generator with correct badge dimensions
        self.pdf_generator = PDFGenerator(
            badge_width=mesh_size['width'],
            badge_height=mesh_size['height'],
            x_offset=self.x_offset,
            y_offset=self.y_offset
        )
        
        return mesh_size
    
    def read_csv_data(self, csv_file):
        """Read badge text data from CSV file"""
        if not os.path.exists(csv_file):
            raise FileNotFoundError(f"CSV file not found: {csv_file}")
        
        badges_data = []
        
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row_num, row in enumerate(reader, 1):
                # Validate required columns
                if 'line1' not in row:
                    print(f"Warning: Row {row_num} missing 'line1' column, skipping")
                    continue
                
                text_config = []
                for line_num in range(1, 4):
                    line_key = f'line{line_num}'
                    if line_key in row and row[line_key].strip():
                        text_config.append({
                            'text': row[line_key].strip(),
                            'font_name': self.config['fonts'][line_key]['font_name'],
                            'font_size': self.config['fonts'][line_key]['font_size'],
                            'y_position': self.config['fonts'][line_key]['y_position']
                        })
                
                if text_config:
                    background_image = self.config['badge_options'].get('background_image')
                    background_opacity = self.config['badge_options'].get('background_opacity', 1.0)
                    
                    badges_data.append({
                        'text_config': text_config,
                        'draw_border': self.config['badge_options']['draw_border'],
                        'border_radius': self.config['badge_options']['border_radius'],
                        'background_image': background_image,
                        'background_opacity': background_opacity
                    })
        return badges_data
    
    def create_registration_stl(self, output_file):
        """Create STL with L-shaped registration stops"""
        if not self.mesh_builder:
            raise RuntimeError("No badge STL loaded. Call load_badge_stl() first.")
        
        print(f"Creating STL with L-shaped registration stops: {output_file}")
        # Use the new L-shaped stop method with default dimensions
        self.mesh_builder.create_l_stop_registration_stl(output_file, arm_length=20.0, arm_width=5.0, height=2.0)
    
    def create_layout_stl(self, output_file, badge_centers):
        """Create STL with badge layout positioned according to PDF layout"""
        if not self.mesh_builder:
            raise RuntimeError("No badge STL loaded. Call load_badge_stl() first.")
        
        print(f"Creating STL with badge layout: {output_file}")
        
        # Create a grid of badges positioned according to the PDF layout
        self.mesh_builder.create_badge_layout_stl(output_file, badge_centers, self.pdf_generator)
    
    def create_pdf(self, badges_data, output_file):
        """Create PDF with badge images"""
        if not self.pdf_generator:
            raise RuntimeError("No PDF generator initialized. Call load_badge_stl() first.")
        
        print(f"Creating PDF with {len(badges_data)} badges: {output_file}")
        badge_centers = self.pdf_generator.create_badge_page(output_file, badges_data)
        
        # Store badge centers for use in STL layout
        self.badge_centers = badge_centers
        return badge_centers
    
    def process_badges(self, stl_file=None, csv_file=None, output_prefix=None):
        """Main processing function - orchestrates the entire badge creation process"""
        try:
            # Store CSV file path for later use in layout creation
            self.csv_file = csv_file
            
            # Load badge STL or create default badge and get dimensions
            mesh_size = self.load_badge_stl(stl_file)
            
            # Read badge data from CSV
            badges_data = self.read_csv_data(csv_file)
            
            if not badges_data:
                print("No valid badge data found in CSV")
                return
            
            # Set output prefix (default to "badge_" if not provided)
            if output_prefix is None:
                output_prefix = "badge_"
            
            # Always create all three output files
            reg_stl_file = f"{output_prefix}registration.stl"
            self.create_registration_stl(reg_stl_file)
            
            pdf_file = f"{output_prefix}badges.pdf"
            badge_centers = self.create_pdf(badges_data, pdf_file)
            
            # Now create layout STL with the badge centers from PDF
            layout_stl_file = f"{output_prefix}layout.stl"
            self.create_layout_stl(layout_stl_file, badge_centers)
            
        except Exception as e:
            print(f"Error during badge creation: {e}")
            raise


def main():
    """Main entry point with command line argument parsing"""
    parser = argparse.ArgumentParser(
        description="Create 3D printed badges with PDF layouts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
 Examples:
   python badgemaker.py names.csv                    # Use default badge shape
   python badgemaker.py names.csv badge.stl         # Use custom STL file
   python badgemaker.py names.csv --config my_config.json
   python badgemaker.py names.csv badge.stl --prefix "event_"
         """
    )
    
    parser.add_argument('csv_file', help='CSV file containing badge text data')
    parser.add_argument('stl_file', nargs='?', help='Badge STL file to use as template (optional, uses default if not provided)')
    parser.add_argument('--config', '-c', help='Configuration JSON file')
    parser.add_argument('--prefix', '-p', help='Output file prefix')
    
    args = parser.parse_args()
    
    try:
        # Create BadgeMaker instance
        badge_maker = BadgeMaker(config_file=args.config)
        
        # Process badges
        badge_maker.process_badges(
            stl_file=args.stl_file,
            csv_file=args.csv_file,
            output_prefix=args.prefix
        )
        
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
