"""
MeshBuilder class all the meshy things we have to do
"""

from typing import Optional, Tuple
import numpy as np
from PIL import Image, ImageDraw
import meshlib.mrmeshpy as mr
import tempfile
import os
import math


class MeshBuilder:
    """
    A class for doing mesh operations for making badges.
    
    This class provides methods to do useful things :)
    """
    
    def __init__(self):
        # Badge dimensions (in mm)
        self.badge_width: float = 75.0
        self.badge_height: float = 30.0
        self.badge_thickness: float = 3
        
        # Magnet recess dimensions (in mm)
        self.recess_width: float = 46.0
        self.recess_height: float = 14.5
        self.recess_depth: float = 0.6
        
        # Corner radius (in mm)
        self.corner_radius: float = 2.0

        # Registration knob dimensions (in mm)
        self.registration_mark_size: float = 5.0
        self.registration_knob_height: float = 2.0
        self.registration_knob_diameter: float = 4.5
        
        # Image resolution (pixels per mm)
        self.resolution: float = 10.0
        
        # Add border so we can do distancemaps properly
        self.img_width: int = int(self.badge_width * self.resolution) + 4
        self.img_height: int = int(self.badge_height * self.resolution) + 4

        # A4 page dimensions in mm
        self.page_width = 210.0  # mm
        self.page_height = 297.0  # mm
        self.page_margin = 10.0  # mm
        
        # Calculate available space for badges
        self.usable_width = self.page_width - (2 * self.page_margin)
        self.usable_height = self.page_height - (2 * self.page_margin)

        # Store meshes for future use
        self.badge_mesh: Optional[mr.Mesh] = None
        self.registration_mesh: Optional[mr.Mesh] = None
        

    def get_mesh_bounding_box_in_mm(self, mesh: mr.Mesh) -> Optional[dict]:
        """
        Get the physical size of the mesh bounding box in millimeters.
        
        Returns:
            Optional[dict]: Dictionary with 'width', 'height', 'depth' keys in mm,
                           or None if no mesh is loaded
        """

        # Get the bounding box of the mesh
        bbox = mesh.computeBoundingBox()
        
        # Extract dimensions
        min_point = bbox.min
        max_point = bbox.max
        
        # Calculate dimensions in mm
        width = max_point.x - min_point.x
        height = max_point.y - min_point.y
        depth = max_point.z - min_point.z
        
        return {
            'width': width,
            'height': height,
            'depth': depth
        }
    

    def get_mesh_size(self) -> Optional[dict]:
        """
        Get the physical size of the mesh bounding box in millimeters.
        
        Returns:
            Optional[dict]: Dictionary with 'width', 'height', 'depth' keys in mm,
                           or None if no mesh is loaded
        """
        if self.badge_mesh is None:
            print("No mesh loaded. Load a mesh first using load_mesh_from_file().")
            return None
        return self.get_mesh_bounding_box_in_mm(self.badge_mesh)

    def load_badge_stl(self, filename: str) -> Optional[mr.Mesh]:
        """
        Load a badge mesh from an STL file for later use
        
        Args:
            filename (str): Path to the STL file to load
            
        Returns:
            Optional[mr.Mesh]: The loaded mesh if successful, None if failed
        """
        try:
            # Check if file exists
            if not os.path.exists(filename):
                print(f"Error: STL file {filename} does not exist")
                return None
            
            # Check if it's an STL file
            if not filename.lower().endswith('.stl'):
                print(f"Error: {filename} is not an STL file")
                return None
            
            # Use MeshLib to load the STL mesh
            loaded_mesh = mr.loadMesh(filename)
            if loaded_mesh:
                self.badge_mesh = loaded_mesh
                # Store the original filename for later use in layout creation
                self.original_stl_file = filename
                print(f"Successfully loaded badge mesh from {filename}")
                return loaded_mesh
            else:
                print(f"Error: Failed to load mesh from {filename}")
                return None
                
        except Exception as e:
            print(f"Error loading badge STL from {filename}: {str(e)}")
            return None

    def create_badge_main_heightmap(self) -> Image.Image:
        """
        Create the main badge heightmap image with rounded corners.
        
        Returns:
            Image.Image: A binary PIL Image
        """
        img = Image.new('1', (self.img_width, self.img_height), 1)
        draw = ImageDraw.Draw(img)


        corner_radius_pixels: int = int(self.corner_radius * self.resolution)
        
        padding: int = 2
        draw.rounded_rectangle(
            [padding, padding, self.img_width - 1 - padding, self.img_height - 1 - padding],
            radius=corner_radius_pixels,
            fill=0,  # Black fill (will be extruded)
            outline=0  # Black outline (will be extruded)
        )
        
        return img

    def create_badge_recess_heightmap(self, main_heightmap: Image.Image) -> Image.Image:
        """
        Chomp out the recess part of the badge
         
        Args:
            main_heightmap (Image.Image): The main badge heightmap image to modify.
        
        Returns:
            Image.Image: A new PIL Image with the magnet recess cut out.
        """
        recess_heightmap = main_heightmap.copy()
        recess_width_pixels: int = int(self.recess_width * self.resolution)
        recess_height_pixels: int = int(self.recess_height * self.resolution)
        
        recess_start_x: int = (self.img_width - recess_width_pixels) // 2
        recess_start_y: int = (self.img_height - recess_height_pixels) // 2
        recess_end_x: int = recess_start_x + recess_width_pixels
        recess_end_y: int = recess_start_y + recess_height_pixels

        draw = ImageDraw.Draw(recess_heightmap)
        draw.rectangle(
            [recess_start_x, recess_start_y, recess_end_x, recess_end_y],
            fill=1,  
            outline=1  
        )
        return recess_heightmap
    
    def pil_to_meshlib_distancemap(self, pil_image: Image.Image) -> Optional[mr.DistanceMap]:
        """
        Convert a PIL Image to a MeshLib DistanceMap using temporary file conversion.
        
        Args:
            pil_image (Image.Image): The PIL Image to convert.
        
        Returns:
            Optional[mr.DistanceMap]: A MeshLib DistanceMap object if conversion succeeds,
                                    None if conversion fails. 

        """
        if pil_image.mode != 'L':
            pil_image = pil_image.convert('L')
        
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            temp_filename: str = tmp_file.name
        
        try:
            pil_image.save(temp_filename)
            distance_map: mr.DistanceMap = mr.loadDistanceMapFromImage(temp_filename, 0)
    
            os.unlink(temp_filename)
            return distance_map
            
        except Exception as e:
            try:
                os.unlink(temp_filename)
            except:
                pass
            
            return None
    
    def image_to_mesh(self, image: Image.Image) -> Optional[mr.Mesh]:
        """
        Convert an image to a mesh. 

        Returns:
            Optional[mr.Mesh]: A MeshLib mesh if conversion succeeds, None if any step fails.
        """
        # Create 2D iso-polylines
        polyline: mr.Polyline2 = mr.distanceMapTo2DIsoPolyline(image, isoValue=0.5)

        # Triangulate contours
        contours: mr.Contours2 = polyline.contours()
        meshmain: mr.Mesh = mr.triangulateContours(contours)
        return meshmain

    def distancemap_to_mesh(self, distance_map: mr.DistanceMap) -> Optional[mr.Mesh]:
        """
        Convert a DistanceMap to a mesh. 

        Returns:
            Optional[mr.Mesh]: A MeshLib mesh if conversion succeeds, None if any step fails.
        """
        try:
            # Create 2D iso-polylines
            polyline: mr.Polyline2 = mr.distanceMapTo2DIsoPolyline(distance_map, isoValue=0.5)

            # Triangulate contours
            contours: mr.Contours2 = polyline.contours()
            mesh: mr.Mesh = mr.triangulateContours(contours)
            return mesh
        except Exception as e:
            print(f"Error converting DistanceMap to mesh: {str(e)}")
            return None

    def create_badge_mesh(self) -> Optional[mr.Mesh]:
        """
        Create the 3D badge mesh by combining main and recess meshes.
        
        Returns:
            Optional[mr.Mesh]: A complete 3D badge mesh if creation succeeds,
                              None if any step fails. 
        
        """
        # Create heightmaps
        main_heightmap: Image.Image = self.create_badge_main_heightmap()
        recess_heightmap: Image.Image = self.create_badge_recess_heightmap(main_heightmap)
        
        # Convert PIL images to DistanceMaps
        dmmain: Optional[mr.DistanceMap] = self.pil_to_meshlib_distancemap(main_heightmap)
        if dmmain is None:
            return None
            
        dmrecess: Optional[mr.DistanceMap] = self.pil_to_meshlib_distancemap(recess_heightmap)
        if dmrecess is None:
            return None

        meshmain = self.image_to_mesh(dmmain)
        meshrecess = self.image_to_mesh(dmrecess)

        # Scale the Z-axis values appropriately
        scaled_thickness = self.badge_thickness * self.resolution
        scaled_recess_depth = self.recess_depth * self.resolution

        # Move the recess mesh to the top of the main mesh
        meshrecess.transform(mr.AffineXf3f.translation(mr.Vector3f(0, 0, scaled_thickness - scaled_recess_depth)))

        # Main mesh: from 0 to scaled_thickness - scaled_recess_depth
        mr.addBaseToPlanarMesh(meshmain, zOffset=scaled_thickness - scaled_recess_depth)
        # Recess mesh: from scaled_thickness - scaled_recess_depth to scaled_thickness
        mr.addBaseToPlanarMesh(meshrecess, zOffset=scaled_recess_depth)

        merged_mesh: mr.Mesh = mr.mergeMeshes([meshmain, meshrecess])

        scale_factor: float = 0.1  # 1/10 to convert from 10 pixels per mm back to mm
        
        # Scale down to to the correct physical dimensions
        scale_transform = mr.RigidScaleXf3f(mr.Vector3f(0, 0, 0), mr.Vector3f(0, 0, 0), scale_factor)
        affine_transform = scale_transform.rigidScaleXf()

        merged_mesh.transform(affine_transform)

        # Decimate the mesh to reduce the number of faces and file size
        merged_mesh.packOptimally()
        settings = mr.DecimateSettings()
        settings.maxDeletedFaces = 100000
        settings.maxError = 0.1
        mr.decimateMesh(merged_mesh, settings)

        self.badge_mesh = merged_mesh

        return merged_mesh
    
    def save_badge_stl(self, output_filename: str = "badge.stl") -> bool:
        """
        Create and save the badge as an STL file.
        
        Args:
            output_filename (str): The filename for the output STL file.
                                 Defaults to "badge.stl".
        
        Returns:
            bool: True if the STL file was successfully created and saved,
                  False if any step failed (mesh creation or file saving).
        
        """
        
        # Create the composite badge
        if self.badge_mesh is None:
            badge_mesh: Optional[mr.Mesh] = self.create_badge_mesh()
        
        if self.badge_mesh is None:
            print("Failed to create badge mesh")
            return False
        
        # Save the mesh as STL
        try:
            mr.saveMesh(self.badge_mesh, output_filename)
            print(f"Successfully saved badge to {output_filename}")
            return True
            
        except Exception as e:
            print(f"Error saving STL file: {e}")
            return False
        
    def load_mesh_from_file(self, filepath: str) -> Optional[mr.Mesh]:
        """
        Load a mesh from a file and store it as self.mesh.
        
        Args:
            filepath (str): Path to the mesh file to load
            
        Returns:
            Optional[mr.Mesh]: The loaded mesh if successful, None if failed
        """
        try:
            # Check if file exists
            if not os.path.exists(filepath):
                print(f"Error: File {filepath} does not exist")
                return None
            
            # Determine file extension and load accordingly
            file_ext = os.path.splitext(filepath)[1].lower()
            
            if file_ext in ['.obj', '.stl', '.ply', '.3ds', '.dae', '.fbx']:
                # Use MeshLib to load the mesh
                loaded_mesh = mr.loadMesh(filepath)
                if loaded_mesh:
                    self.badge_mesh = loaded_mesh
                    return loaded_mesh
                else:
                    print(f"Error: Failed to load mesh from {filepath}")
                    return None
            else:
                print(f"Error: Unsupported file format {file_ext}")
                return None
                
        except Exception as e:
            print(f"Error loading mesh from {filepath}: {str(e)}")
            return None
    
    def create_cylinder_mesh(self, radius: float, height: float) -> mr.Mesh:
        """
        Create a simple cylinder mesh
        
        Args:
            radius (float): Radius of the cylinder in mm.
            height (float): Height of the cylinder in mm.
            
        Returns:
            mr.Mesh: Cylinder mesh.
        """

        img_size = int(radius * self.resolution * 2) + 8  # Ensure image is large enough for the circle
        
        img = Image.new('1', (img_size, img_size), 1)  # White background
        draw = ImageDraw.Draw(img)
        
        # Draw filled circle with 2-pixel padding (like working code)
        padding = 2
        center = img_size // 2
        radius_pixels = int(radius * self.resolution)
        
        # Ensure we have a valid circle
        if radius_pixels <= 0:
            print(f"Error: Invalid radius_pixels: {radius_pixels}")
            return None
            
        draw.ellipse([center - radius_pixels, center - radius_pixels, 
                     center + radius_pixels, center + radius_pixels], fill=0)
        
        cylinder_dm = self.pil_to_meshlib_distancemap(img)
        if cylinder_dm is None:
            print("Error: Failed to create DistanceMap from image")
            return None
            
        cylinder_mesh = self.distancemap_to_mesh(cylinder_dm)
        if cylinder_mesh is None:
            print("Error: Failed to convert DistanceMap to mesh")
            return None
         # Recess mesh: from scaled_thickness - scaled_recess_depth to scaled_thickness
        mr.addBaseToPlanarMesh(cylinder_mesh, zOffset=height * self.resolution)


        scale_factor: float = 0.1  # 1/10 to convert from 10 pixels per mm back to mm
        
        # Scale down to to the correct physical dimensions
        scale_transform = mr.RigidScaleXf3f(mr.Vector3f(0, 0, 0), mr.Vector3f(0, 0, 0), scale_factor)
        affine_transform = scale_transform.rigidScaleXf()
        cylinder_mesh.transform(affine_transform)

        return cylinder_mesh

    def create_crosshair_mesh(self, size: float = 10.0, height: float = 0.4) -> mr.Mesh:
        """
        Create a crosshair mesh that matches the PDF registration mark.
        
        Args:
            size (float): Size of the crosshair in mm (default: 10.0mm)
            height (float): Height/thickness of the crosshair in mm (default: 0.4mm)
            
        Returns:
            mr.Mesh: Crosshair mesh.
        """
        # Calculate image size with padding
        img_size = int(size * self.resolution) + 8  # Add padding for distance map
        
        img = Image.new('1', (img_size, img_size), 1)  # White background
        draw = ImageDraw.Draw(img)
        
        # Calculate crosshair dimensions
        center = img_size // 2
        half_size_pixels = int((size / 2) * self.resolution)
        line_width_pixels = max(1, int(0.5 * self.resolution))  # 0.5mm line width
        
        # Draw horizontal line
        draw.rectangle([
            center - half_size_pixels, center - line_width_pixels // 2,
            center + half_size_pixels, center + line_width_pixels // 2
        ], fill=0)
        
        # Draw vertical line
        draw.rectangle([
            center - line_width_pixels // 2, center - half_size_pixels,
            center + line_width_pixels // 2, center + half_size_pixels
        ], fill=0)
        
        # Convert image to distance map
        crosshair_dm = self.pil_to_meshlib_distancemap(img)
        if crosshair_dm is None:
            print("Error: Failed to create DistanceMap from crosshair image")
            return None
            
        # Convert distance map to mesh
        crosshair_mesh = self.distancemap_to_mesh(crosshair_dm)
        if crosshair_mesh is None:
            print("Error: Failed to convert DistanceMap to crosshair mesh")
            return None
            
        # Add height to the mesh
        mr.addBaseToPlanarMesh(crosshair_mesh, zOffset=height * self.resolution)
        
        # Scale down to correct physical dimensions
        scale_factor: float = 0.1  # 1/10 to convert from 10 pixels per mm back to mm
        scale_transform = mr.RigidScaleXf3f(mr.Vector3f(0, 0, 0), mr.Vector3f(0, 0, 0), scale_factor)
        affine_transform = scale_transform.rigidScaleXf()
        crosshair_mesh.transform(affine_transform)
        
        return crosshair_mesh

        
    def create_registration_knob_stl(self, output_file: str) -> bool:
        """
        Generate STL file for the registration knobs.
        
        Args:
            output_file (str): Output STL filename.
            
        Returns:
            bool: True if STL generation succeeds, False otherwise.
        """
        
        # Create a simple cylinder mesh for registration knobs
        knob_height = self.registration_knob_height
        knob_radius = self.registration_knob_diameter / 2
        
        all_knobs = []
        
        # Top center knob
        top_knob = self.create_cylinder_mesh(knob_radius, knob_height)
        top_knob.transform(mr.AffineXf3f.translation(mr.Vector3f(0, self.page_height/2 - knob_height - self.page_margin, 0)))
        
        # Bottom left knob
        left_knob = self.create_cylinder_mesh(knob_radius, knob_height)
        left_knob.transform(mr.AffineXf3f.translation(mr.Vector3f(-self.page_width/3, -self.page_height/2 + knob_height+ self.page_margin, 0)))
        
        # Bottom right knob
        right_knob = self.create_cylinder_mesh(knob_radius, knob_height)
        right_knob.transform(mr.AffineXf3f.translation(mr.Vector3f(self.page_width/3, -self.page_height/2 + knob_height + self.page_margin, 0)))
        
        # Merge all knobs
        self.registration_mesh = mr.mergeMeshes([top_knob, left_knob, right_knob])
        
        # Save STL
        mr.saveMesh(self.registration_mesh, output_file)
        return self.registration_mesh
    
    def create_l_shaped_stop(self, arm_length: float = 20.0, arm_width: float = 5.0, height: float = 1.0) -> mr.Mesh:
        """
        Create an L-shaped registration stop for acetate sheet alignment.
        
        Args:
            arm_length (float): Length of each arm in mm (default: 20.0)
            arm_width (float): Width of each arm in mm (default: 5.0)
            height (float): Height/thickness of the stop in mm (default: 2.0)
            
        Returns:
            mr.Mesh: The L-shaped mesh
        """
        # Calculate image dimensions for the L shape
        img_size = int(max(arm_length, arm_width) * self.resolution * 2) + 4
        
        # Create a white background image
        img = Image.new('RGB', (img_size, img_size), (255, 255, 255))
        draw = ImageDraw.Draw(img)
             
        # Convert mm to pixels
        arm_length_px = int(arm_length * self.resolution)
        arm_width_px = int(arm_width * self.resolution)
        
        # Vertical arm (from center down and to the right)
        vertical_left = 2
        vertical_right = 2+arm_width_px
        vertical_top = 2
        vertical_bottom = 2+arm_length_px
        
        # Horizontal arm (from center right)
        horizontal_left = 2
        horizontal_right = 2+arm_length_px
        horizontal_top = 2
        horizontal_bottom = 2+arm_width_px
        
        # Draw the L shape as filled rectangles
        draw.rectangle([vertical_left, vertical_top, vertical_right, vertical_bottom], fill=(0, 0, 0))
        draw.rectangle([horizontal_left, horizontal_top, horizontal_right, horizontal_bottom], fill=(0, 0, 0))
        
        # Convert image to DistanceMap first, then to mesh
        distance_map = self.pil_to_meshlib_distancemap(img)
        if distance_map is None:
            print("Error: Failed to create DistanceMap from L-shape image")
            return None
            
        mesh = self.distancemap_to_mesh(distance_map)
        if mesh is None:
            print("Error: Failed to convert DistanceMap to L-shape mesh")
            return None
        
        # Add height to the mesh
        scaled_height = height * self.resolution
        mr.addBaseToPlanarMesh(mesh, zOffset=scaled_height)
        
        # Scale down to correct physical dimensions
        scale_factor: float = 0.1  # 1/10 to convert from 10 pixels per mm back to mm
        scale_transform = mr.RigidScaleXf3f(mr.Vector3f(0, 0, 0), mr.Vector3f(0, 0, 0), scale_factor)
        affine_transform = scale_transform.rigidScaleXf()
        mesh.transform(affine_transform)
        
        return mesh
    
    def create_l_stop_registration_stl(self, output_file: str, arm_length: float = 20.0, arm_width: float = 5.0, height: float = 1.0, include_cylinder: bool = True) -> bool:
        """
        Generate STL file with registration stops for acetate sheet alignment.
        
        Args:
            output_file (str): Output STL filename.
            arm_length (float): Length of each arm in mm (default: 20.0)
            arm_width (float): Width of each arm in mm (default: 5.0)
            height (float): Height/thickness of the stop in mm (default: 2.0)
            include_cylinder (bool): Whether to include the cylinder stop (default: True)
            
        Returns:
            bool: True if STL generation succeeds, False otherwise.
        """
        # A4 is 210mm × 297mm, but I'm unsure why I've had to manually adjust so much

        stop_positions = [
            (0, -6, self.page_height-arm_length-14),  # Top left corner, just outside paper 
            (1, self.page_width + 6, self.page_height-arm_length-14),
        ]
        
        # Add cylinder stop position only if include_cylinder is True
        if include_cylinder:
            stop_positions.append((2, self.page_width/2, -6))  # Top right corner, just outside paper
         
        all_stops = [] 
        for i, (stop_type, x, y) in enumerate(stop_positions):
            if stop_type <2: # L-shaped stop
                stop_mesh = self.create_l_shaped_stop(arm_length, arm_width, height)
                # Mirror the second stop (top right) in X axis before we translate
                if stop_type== 1:  
                    mirror_y_matrix = mr.Matrix3f(
                        mr.Vector3f(-1,  0,  0), 
                        mr.Vector3f( 0,  1,  0), 
                        mr.Vector3f( 0,  0,  1)    
                    )
                    mirror_y_xf = mr.AffineXf3f.linear(mirror_y_matrix)
                    stop_mesh.transform(mirror_y_xf)
            elif stop_type == 2: # Cylinder stop
                stop_mesh = self.create_cylinder_mesh(3.0, 2.0)
            # Move to the right place
            stop_mesh.transform(mr.AffineXf3f.translation(mr.Vector3f(x, y, 0)))
            
            all_stops.append(stop_mesh)
        
        registration_mesh = mr.mergeMeshes(all_stops)

        mr.saveMesh(registration_mesh, output_file)
        return True

    
    def create_badge_layout_stl(self, output_file: str, badge_centers: list, pdf_generator) -> bool:
        """
        Generate STL file with badges positioned at the exact centers from PDF layout.
        
        Args:
            output_file (str): Output STL filename.
            badge_centers (list): List of (center_x, center_y) tuples in mm from page origin.
            pdf_generator: PDFGenerator instance to get layout parameters.
            
        Returns:
            bool: True if STL generation succeeds, False otherwise.
        """
        if not self.badge_mesh:
            print("Error: No badge mesh available. Load or create a badge mesh first.")
            return False
        
        if not badge_centers:
            print("Error: No badge center points provided for layout.")
            return False
        
        all_badges = []
        
        # Get the original mesh bounding box to understand its current position
        original_bbox = self.badge_mesh.computeBoundingBox()
        original_center_x = (original_bbox.min.x + original_bbox.max.x) / 2
        original_center_y = (original_bbox.min.y + original_bbox.max.y) / 2
        
        # Note: PDF coordinates are bottom-up, mesh coordinates are typically top-down
        # We need to convert from PDF coordinates to mesh coordinates
        page_height = pdf_generator.page_height
        
        for i, (pdf_center_x, pdf_center_y) in enumerate(badge_centers):
            # Create a copy of the badge mesh
            badge_mesh = mr.Mesh(self.badge_mesh)
            
            # Convert PDF coordinates to mesh coordinates
            # PDF Y increases upward from bottom, mesh Y increases downward from top
            mesh_center_x = pdf_center_x
            mesh_center_y = page_height - pdf_center_y  # Flip Y coordinate
            
            # Calculate offset from original mesh center to target position
            offset_x = mesh_center_x - original_center_x
            offset_y = mesh_center_y - original_center_y
            
            # Transform the badge to the target position
            badge_mesh.transform(mr.AffineXf3f.translation(mr.Vector3f(offset_x, offset_y, 0)))
            
            all_badges.append(badge_mesh)
                
        # Merge all badge meshes into a single mesh
        if all_badges:
            layout_mesh = mr.mergeMeshes(all_badges)
            
            mr.saveMesh(layout_mesh, output_file)
            return True
        else:
            print("Error: No badges were created for the layout.")
            return False
    
    def get_mesh_stats(self, mesh: mr.Mesh) -> Optional[dict]:
        """
        Get statistics about a mesh
        
        Returns:
            Optional[dict]: Dictionary with vertex, face, and edge counts, or None if no mesh
        """
        
        if mesh is None:
            print("Error: Mesh is None")
            return None
            
        try:
            stats = {
                'vertices': mesh.topology.numValidVerts(),
                'faces': mesh.topology.numValidFaces()
            }
            return stats
        except Exception as e:
            print(f"Error getting mesh statistics: {str(e)}")
            print(f"Mesh type: {type(mesh)}")
            print(f"Mesh has topology: {hasattr(mesh, 'topology')}")
            return None            
        
def main() -> None:
    # Create badge maker instance
    maker: MeshBuilder = MeshBuilder()


    badgemesh = maker.create_badge_mesh()
    dimensions = maker.get_mesh_size()
    assert math.isclose(dimensions['width'], 75.0, rel_tol=0.1),"Error creating badge mesh: Mesh width is not 75.0mm"
    assert math.isclose(dimensions['height'], 30.0, rel_tol=0.1),"Error creating badge mesh: Mesh height is not 30.0mm"
    assert math.isclose(dimensions['depth'], 3.0, rel_tol=0.1),"Error creating badge mesh: Mesh depth is not 3.0mm"
    print(dimensions)
    # Create and save the badge STL
    success: bool = maker.save_badge_stl("single_badge.stl")

    maker.load_mesh_from_file("HeartBadge.stl")
    dimensions = maker.get_mesh_size()
    print(dimensions)
    
    if success:
        print("Files created:")
        print("  - single_badge.stl (main badge file)")
    else:
        print("\nBadge creation failed. Check the error messages above.")

if __name__ == "__main__":
    main()
