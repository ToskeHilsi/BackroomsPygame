import pygame
import random
import math
import sys
import time
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Set, Optional

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
TILE_SIZE = 20
GRID_WIDTH = SCREEN_WIDTH // TILE_SIZE
GRID_HEIGHT = SCREEN_HEIGHT // TILE_SIZE

# Fade system constants
FADE_TIME = 300  # Frames until tile completely fades (5 seconds at 60 FPS)
FADE_RATE = 1.0 / FADE_TIME

# Sprint system constants
MAX_STAMINA = 100
STAMINA_DRAIN_RATE = 1.5  # Per frame while sprinting
STAMINA_REGEN_RATE = 0.8  # Per frame while not sprinting
SPRINT_MULTIPLIER = 2.0

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
YELLOW = (255, 255, 0)
DARK_YELLOW = (255, 255, 100)
BEIGE = (245, 245, 220)
CREAM = (255, 253, 208)
BROWN = (139, 69, 19)
DARK_BROWN = (101, 67, 33)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
ORANGE = (255, 165, 0)
PURPLE = (128, 0, 128)
PINK = (255, 192, 203)
LIGHT_GRAY = (192, 192, 192)
FLUORESCENT_WHITE = (248, 248, 255)
DIRTY_WHITE = (240, 240, 235)
BUZZING_YELLOW = (255, 255, 150)
# Poolrooms colors
POOL_BLUE = (64, 164, 223)
POOL_TILE_WHITE = (250, 250, 250)
POOL_TILE_BLUE = (200, 230, 255)
POOL_WATER = (100, 200, 255)
HUMID_YELLOW = (255, 255, 200)

# Game settings
PLAYER_SPEED = 2
FLASHLIGHT_RANGE = 80
FLASHLIGHT_ANGLE = 60  # degrees

class TileType(Enum):
    EMPTY = 0
    WALL = 1
    FLOOR = 2
    DOOR = 3
    EXIT = 4
    VENT = 5
    WATER_DAMAGE = 6
    ELECTRICAL = 7
    STAIRWELL = 8
    ELEVATOR = 9
    LEVEL_EXIT = 10  # Exit to next level
    POOL = 11  # Pool water
    POOL_EDGE = 12  # Pool edge tiles

class RoomType(Enum):
    OFFICE_SPACE = "office_space"
    LONG_HALLWAY = "long_hallway"
    CONFERENCE_ROOM = "conference_room"
    STORAGE_ROOM = "storage_room"
    ELECTRICAL_ROOM = "electrical_room"
    FLOODED_AREA = "flooded_area"
    MAINTENANCE = "maintenance"
    LOBBY = "lobby"
    CAFETERIA = "cafeteria"
    BATHROOM = "bathroom"
    SERVER_ROOM = "server_room"
    ABANDONED_OFFICE = "abandoned_office"
    # Poolrooms types
    POOL_AREA = "pool_area"
    POOL_CORRIDOR = "pool_corridor"
    POOL_CHANGING = "pool_changing"

class LevelType(Enum):
    LEVEL_0 = "level_0"  # Classic yellow backrooms
    POOLROOMS = "poolrooms"  # Level 37 - The Poolrooms

@dataclass
class Room:
    x: int
    y: int
    width: int
    height: int
    room_type: RoomType
    is_lit: bool = False
    connections: List[Tuple[int, int]] = None

    def __post_init__(self):
        if self.connections is None:
            self.connections = []

    def center(self) -> Tuple[int, int]:
        return (self.x + self.width // 2, self.y + self.height // 2)

    def overlaps(self, other: 'Room') -> bool:
        return not (self.x + self.width <= other.x or 
                   other.x + other.width <= self.x or 
                   self.y + self.height <= other.y or 
                   other.y + other.height <= self.y)

class Entity:
    """Mysterious entity that appears as another player just out of view"""
    def __init__(self):
        self.x = 0
        self.y = 0
        self.visible = False
        self.visibility_timer = 0
        self.spawn_timer = random.randint(1800, 3600)  # 30-60 seconds at 60 FPS
        self.angle = 0  # Facing direction
        self.last_player_x = 0
        self.last_player_y = 0
        self.move_timer = 0
        self.target_angle = 0
        
    def update(self, player_x: float, player_y: float, level_type: LevelType, visible_tiles: Set, level_map: List[List[TileType]]):
        # Only spawn in Level 0, not in Poolrooms
        if level_type != LevelType.LEVEL_0:
            self.visible = False
            return
            
        self.spawn_timer -= 1
        
        if self.spawn_timer <= 0 and not self.visible:
            # Try to spawn the entity just outside the visible area but close to player
            attempts = 0
            spawned = False
            
            while attempts < 20 and not spawned:
                distance = random.randint(120, 180)  # Close to player
                angle = random.uniform(0, 2 * math.pi)
                
                spawn_x = player_x + math.cos(angle) * distance
                spawn_y = player_y + math.sin(angle) * distance
                
                # Check if spawn position is within map bounds
                spawn_grid_x = int(spawn_x // TILE_SIZE)
                spawn_grid_y = int(spawn_y // TILE_SIZE)
                
                if (0 <= spawn_grid_x < len(level_map[0]) and 
                    0 <= spawn_grid_y < len(level_map) and
                    level_map[spawn_grid_y][spawn_grid_x] == TileType.FLOOR):
                    
                    # Check if spawn position would be visible - if so, try different position
                    if (spawn_grid_x, spawn_grid_y) not in visible_tiles:
                        self.x = spawn_x
                        self.y = spawn_y
                        spawned = True
                
                attempts += 1
            
            if spawned:
                # Make entity face a random direction initially
                self.angle = random.uniform(0, 360)
                self.target_angle = self.angle
                
                self.visible = True
                self.visibility_timer = random.randint(120, 300)  # 2-5 seconds visible
                self.spawn_timer = random.randint(1200, 2400)  # Next spawn in 20-40 seconds
                
                self.last_player_x = player_x
                self.last_player_y = player_y
                self.move_timer = 0
            else:
                self.spawn_timer = 60  # Try again in 1 second if couldn't spawn
            
        if self.visible:
            self.visibility_timer -= 1
            self.move_timer += 1
            
            # Entity movement behavior - move around like a player
            if self.move_timer % 60 == 0:  # Change direction every second
                self.target_angle = random.uniform(0, 360)
            
            # Smoothly rotate towards target angle
            angle_diff = self.target_angle - self.angle
            if angle_diff > 180:
                angle_diff -= 360
            elif angle_diff < -180:
                angle_diff += 360
            
            self.angle += angle_diff * 0.1  # Smooth rotation
            
            # Move forward in facing direction
            move_speed = 1.0  # Slightly slower than player
            dx = math.cos(math.radians(self.angle)) * move_speed
            dy = math.sin(math.radians(self.angle)) * move_speed
            
            # Check collision before moving (like player movement)
            new_x = self.x + dx
            new_y = self.y + dy
            
            if self._can_move_to(new_x, new_y, level_map):
                self.x = new_x
                self.y = new_y
            else:
                # If can't move forward, pick a new random direction
                self.target_angle = random.uniform(0, 360)
            
            if self.visibility_timer <= 0:
                self.visible = False
    
    def _can_move_to(self, x: float, y: float, level_map: List[List[TileType]]) -> bool:
        """Check if entity can move to this position (same logic as player)"""
        entity_size = 8  # Half the entity size
        
        positions_to_check = [
            (x - entity_size, y - entity_size),  # Top-left
            (x + entity_size, y - entity_size),  # Top-right
            (x - entity_size, y + entity_size),  # Bottom-left
            (x + entity_size, y + entity_size),  # Bottom-right
            (x, y)  # Center
        ]
        
        for check_x, check_y in positions_to_check:
            grid_x = int(check_x // TILE_SIZE)
            grid_y = int(check_y // TILE_SIZE)
            
            # Check bounds
            if not (0 <= grid_x < len(level_map[0]) and 0 <= grid_y < len(level_map)):
                return False
            
            # Check for walls and pool edges (but allow walking on pools)
            tile_type = level_map[grid_y][grid_x]
            if tile_type == TileType.WALL or tile_type == TileType.POOL_EDGE:
                return False
        
        return True
    
    def draw(self, screen, camera_x: float, camera_y: float):
        if not self.visible:
            return
            
        screen_x = int(self.x - camera_x)
        screen_y = int(self.y - camera_y)
        
        # Only draw if on screen
        if -50 <= screen_x <= SCREEN_WIDTH + 50 and -50 <= screen_y <= SCREEN_HEIGHT + 50:
            # Draw as a player-like figure (green rectangle like the real player)
            player_rect = pygame.Rect(screen_x - 8, screen_y - 8, 16, 16)
            # Slightly dimmer green to make it feel "off"
            entity_color = (0, 200, 0)
            pygame.draw.rect(screen, entity_color, player_rect)
            
            # Draw direction indicator (like the real player)
            end_x = screen_x + math.cos(math.radians(self.angle)) * 20
            end_y = screen_y + math.sin(math.radians(self.angle)) * 20
            # Slightly dimmer white
            pygame.draw.line(screen, (200, 200, 200), 
                            (screen_x, screen_y), 
                            (int(end_x), int(end_y)), 2)

class Player:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.angle = 0  # Facing direction in degrees
        self.has_flashlight = True
        self.stamina = MAX_STAMINA
        self.is_sprinting = False
        self.can_sprint = True  # Flag to track if player can start sprinting
        
    def move(self, dx: float, dy: float, level_map: List[List[TileType]], is_sprint_pressed: bool):
        # Handle sprinting - can only sprint if stamina is full OR already sprinting
        if self.stamina <= 0:
            self.can_sprint = False  # Can't sprint until stamina is full again
        elif self.stamina >= MAX_STAMINA:
            self.can_sprint = True   # Can sprint again when stamina is full
        
        can_sprint = self.can_sprint and is_sprint_pressed and (dx != 0 or dy != 0)
        
        if can_sprint:
            self.is_sprinting = True
            self.stamina = max(0, self.stamina - STAMINA_DRAIN_RATE)
            speed_multiplier = SPRINT_MULTIPLIER
        else:
            self.is_sprinting = False
            if self.stamina < MAX_STAMINA:
                self.stamina = min(MAX_STAMINA, self.stamina + STAMINA_REGEN_RATE)
            speed_multiplier = 1.0
        
        # Apply movement with speed multiplier
        dx *= speed_multiplier
        dy *= speed_multiplier
        
        # Check horizontal movement
        new_x = self.x + dx
        if self._can_move_to(new_x, self.y, level_map):
            self.x = new_x
        
        # Check vertical movement
        new_y = self.y + dy
        if self._can_move_to(self.x, new_y, level_map):
            self.y = new_y
    
    def _can_move_to(self, x: float, y: float, level_map: List[List[TileType]]) -> bool:
        # Player is 16x16 pixels, so check all four corners plus center
        player_size = 8  # Half the player size (16/2)
        
        positions_to_check = [
            (x - player_size, y - player_size),  # Top-left
            (x + player_size, y - player_size),  # Top-right
            (x - player_size, y + player_size),  # Bottom-left
            (x + player_size, y + player_size),  # Bottom-right
            (x, y)  # Center
        ]
        
        for check_x, check_y in positions_to_check:
            grid_x = int(check_x // TILE_SIZE)
            grid_y = int(check_y // TILE_SIZE)
            
            # Check bounds
            if not (0 <= grid_x < len(level_map[0]) and 0 <= grid_y < len(level_map)):
                return False
            
            # Check for walls and pool edges (but allow walking on pools)
            tile_type = level_map[grid_y][grid_x]
            if tile_type == TileType.WALL or tile_type == TileType.POOL_EDGE:
                return False
        
        return True
    
    def update_angle(self, mouse_pos: Tuple[int, int]):
        dx = mouse_pos[0] - self.x
        dy = mouse_pos[1] - self.y
        self.angle = math.degrees(math.atan2(dy, dx))

class BackroomsGenerator:
    def __init__(self, width: int, height: int, level_type: LevelType = LevelType.LEVEL_0):
        self.width = width
        self.height = height
        self.level_type = level_type
        self.grid = [[TileType.WALL for _ in range(width)] for _ in range(height)]
        self.rooms = []
        
    def generate(self) -> Tuple[List[List[TileType]], List[Room]]:
        if self.level_type == LevelType.POOLROOMS:
            self._generate_poolrooms()
        else:
            self._generate_level_0()
        return self.grid, self.rooms
    
    def _generate_level_0(self):
        """Generate classic Level 0 backrooms"""
        self._generate_rooms()
        self._connect_rooms()
        self._add_room_features()
        self._add_level_exit()
    
    def _generate_poolrooms(self):
        """Generate Level 37 - The Poolrooms"""
        self._generate_pool_rooms()
        self._connect_rooms()
        self._add_pools()
        self._add_poolrooms_features()
        self._add_level_exit()
    
    def _generate_rooms(self):
        attempts = 0
        while len(self.rooms) < 20 and attempts < 150:
            room_type = random.choice(list(RoomType))
            if room_type in [RoomType.POOL_AREA, RoomType.POOL_CORRIDOR, RoomType.POOL_CHANGING]:
                continue  # Skip poolrooms types in Level 0
            
            width, height = self._get_room_size(room_type)
            
            x = random.randint(1, self.width - width - 1)
            y = random.randint(1, self.height - height - 1)
            
            # Most backrooms areas are dark with flickering lights
            is_lit = random.random() < 0.3  # 30% chance of being lit
            new_room = Room(x, y, width, height, room_type, is_lit)
            
            if not any(new_room.overlaps(existing) for existing in self.rooms):
                self.rooms.append(new_room)
                self._carve_room(new_room)
            
            attempts += 1
    
    def _generate_pool_rooms(self):
        """Generate rooms specific to the poolrooms"""
        pool_room_types = [RoomType.POOL_AREA, RoomType.POOL_CORRIDOR, RoomType.POOL_CHANGING]
        attempts = 0
        while len(self.rooms) < 15 and attempts < 150:
            room_type = random.choice(pool_room_types)
            width, height = self._get_room_size(room_type)
            
            x = random.randint(1, self.width - width - 1)
            y = random.randint(1, self.height - height - 1)
            
            # Poolrooms are better lit than Level 0
            is_lit = random.random() < 0.7  # 70% chance of being lit
            new_room = Room(x, y, width, height, room_type, is_lit)
            
            if not any(new_room.overlaps(existing) for existing in self.rooms):
                self.rooms.append(new_room)
                self._carve_room(new_room)
            
            attempts += 1
    
    def _get_room_size(self, room_type: RoomType) -> Tuple[int, int]:
        size_ranges = {
            RoomType.OFFICE_SPACE: (8, 16, 6, 12),
            RoomType.LONG_HALLWAY: (20, 40, 3, 6),
            RoomType.CONFERENCE_ROOM: (10, 16, 8, 14),
            RoomType.STORAGE_ROOM: (4, 8, 4, 8),
            RoomType.ELECTRICAL_ROOM: (5, 8, 5, 8),
            RoomType.FLOODED_AREA: (8, 14, 8, 14),
            RoomType.MAINTENANCE: (6, 10, 4, 8),
            RoomType.LOBBY: (12, 20, 10, 16),
            RoomType.CAFETERIA: (12, 18, 8, 14),
            RoomType.BATHROOM: (4, 8, 6, 10),
            RoomType.SERVER_ROOM: (6, 10, 6, 10),
            RoomType.ABANDONED_OFFICE: (6, 12, 6, 12),
            # Poolrooms sizes
            RoomType.POOL_AREA: (15, 25, 10, 20),
            RoomType.POOL_CORRIDOR: (25, 45, 4, 8),
            RoomType.POOL_CHANGING: (8, 12, 6, 10)
        }
        
        min_w, max_w, min_h, max_h = size_ranges.get(room_type, (6, 12, 6, 12))
        return random.randint(min_w, max_w), random.randint(min_h, max_h)
    
    def _carve_room(self, room: Room):
        for y in range(room.y, room.y + room.height):
            for x in range(room.x, room.x + room.width):
                if 0 <= x < self.width and 0 <= y < self.height:
                    self.grid[y][x] = TileType.FLOOR
    
    def _connect_rooms(self):
        if len(self.rooms) < 2:
            return
            
        connected = {0}
        unconnected = set(range(1, len(self.rooms)))
        
        while unconnected:
            room_a_idx = random.choice(list(connected))
            room_b_idx = random.choice(list(unconnected))
            
            room_a = self.rooms[room_a_idx]
            room_b = self.rooms[room_b_idx]
            
            self._create_corridor(room_a.center(), room_b.center())
            
            connected.add(room_b_idx)
            unconnected.remove(room_b_idx)
        
        # Add some extra connections for that maze-like backrooms feel
        for _ in range(len(self.rooms) // 3):
            room_a = random.choice(self.rooms)
            room_b = random.choice(self.rooms)
            if room_a != room_b:
                self._create_corridor(room_a.center(), room_b.center())
    
    def _create_corridor(self, start: Tuple[int, int], end: Tuple[int, int]):
        x1, y1 = start
        x2, y2 = end
        
        # Create L-shaped corridor
        if random.choice([True, False]):
            # Horizontal first, then vertical
            for x in range(min(x1, x2), max(x1, x2) + 1):
                if 0 <= x < self.width and 0 <= y1 < self.height:
                    self.grid[y1][x] = TileType.FLOOR
            for y in range(min(y1, y2), max(y1, y2) + 1):
                if 0 <= x2 < self.width and 0 <= y < self.height:
                    self.grid[y][x2] = TileType.FLOOR
        else:
            # Vertical first, then horizontal
            for y in range(min(y1, y2), max(y1, y2) + 1):
                if 0 <= x1 < self.width and 0 <= y < self.height:
                    self.grid[y][x1] = TileType.FLOOR
            for x in range(min(x1, x2), max(x1, x2) + 1):
                if 0 <= x < self.width and 0 <= y2 < self.height:
                    self.grid[y2][x] = TileType.FLOOR
    
    def _add_room_features(self):
        for room in self.rooms:
            self._add_features_by_type(room)
    
    def _add_features_by_type(self, room: Room):
        cx, cy = room.center()
        
        if room.room_type == RoomType.STORAGE_ROOM:
            # Add some exits/items scattered around
            for _ in range(random.randint(1, 3)):
                x = random.randint(room.x + 1, room.x + room.width - 2)
                y = random.randint(room.y + 1, room.y + room.height - 2)
                if self.grid[y][x] == TileType.FLOOR:
                    self.grid[y][x] = TileType.EXIT
        
        elif room.room_type == RoomType.ELECTRICAL_ROOM:
            # Add electrical hazards
            for _ in range(random.randint(2, 4)):
                x = random.randint(room.x + 1, room.x + room.width - 2)
                y = random.randint(room.y + 1, room.y + room.height - 2)
                if self.grid[y][x] == TileType.FLOOR:
                    self.grid[y][x] = TileType.ELECTRICAL
        
        elif room.room_type == RoomType.FLOODED_AREA:
            # Add water damage in center
            water_width = max(2, room.width // 2)
            water_height = max(2, room.height // 2)
            start_x = cx - water_width // 2
            start_y = cy - water_height // 2
            
            for y in range(start_y, start_y + water_height):
                for x in range(start_x, start_x + water_width):
                    if (room.x < x < room.x + room.width - 1 and 
                        room.y < y < room.y + room.height - 1):
                        self.grid[y][x] = TileType.WATER_DAMAGE
        
        elif room.room_type == RoomType.MAINTENANCE:
            # Add vents
            for _ in range(random.randint(1, 3)):
                x = random.randint(room.x + 1, room.x + room.width - 2)
                y = random.randint(room.y + 1, room.y + room.height - 2)
                if self.grid[y][x] == TileType.FLOOR:
                    self.grid[y][x] = TileType.VENT

    def _add_pools(self):
        """Add pools to poolrooms"""
        for room in self.rooms:
            if room.room_type == RoomType.POOL_AREA:
                # Add a pool in the center of the room, but smaller to avoid blocking exits
                pool_width = max(3, min(room.width - 6, room.width // 2))  # Smaller pool
                pool_height = max(3, min(room.height - 6, room.height // 2))  # Smaller pool
                start_x = room.x + (room.width - pool_width) // 2
                start_y = room.y + (room.height - pool_height) // 2
                
                # Create pool edges (only if there's space and won't block pathways)
                for y in range(start_y - 1, start_y + pool_height + 1):
                    for x in range(start_x - 1, start_x + pool_width + 1):
                        if (room.x + 2 <= x <= room.x + room.width - 3 and 
                            room.y + 2 <= y <= room.y + room.height - 3):  # Keep edges away from room borders
                            if (x == start_x - 1 or x == start_x + pool_width or 
                                y == start_y - 1 or y == start_y + pool_height):
                                # Only place pool edge if it won't block critical paths
                                if not ((x <= room.x + 2 or x >= room.x + room.width - 3) or
                                       (y <= room.y + 2 or y >= room.y + room.height - 3)):
                                    self.grid[y][x] = TileType.POOL_EDGE
                
                # Fill pool with water (smaller area)
                for y in range(start_y, start_y + pool_height):
                    for x in range(start_x, start_x + pool_width):
                        if (room.x + 2 < x < room.x + room.width - 3 and 
                            room.y + 2 < y < room.y + room.height - 3):
                            self.grid[y][x] = TileType.POOL
    
    def _add_poolrooms_features(self):
        """Add features specific to poolrooms"""
        for room in self.rooms:
            if room.room_type == RoomType.POOL_CHANGING:
                # Add some benches/lockers
                for _ in range(random.randint(1, 2)):
                    x = random.randint(room.x + 1, room.x + room.width - 2)
                    y = random.randint(room.y + 1, room.y + room.height - 2)
                    if self.grid[y][x] == TileType.FLOOR:
                        self.grid[y][x] = TileType.EXIT  # Repurpose as furniture
    
    def _add_level_exit(self):
        """Add an exit to the next level"""
        if not self.rooms:
            return
        
        # Place exit in a random room, preferably a larger one
        suitable_rooms = [room for room in self.rooms if room.width * room.height >= 64]
        if not suitable_rooms:
            suitable_rooms = self.rooms
        
        exit_room = random.choice(suitable_rooms)
        
        # Place exit in a corner of the room
        corner_positions = [
            (exit_room.x + 1, exit_room.y + 1),  # Top-left
            (exit_room.x + exit_room.width - 2, exit_room.y + 1),  # Top-right
            (exit_room.x + 1, exit_room.y + exit_room.height - 2),  # Bottom-left
            (exit_room.x + exit_room.width - 2, exit_room.y + exit_room.height - 2)  # Bottom-right
        ]
        
        for x, y in corner_positions:
            if 0 <= x < self.width and 0 <= y < self.height and self.grid[y][x] == TileType.FLOOR:
                self.grid[y][x] = TileType.LEVEL_EXIT
                break

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        
        # Game state
        self.current_level = LevelType.LEVEL_0
        self.game_won = False
        
        # Camera offset
        self.camera_x = 0
        self.camera_y = 0
        
        # Initialize first level
        self._init_level()
        
        # Mysterious entity
        self.entity = Entity()
        
        # Ping system
        self.ping_active = False
        self.ping_radius = 0
        self.ping_max_radius = 300
        self.ping_speed = 8
        self.exit_positions = []  # Store positions of level exits
        
        # Visibility system
        self.visible_tiles = set()
        self.explored_tiles = {}  # Now stores fade timers
        
    def _init_level(self):
        """Initialize the current level"""
        pygame.display.set_caption(f"The Backrooms - {self.current_level.value.replace('_', ' ').title()}")
        
        # Generate level layout
        generator = BackroomsGenerator(GRID_WIDTH * 3, GRID_HEIGHT * 3, self.current_level)
        self.level_map, self.rooms = generator.generate()
        
        # Find a starting position in the first room
        start_room = self.rooms[0] if self.rooms else None
        if start_room:
            if hasattr(self, 'player'):
                # Keep existing player, just move position
                self.player.x = start_room.center()[0] * TILE_SIZE
                self.player.y = start_room.center()[1] * TILE_SIZE
            else:
                self.player = Player(
                    start_room.center()[0] * TILE_SIZE,
                    start_room.center()[1] * TILE_SIZE
                )
        else:
            if hasattr(self, 'player'):
                self.player.x = SCREEN_WIDTH // 2
                self.player.y = SCREEN_HEIGHT // 2
            else:
                self.player = Player(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        
        # Reset visibility
        self.visible_tiles = set()
        self.explored_tiles = {}
        
        # Reset entity
        self.entity = Entity()
        
        # Find and store exit positions for ping system
        self.exit_positions = []
        for y in range(len(self.level_map)):
            for x in range(len(self.level_map[0])):
                if self.level_map[y][x] == TileType.LEVEL_EXIT:
                    self.exit_positions.append((x * TILE_SIZE, y * TILE_SIZE))
        
    def _transition_to_next_level(self):
        """Handle transition to next level"""
        if self.current_level == LevelType.LEVEL_0:
            self.current_level = LevelType.POOLROOMS
            self._init_level()
        elif self.current_level == LevelType.POOLROOMS:
            self.game_won = True
    
    def update(self):
        if self.game_won:
            return
            
        keys = pygame.key.get_pressed()
        dx = dy = 0
        
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy = -PLAYER_SPEED
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy = PLAYER_SPEED
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx = -PLAYER_SPEED
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx = PLAYER_SPEED
        
        # Check for sprint (Space key)
        is_sprint_pressed = keys[pygame.K_SPACE]
        
        # Check for ping (P key)
        if keys[pygame.K_p] and not self.ping_active:
            self.ping_active = True
            self.ping_radius = 0
        
        self.player.move(dx, dy, self.level_map, is_sprint_pressed)
        
        # Check for level exit collision
        player_grid_x = int(self.player.x // TILE_SIZE)
        player_grid_y = int(self.player.y // TILE_SIZE)
        
        if (0 <= player_grid_x < len(self.level_map[0]) and 
            0 <= player_grid_y < len(self.level_map) and
            self.level_map[player_grid_y][player_grid_x] == TileType.LEVEL_EXIT):
            self._transition_to_next_level()
        
        # Update camera to center on player
        self._update_camera()
        
        # Convert mouse position to world coordinates for player angle
        mouse_pos = pygame.mouse.get_pos()
        world_mouse_x = mouse_pos[0] + self.camera_x
        world_mouse_y = mouse_pos[1] + self.camera_y
        self.player.update_angle((world_mouse_x, world_mouse_y))
        
        self._update_visibility()
        
        # Update ping system
        if self.ping_active:
            self.ping_radius += self.ping_speed
            if self.ping_radius >= self.ping_max_radius:
                self.ping_active = False
                self.ping_radius = 0
        
        # Update mysterious entity (pass visible_tiles to avoid spawning in visible areas)
        self.entity.update(self.player.x, self.player.y, self.current_level, self.visible_tiles, self.level_map)
    
    def _update_camera(self):
        # Center camera on player
        self.camera_x = self.player.x - SCREEN_WIDTH // 2
        self.camera_y = self.player.y - SCREEN_HEIGHT // 2
    
    def _update_visibility(self):
        self.visible_tiles.clear()
        
        player_grid_x = int(self.player.x // TILE_SIZE)
        player_grid_y = int(self.player.y // TILE_SIZE)
        
        # Check if player is in a lit room
        current_room = self._get_current_room()
        
        if current_room and current_room.is_lit:
            # If in a lit room, make entire room visible
            for y in range(current_room.y, current_room.y + current_room.height):
                for x in range(current_room.x, current_room.x + current_room.width):
                    if 0 <= x < len(self.level_map[0]) and 0 <= y < len(self.level_map):
                        self.visible_tiles.add((x, y))
        
        # Always use flashlight mechanics (even in lit rooms)
        self._calculate_flashlight_visibility()
        
        # Update fade timers for explored tiles
        self._update_fade_timers()
        
        # Add/refresh visible tiles in explored tiles with full visibility
        for tile in self.visible_tiles:
            self.explored_tiles[tile] = 1.0  # Full visibility
    
    def _update_fade_timers(self):
        # Fade out tiles that are not currently visible
        tiles_to_remove = []
        for tile, visibility in self.explored_tiles.items():
            if tile not in self.visible_tiles:
                new_visibility = max(0.0, visibility - FADE_RATE)
                if new_visibility <= 0:
                    tiles_to_remove.append(tile)
                else:
                    self.explored_tiles[tile] = new_visibility
        
        # Remove completely faded tiles
        for tile in tiles_to_remove:
            del self.explored_tiles[tile]
    
    def _get_current_room(self) -> Optional[Room]:
        player_grid_x = int(self.player.x // TILE_SIZE)
        player_grid_y = int(self.player.y // TILE_SIZE)
        
        for room in self.rooms:
            if (room.x <= player_grid_x < room.x + room.width and
                room.y <= player_grid_y < room.y + room.height):
                return room
        return None
    
    def _calculate_flashlight_visibility(self):
        if not self.player.has_flashlight:
            return
        
        player_grid_x = int(self.player.x // TILE_SIZE)
        player_grid_y = int(self.player.y // TILE_SIZE)
        
        # Cast rays for flashlight cone
        start_angle = self.player.angle - FLASHLIGHT_ANGLE // 2
        end_angle = self.player.angle + FLASHLIGHT_ANGLE // 2
        
        for angle in range(int(start_angle), int(end_angle) + 1, 2):
            self._cast_ray(
                self.player.x / TILE_SIZE,
                self.player.y / TILE_SIZE,
                math.radians(angle),
                FLASHLIGHT_RANGE // TILE_SIZE
            )
    
    def _cast_ray(self, start_x: float, start_y: float, angle: float, max_distance: float):
        dx = math.cos(angle)
        dy = math.sin(angle)
        
        x, y = start_x, start_y
        distance = 0
        
        while distance < max_distance:
            grid_x, grid_y = int(x), int(y)
            
            if not (0 <= grid_x < len(self.level_map[0]) and 0 <= grid_y < len(self.level_map)):
                break
                
            self.visible_tiles.add((grid_x, grid_y))
            
            if self.level_map[grid_y][grid_x] == TileType.WALL:
                break
            
            x += dx * 0.1
            y += dy * 0.1
            distance += 0.1
    
    def _get_tile_color(self, tile_type: TileType, room_type: RoomType = None) -> Tuple[int, int, int]:
        if self.current_level == LevelType.POOLROOMS:
            return self._get_poolrooms_tile_color(tile_type, room_type)
        else:
            return self._get_level_0_tile_color(tile_type, room_type)
    
    def _get_level_0_tile_color(self, tile_type: TileType, room_type: RoomType = None) -> Tuple[int, int, int]:
        base_colors = {
            TileType.WALL: CREAM,  # Yellowy backrooms walls
            TileType.FLOOR: DARK_YELLOW,  # Moist carpet
            TileType.EXIT: GREEN,  # Emergency exits
            TileType.VENT: DARK_GRAY,  # Air vents
            TileType.WATER_DAMAGE: BLUE,  # Water stains
            TileType.ELECTRICAL: ORANGE,  # Electrical hazards
            TileType.STAIRWELL: LIGHT_GRAY,
            TileType.ELEVATOR: GRAY,
            TileType.LEVEL_EXIT: PURPLE,  # Level exit portal
        }
        
        # Modify colors based on room type for that authentic backrooms feel
        if room_type:
            if room_type == RoomType.OFFICE_SPACE and tile_type == TileType.FLOOR:
                return BEIGE  # Office carpet
            elif room_type == RoomType.LONG_HALLWAY and tile_type == TileType.FLOOR:
                return DARK_YELLOW  # Classic backrooms carpet
            elif room_type == RoomType.CONFERENCE_ROOM and tile_type == TileType.FLOOR:
                return BROWN  # Conference room carpet
            elif room_type == RoomType.FLOODED_AREA and tile_type == TileType.FLOOR:
                return DARK_BROWN  # Water-damaged carpet
            elif room_type == RoomType.ELECTRICAL_ROOM and tile_type == TileType.FLOOR:
                return GRAY  # Industrial flooring
            elif room_type == RoomType.BATHROOM and tile_type == TileType.FLOOR:
                return DIRTY_WHITE  # Tile flooring
            elif room_type == RoomType.SERVER_ROOM and tile_type == TileType.FLOOR:
                return DARK_GRAY  # Raised server room floor
            elif room_type == RoomType.ABANDONED_OFFICE and tile_type == TileType.FLOOR:
                return DARK_BROWN  # Old, deteriorated carpet
        
        return base_colors.get(tile_type, BUZZING_YELLOW)
    
    def _get_poolrooms_tile_color(self, tile_type: TileType, room_type: RoomType = None) -> Tuple[int, int, int]:
        base_colors = {
            TileType.WALL: POOL_TILE_WHITE,  # White tiled walls
            TileType.FLOOR: POOL_TILE_BLUE,  # Light blue tiles
            TileType.EXIT: GREEN,  # Emergency exits
            TileType.VENT: DARK_GRAY,  # Air vents
            TileType.WATER_DAMAGE: BLUE,  # Water stains
            TileType.ELECTRICAL: ORANGE,  # Electrical hazards
            TileType.LEVEL_EXIT: PURPLE,  # Level exit portal
            TileType.POOL: POOL_WATER,  # Pool water
            TileType.POOL_EDGE: POOL_BLUE,  # Pool edges
        }
        
        return base_colors.get(tile_type, HUMID_YELLOW)
    
    def draw(self):
        self.screen.fill(BLACK)
        
        if self.game_won:
            self._draw_victory_screen()
            return
        
        # Calculate which tiles are visible on screen
        start_x = max(0, int(self.camera_x // TILE_SIZE) - 1)
        end_x = min(len(self.level_map[0]), int((self.camera_x + SCREEN_WIDTH) // TILE_SIZE) + 2)
        start_y = max(0, int(self.camera_y // TILE_SIZE) - 1)
        end_y = min(len(self.level_map), int((self.camera_y + SCREEN_HEIGHT) // TILE_SIZE) + 2)
        
        # Draw tiles
        for y in range(start_y, end_y):
            for x in range(start_x, end_x):
                # Convert world coordinates to screen coordinates
                screen_x = x * TILE_SIZE - self.camera_x
                screen_y = y * TILE_SIZE - self.camera_y
                tile_rect = pygame.Rect(screen_x, screen_y, TILE_SIZE, TILE_SIZE)
                tile_type = self.level_map[y][x]
                
                # Find room type for this tile
                room_type = None
                for room in self.rooms:
                    if (room.x <= x < room.x + room.width and
                        room.y <= y < room.y + room.height):
                        room_type = room.room_type
                        break
                
                is_visible = (x, y) in self.visible_tiles
                is_explored = (x, y) in self.explored_tiles
                
                if is_visible:
                    # Fully visible
                    color = self._get_tile_color(tile_type, room_type)
                    pygame.draw.rect(self.screen, color, tile_rect)
                elif is_explored:
                    # Explored but not currently visible (fading)
                    visibility = self.explored_tiles[(x, y)]
                    color = self._get_tile_color(tile_type, room_type)
                    # Apply fading effect
                    faded_color = tuple(int(c * visibility * 0.5) for c in color)  # Max 50% brightness when faded
                    pygame.draw.rect(self.screen, faded_color, tile_rect)
                
                # Draw tile borders for visible tiles
                if is_visible and tile_type != TileType.WALL:
                    pygame.draw.rect(self.screen, GRAY, tile_rect, 1)
                
                # Special effects for level exit
                if is_visible and tile_type == TileType.LEVEL_EXIT:
                    # Pulsing effect
                    pulse = abs(math.sin(time.time() * 3)) * 50
                    pulse_color = tuple(min(255, int(c + pulse)) for c in color)
                    pygame.draw.rect(self.screen, pulse_color, tile_rect)
        
        # Draw mysterious entity
        self.entity.draw(self.screen, self.camera_x, self.camera_y)
        
        # Draw ping effect
        if self.ping_active:
            self._draw_ping()
        
        # Draw player (convert world coordinates to screen coordinates)
        player_screen_x = int(self.player.x - self.camera_x)
        player_screen_y = int(self.player.y - self.camera_y)
        player_rect = pygame.Rect(
            player_screen_x - 8,
            player_screen_y - 8,
            16, 16
        )
        pygame.draw.rect(self.screen, GREEN, player_rect)
        
        # Draw direction indicator
        end_x = player_screen_x + math.cos(math.radians(self.player.angle)) * 20
        end_y = player_screen_y + math.sin(math.radians(self.player.angle)) * 20
        pygame.draw.line(self.screen, WHITE, 
                        (player_screen_x, player_screen_y), 
                        (int(end_x), int(end_y)), 2)
        
        # Draw UI
        self._draw_ui()
        
        pygame.display.flip()
    
    def _draw_victory_screen(self):
        """Draw the victory screen"""
        font_large = pygame.font.Font(None, 72)
        font_medium = pygame.font.Font(None, 48)
        font_small = pygame.font.Font(None, 36)
        
        # Victory text
        victory_text = font_large.render("YOU ESCAPED THE BACKROOMS!", True, GREEN)
        victory_rect = victory_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 100))
        self.screen.blit(victory_text, victory_rect)
        
        # Congratulations text
        congrats_text = font_medium.render("Congratulations on finding your way out!", True, WHITE)
        congrats_rect = congrats_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        self.screen.blit(congrats_text, congrats_rect)
        
        # Instructions to restart
        restart_text = font_small.render("Press ESC to quit or R to restart", True, FLUORESCENT_WHITE)
        restart_rect = restart_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 60))
        self.screen.blit(restart_text, restart_rect)
    
    def _draw_ping(self):
        """Draw the circular ping effect emanating from exits"""
        if not self.exit_positions:
            return
            
        for exit_x, exit_y in self.exit_positions:
            # Convert exit world coordinates to screen coordinates
            screen_exit_x = int(exit_x + TILE_SIZE // 2 - self.camera_x)
            screen_exit_y = int(exit_y + TILE_SIZE // 2 - self.camera_y)
            
            # Only draw if the center is reasonably close to screen
            if (-500 <= screen_exit_x <= SCREEN_WIDTH + 500 and 
                -500 <= screen_exit_y <= SCREEN_HEIGHT + 500):
                
                # Draw multiple concentric circles for the ping effect
                for i in range(3):
                    radius_offset = i * 25
                    current_radius = max(0, self.ping_radius - radius_offset)
                    
                    if current_radius > 5:  # Only draw if radius is meaningful
                        # Calculate alpha based on ping progress (fade out as it expands)
                        alpha = max(0, 255 - int((current_radius / self.ping_max_radius) * 255))
                        alpha = max(0, alpha - i * 50)  # Each ring is dimmer
                        
                        if alpha > 20:  # Only draw if visible enough
                            # Draw the ring directly without surface (simpler approach)
                            ring_color = (128, 0, 128)  # Purple color
                            
                            # Draw multiple thin circles to create a thick ring effect
                            for thickness in range(4):
                                radius = max(1, int(current_radius) - thickness)
                                if radius > 0:
                                    try:
                                        pygame.draw.circle(self.screen, ring_color, 
                                                         (screen_exit_x, screen_exit_y), radius, 1)
                                    except:
                                        pass  # Skip if drawing fails
    
    def _draw_ui(self):
        # Current level info
        level_name = self.current_level.value.replace('_', ' ').title()
        if self.current_level == LevelType.POOLROOMS:
            level_name = "Level 37 - The Poolrooms"
        
        # Current room info
        current_room = self._get_current_room()
        if current_room:
            room_text = f"Area: {current_room.room_type.value.replace('_', ' ').title()}"
            lighting_text = "Fluorescent Lights" if current_room.is_lit else "Dim/Broken Lights"
        else:
            room_text = "Area: Hallway"
            lighting_text = "Dim/Broken Lights"
        
        font = pygame.font.Font(None, 36)
        level_surface = font.render(f"Level: {level_name}", True, FLUORESCENT_WHITE)
        room_surface = font.render(room_text, True, FLUORESCENT_WHITE)
        lighting_surface = font.render(f"Lighting: {lighting_text}", True, FLUORESCENT_WHITE)
        
        self.screen.blit(level_surface, (10, 10))
        self.screen.blit(room_surface, (10, 50))
        self.screen.blit(lighting_surface, (10, 90))
        
        # Stamina bar
        stamina_width = 200
        stamina_height = 20
        stamina_x = SCREEN_WIDTH - stamina_width - 20
        stamina_y = 20
        
        # Background
        stamina_bg = pygame.Rect(stamina_x, stamina_y, stamina_width, stamina_height)
        pygame.draw.rect(self.screen, DARK_GRAY, stamina_bg)
        
        # Stamina fill
        stamina_fill_width = int((self.player.stamina / MAX_STAMINA) * stamina_width)
        if stamina_fill_width > 0:
            stamina_fill = pygame.Rect(stamina_x, stamina_y, stamina_fill_width, stamina_height)
            stamina_color = GREEN if self.player.stamina > 30 else YELLOW if self.player.stamina > 10 else RED
            pygame.draw.rect(self.screen, stamina_color, stamina_fill)
        
        # Stamina border
        pygame.draw.rect(self.screen, WHITE, stamina_bg, 2)
        
        # Stamina label
        small_font = pygame.font.Font(None, 24)
        stamina_label = small_font.render(f"Stamina: {int(self.player.stamina)}", True, WHITE)
        self.screen.blit(stamina_label, (stamina_x, stamina_y - 25))
        
        # Sprint indicator
        if self.player.is_sprinting:
            sprint_text = small_font.render("SPRINTING", True, YELLOW)
            self.screen.blit(sprint_text, (stamina_x, stamina_y + stamina_height + 5))
        
        # Instructions based on current level
        if self.current_level == LevelType.LEVEL_0:
            instructions = [
                "WASD/Arrow Keys: Move carefully",
                "SPACE (hold): Sprint (drains stamina)",
                "P: Ping exits (purple circles)",
                "Mouse: Aim flashlight",
                "Find the purple exit to reach the Poolrooms...",
                "Was that another person in the shadows?"
            ]
        else:  # Poolrooms
            instructions = [
                "WASD/Arrow Keys: Move carefully",
                "SPACE (hold): Sprint (drains stamina)", 
                "P: Ping exits (purple circles)",
                "Mouse: Aim flashlight",
                "Find the purple exit to escape!",
                "The humid air makes you feel uneasy..."
            ]
        
        small_font = pygame.font.Font(None, 24)
        for i, instruction in enumerate(instructions):
            text_surface = small_font.render(instruction, True, BUZZING_YELLOW)
            self.screen.blit(text_surface, (10, SCREEN_HEIGHT - 140 + i * 25))
    
    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_r and self.game_won:
                        # Restart the game
                        self.current_level = LevelType.LEVEL_0
                        self.game_won = False
                        self._init_level()
            
            self.update()
            self.draw()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()
        
