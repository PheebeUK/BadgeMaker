# BadgeMaker

A tool for creating 3D printed badges with PDF layouts for printing. Automatically determines badge dimensions from STL files and generates appropriate PDF layouts with registration marks.

## Installation prequisites

1. **Create Virtual Environment**:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```
Remember that you need to activate 

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Basic Commands

```bash
# Use default badge shape
python badgemaker.py names.csv

# Use custom STL file
python badgemaker.py names.csv badge.stl

# With configuration file
python badgemaker.py names.csv --config config.json

# With custom output prefix
python badgemaker.py names.csv --prefix "event_"
```

### Command Line Options

- `csv_file`: CSV file containing badge text data (required) - see below
- `stl_file`: Badge STL file to use as template (optional, uses default badge shape if not provided)
- `--config, -c`: Configuration JSON file (optional)
- `--prefix, -p`: Output file prefix (optional, defaults to "badge_")

## Workflow

1. **Prepare CSV file** with badge text data (see CSV Format below)
2. **Optionally create config.json** for custom fonts and styling
3. **Run the tool** with your CSV file to get the PDF/STL files
4. **Print the PDF** on laser safe acetate sheet using a laser printer (dye sub might work too) - make sure the sheet is printed at 100%, and not scaled or adjusted to fit the page width.
6. **3D print** the registration marks, without skirt or brims - the top ones are to align with.
7. **Prepare and place acetate** sheet. Put a small amount of water in the center of your bed, and then place the sheet so the holes in the sheet sit over the registration knobs. Squeeze the water out with an absorbant cloth. The water helps with the heat transfer and holding the sheet in position close to the bed. Use low profile magnets or tape the sides down to prevent the sheet being lifted during the print.
8. **3D print** the crosshair stl file. It should sit over the crosshairs on the acetate. If it's out, now is your time to adjust things to get the position close to spot on. You might need to print the crosshair more than once to get alignment right.
9. **3D print** the badges on top of the acetate sheet. Remember that you may need to set a Z-offset in your slicer/printer (see below). The heat of filament will transfer the toner. You may have to adjust settings to prevent the toner from moving too much
10. **Attach** your preferred mount to the back of each badge

### Other options

Once you've positioned your acetate sheet, and printed the crosshair, you can use the resulting measurements to decide how to adjust. You can do this in your slicer software so that you compensate for where the sheet is positioned. Depending on your printer and bed this might be an easier alternative to trying to reposition your acetate on the bed.


### Z offset

When you put an acetate sheet on the bed of your 3D printer, it may affect the Z offset, as there's now something raising the print surface. While technically a 120micron sheet should be about 0.12mm, I found that less worked better. For example, 0.8mm worked better with a thin first layer (0.12mm) with a 0.4mm nozzle set to a 0.4mm line

If your printer has a auto bed levelling probe that makes contact with the surface (such as BL Touch, 3D Touch, CR Touch) then it will compensate for the additional height, and you don't need to adjust anything at all.

If you have a non-contact probe (Inductive or Capactive for example) you probably do need to configure your slicer/printer appropriately. 

If you manually level your bed, then you will have to configure your slicer/printer appropriately.

## Things Print In The Wrong Place

Even with careful alignment, badges might not print exactly where you expect them on the acetate sheet. This can happen due to printer calibration, sheet positioning, or the way your specific printer handles the acetate material.

### PDF Offsets

The `config.json` file includes a `pdf_offsets` section that allows you to fine-tune badge positioning on the PDF without affecting the 3D printed layout:

```json
"pdf_offsets": {
    "x_offset": 1.0,
    "y_offset": -16.0
}
```

- **X offset**: Moves badges left (negative) or right (positive) on the PDF by the specified amount in mm
- **Y offset**: Moves badges down (negative) or up (positive) on the PDF by the specified amount in mm

These offsets only affect the PDF output - the STL files remain unchanged, so you can align your 3D printed badges with the acetate sheet.

### When to Use Offsets

- **Laser printer calibration issues**: If your printer consistently prints badges too far left/right or up/down, because it probably will. 
- **Acetate sheet positioning**: If you need to compensate for how you position the sheet on your print bed
- **Fine-tuning alignment**: Small adjustments to get badges as close to centered on the acetate as you can

Start with small offset values (1-2mm) and adjust based on your test prints. Remember that positive X offset moves right, positive Y offset moves up on the PDF. 

## CSV Format

Create a CSV file with columns for each line of text:

```csv
line1,line2,line3
John,(He/Him),Repairer
Jane,(She/Her),Organiser
```

- `line1` is required, `line2` and `line3` are optional
- Each row creates one badge

## Configuration JSON

The `config.json` file controls fonts, styling, and appearance:

```json
{
    "fonts": {
        "line1": {
            "font_name": "arial.ttf",
            "font_size": 18,
            "y_position": 8
        },
        "line2": {
            "font_name": "times.ttf",
            "font_size": 14,
            "y_position": 15
        },
        "line3": {
            "font_name": "cour.ttf",
            "font_size": 12,
            "y_position": 22
        }
    },
    "badge_options": {
        "draw_border": false,
        "border_radius": 2.5,
        "background_image": "sample_background.png",
        "background_opacity": 1.0,
        "background_scale": 1.0
    }
}
```

### Font Settings
- `font_name`: Font file (use .ttf extension)
- `font_size`: Font size in points
- `y_position`: Vertical position in mm from top of badge

### Badge Options
- `draw_border`: Enable/disable rounded rectangle borders
- `border_radius`: Border corner radius in mm
- `background_image`: Path to background image file (PNG/JPG supported) or `null` for white background
- `background_opacity`: Background image opacity (0.0 to 1.0, where 1.0 is fully opaque)
- `background_scale`: Background image scale factor (1.0 = full size/edge-to-edge, 0.8 = 80% size with borders, 0.5 = 50% size, etc.)

## Known Issues
- The badge offset isn't right. 
- You can only create one page of badges at a time

## Other ideas
- Adding an "outline" mode that only 3D prints the very outside of the badge to help resolve positioning problems.