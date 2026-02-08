# ==========================================
# Block World - Alpha 0.9 (ALTAR + DROPS FIX)
# ==========================================
import pygame
import os
import random
import math
import pickle
from collections import deque

# ==========================================================
# VERSION
# ==========================================================
GAME_VERSION = "Alpha-0.9"

# ==========================================================
# CONFIG
# ==========================================================
blocksize = 32
base_cols = 25
base_rows = 15

# WORLD IS DOUBLED
world_multiplier = 30

toolbar_height = 64

screen_width = base_cols * blocksize
view_height = base_rows * blocksize
screen_height = view_height + toolbar_height

world_cols = base_cols * world_multiplier
world_rows = base_rows * world_multiplier

PLAYER_SIZE = 32
HITBOX_SIZE = 24
player_speed = 4

FPS = 60

# ==========================================================
# COMBAT
# ==========================================================
MAX_HEALTH = 10
ZOMBIE_HITBOX = 20
ZOMBIE_DAMAGE_COOLDOWN = 60
MAX_ZOMBIES_TOTAL = 35

NORMAL_ZOMBIE_SPEED_FACTOR = 0.75
HARD_ZOMBIE_SPEED_FACTOR = 0.90

NORMAL_ZOMBIE_HITS = 3
HARD_ZOMBIE_HITS = 5

NORMAL_DIRT_SPAWN = 0.20
HARD_DIRT_SPAWN = 0.25

NORMAL_HOUSE_SPAWN = 0.10
HARD_HOUSE_SPAWN = 0.25

HARD_DAMAGE_MULT = 1.5
HOUSE_RESPAWN_SECONDS = 10

# ==========================================================
# PATHFINDING
# ==========================================================
PATH_RADIUS_TILES = 28
PATH_UPDATE_FRAMES = 8

# ==========================================================
# PASSIVE HEAL (FIX: these were missing in your file)
# ==========================================================
HEAL_DELAY_FRAMES = 60 * 4      # 4 seconds after last hit
HEAL_TICK_FRAMES  = 60 * 2      # heal every 2 seconds
HEAL_AMOUNT       = 1.0         # heal 1 HP per tick

# ==========================================================
# DAY / NIGHT
# ==========================================================
DAY_SECONDS = 60
NIGHT_SECONDS = 60
DAY_FRAMES = DAY_SECONDS * FPS
NIGHT_FRAMES = NIGHT_SECONDS * FPS
CYCLE_FRAMES = DAY_FRAMES + NIGHT_FRAMES

BLOOD_MOON_CHANCE_NORMAL = 0.25
BLOOD_MOON_CHANCE_HARD = 0.30
BLOOD_MOON_DAMAGE_MULT = 1.5
BLOOD_MOON_Z_SPEED_FACTOR = 0.95

RESPAWN_IMMUNITY_SECONDS = 3.5
RESPAWN_IMMUNITY_FRAMES = int(RESPAWN_IMMUNITY_SECONDS * FPS)

# ==========================================================
# ALTAR / DROPS
# ==========================================================
CORE = 8
CORE_MINE_TIME = FPS * 10                 # 10 seconds
ALTAR_BROKEN_PAUSE_FRAMES = FPS * 5       # 5 seconds pause text
ALTAR_ZOMBIE_SPEED_MULT = 1.05            # after altar breaks

ITEM_PICKUP_RADIUS = 22                   # pickup distance

# ==========================================================
# BLOCKS
# ==========================================================
BLOCKS = {
    0: "void",
    1: "grass",
    2: "dirt",
    3: "wood",
    4: "leaves",
    5: "water",
    6: "stone",
    7: "brick",
    8: "core",   # NEW
}

VOID = 0
GRASS = 1
DIRT = 2
WOOD = 3
LEAVES = 4
WATER = 5
STONE = 6
BRICK = 7

SOLID_BLOCKS = {WOOD, LEAVES, STONE, BRICK, CORE}
DELETE = -1

# ==========================================================
# INIT
# ==========================================================
pygame.init()
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Block World")
clock = pygame.time.Clock()

font = pygame.font.SysFont(None, 24)
small_font = pygame.font.SysFont(None, 18)
title_font = pygame.font.SysFont(None, 64)
button_font = pygame.font.SysFont(None, 36)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ==========================================================
# LOAD IMAGES
# ==========================================================
block_images = {}
for bid, name in BLOCKS.items():
    p = os.path.join(BASE_DIR, f"{name}.png")
    if os.path.exists(p):
        img = pygame.image.load(p).convert_alpha()
        block_images[bid] = pygame.transform.scale(img, (blocksize, blocksize))

player_img = pygame.image.load(os.path.join(BASE_DIR, "player.png")).convert_alpha()
player_img = pygame.transform.scale(player_img, (32, 32))

player_eyeclosed_img = pygame.image.load(
    os.path.join(BASE_DIR, "player-eyeclosed.png")
).convert_alpha()
player_eyeclosed_img = pygame.transform.scale(player_eyeclosed_img, (32, 32))

# ==========================================================
# IMAGE TINTING / NIGHT VARIANTS
# ==========================================================
NIGHT_TINT = (150, 150, 150, 255)
BETTER_GRASS_TINT = (120, 180, 120, 255)

better_grass_enabled = False

def tint_image(img, tint):
    if img is None:
        return None
    s = img.copy()
    overlay = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    overlay.fill(tint)
    s.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return s

grass_normal = block_images.get(GRASS)
grass_better = tint_image(grass_normal, BETTER_GRASS_TINT) if grass_normal else None

night_block_images = {}
for bid, img in block_images.items():
    night_block_images[bid] = tint_image(img, NIGHT_TINT)

grass_better_night = tint_image(grass_better, NIGHT_TINT) if grass_better else None

def get_block_img(bid, is_night, better_grass):
    if bid == GRASS and better_grass and grass_better is not None:
        return grass_better_night if is_night else grass_better
    if is_night:
        return night_block_images.get(bid)
    return block_images.get(bid)

# ==========================================================
# WORLD GENERATION (NOW RETURNS altar tile coords)
# ==========================================================
def generate_world(preset, difficulty):
    world = [[GRASS for _ in range(world_cols)] for _ in range(world_rows)]

    def area_is_clear(top, left, height, width, pad=1):
        for r in range(top - pad, top + height + pad):
            for c in range(left - pad, left + width + pad):
                if r < 0 or c < 0 or r >= world_rows or c >= world_cols:
                    return False
                if world[r][c] != GRASS:
                    return False
        return True

    if preset != "free":
        crowded = (preset == "crowded")
        hard = (difficulty == "hard")
        structure_factor = 0.6 if (hard and not crowded) else 1.0

        lake_count = int((60 if crowded else 30) * structure_factor)
        tree_count = int((250 if crowded else 140) * structure_factor)
        house_count = int((55 if crowded else 28) * structure_factor)
        rock_vein_count = int((150 if crowded else 85) * structure_factor)
        big_tree_count = int((80 if crowded else 42) * structure_factor)
        dirt_patch_count = int((220 if crowded else 130) * structure_factor)

        # lakes
        for _ in range(lake_count):
            for _ in range(80):
                size = random.randint(3, 5)
                row = random.randint(1, world_rows - size - 2)
                col = random.randint(1, world_cols - size - 2)
                if area_is_clear(row, col, size, size, pad=2):
                    for r in range(size):
                        for c in range(size):
                            world[row + r][col + c] = WATER
                    break

        # small trees
        for _ in range(tree_count):
            attempts = 200 if crowded else 120
            for _ in range(attempts):
                row = random.randint(2, world_rows - 3)
                col = random.randint(2, world_cols - 3)
                if area_is_clear(row - 1, col - 1, 3, 3, pad=2):
                    world[row][col] = WOOD
                    world[row - 1][col] = LEAVES
                    world[row + 1][col] = LEAVES
                    world[row][col - 1] = LEAVES
                    world[row][col + 1] = LEAVES
                    break

        # houses (4x4)
        for _ in range(house_count):
            for _ in range(140):
                top = random.randint(2, world_rows - 6)
                left = random.randint(2, world_cols - 6)
                pad = 1 if crowded else 2
                if area_is_clear(top, left, 4, 4, pad=pad):
                    for r in range(top, top + 4):
                        for c in range(left, left + 4):
                            inside = (top + 1 <= r <= top + 2) and (left + 1 <= c <= left + 2)
                            world[r][c] = WOOD if inside else BRICK
                    break

        # rock veins
        for _ in range(rock_vein_count):
            for _ in range(140):
                top = random.randint(2, world_rows - 6)
                left = random.randint(2, world_cols - 6)
                pad = 1 if crowded else 2
                if area_is_clear(top, left, 4, 4, pad=pad):
                    n = random.randint(6, 12)
                    cells = [(top + r, left + c) for r in range(4) for c in range(4)]
                    random.shuffle(cells)
                    for i in range(n):
                        rr, cc = cells[i]
                        world[rr][cc] = STONE
                    break

        # big trees
        for _ in range(big_tree_count):
            for _ in range(160):
                r = random.randint(3, world_rows - 5)
                c = random.randint(3, world_cols - 5)
                top = r - 2
                left = c - 2
                pad = 1 if crowded else 2
                if area_is_clear(top, left, 6, 6, pad=pad):
                    for rr in (r, r + 1):
                        for cc in (c, c + 1):
                            world[rr][cc] = WOOD
                    for rr in range(r - 1, r + 3):
                        for cc in range(c - 1, c + 3):
                            if not (r <= rr <= r + 1 and c <= cc <= c + 1):
                                world[rr][cc] = LEAVES
                    for rr in range(r - 2, r):
                        for cc in range(c, c + 2):
                            world[rr][cc] = LEAVES
                    for rr in range(r + 2, r + 4):
                        for cc in range(c, c + 2):
                            world[rr][cc] = LEAVES
                    for rr in range(r, r + 2):
                        for cc in range(c - 2, c):
                            world[rr][cc] = LEAVES
                    for rr in range(r, r + 2):
                        for cc in range(c + 2, c + 4):
                            world[rr][cc] = LEAVES
                    break

        # dirt patches
        patch_sizes = [(1, 2), (2, 1), (2, 2), (2, 3), (3, 2)]
        for _ in range(dirt_patch_count):
            for _ in range(120):
                h, w = random.choice(patch_sizes)
                top = random.randint(2, world_rows - h - 3)
                left = random.randint(2, world_cols - w - 3)
                pad = 1 if crowded else 2
                if area_is_clear(top, left, h, w, pad=pad):
                    for rr in range(top, top + h):
                        for cc in range(left, left + w):
                            world[rr][cc] = DIRT
                    break

    # ======================================================
    # ALTAR (ALWAYS GENERATED, even on "free")
    # 5x5 brick ring, 3x3 stone ring, center CORE
    # ======================================================
    altar_r = random.randint(10, world_rows - 11)
    altar_c = random.randint(10, world_cols - 11)

    # clear a 7x7 area to grass to avoid weird overlap
    for rr in range(altar_r - 3, altar_r + 4):
        for cc in range(altar_c - 3, altar_c + 4):
            if 0 <= rr < world_rows and 0 <= cc < world_cols:
                world[rr][cc] = GRASS

    # 5x5 brick frame
    for rr in range(altar_r - 2, altar_r + 3):
        for cc in range(altar_c - 2, altar_c + 3):
            if rr in (altar_r - 2, altar_r + 2) or cc in (altar_c - 2, altar_c + 2):
                world[rr][cc] = BRICK

    # 3x3 stone ring (not center)
    for rr in range(altar_r - 1, altar_r + 2):
        for cc in range(altar_c - 1, altar_c + 2):
            if not (rr == altar_r and cc == altar_c):
                world[rr][cc] = STONE

    # center core
    world[altar_r][altar_c] = CORE

    print(f"[DEBUG] ALTAR CORE TILE = ({altar_r}, {altar_c})")

    return world, (altar_r, altar_c)
# ==========================================================
# START MENU
# ==========================================================
def start_menu():
    CENTER_X = screen_width // 2

    Y_TITLE = 120
    Y_MODE = 220
    Y_PRESET = 355
    Y_HARD = 415
    Y_START = 470

    mode_survival = pygame.Rect(CENTER_X - 160, Y_MODE, 320, 56)
    mode_creative = pygame.Rect(CENTER_X - 160, Y_MODE + 70, 320, 56)

    preset_buttons = {
        "normal":   pygame.Rect(CENTER_X - 220, Y_PRESET, 140, 48),
        "crowded":  pygame.Rect(CENTER_X - 70,  Y_PRESET, 140, 48),
        "free":     pygame.Rect(CENTER_X + 80,  Y_PRESET, 140, 48),
    }

    hard_button = pygame.Rect(CENTER_X - 120, Y_HARD, 240, 48)
    start_button = pygame.Rect(CENTER_X - 140, Y_START, 280, 60)

    selected_mode = None
    selected_preset = "normal"
    difficulty = "normal"

    def draw_button(rect, text, hovered, selected=False, text_color=(255, 255, 255), fill=(70, 70, 70)):
        color = (110, 110, 110) if hovered else fill
        pygame.draw.rect(screen, color, rect, border_radius=8)
        if selected:
            pygame.draw.rect(screen, (255, 220, 0), rect, 3, border_radius=8)
        label = button_font.render(text, True, text_color)
        screen.blit(label, label.get_rect(center=rect.center))

    while True:
        mx, my = pygame.mouse.get_pos()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                raise SystemExit
            if e.type == pygame.MOUSEBUTTONDOWN:
                if mode_survival.collidepoint(mx, my):
                    selected_mode = "survival"
                elif mode_creative.collidepoint(mx, my):
                    selected_mode = "creative"
                    difficulty = "normal"

                for name, rect in preset_buttons.items():
                    if rect.collidepoint(mx, my):
                        selected_preset = name

                if selected_mode == "survival" and hard_button.collidepoint(mx, my):
                    difficulty = "hard" if difficulty == "normal" else "normal"

                if start_button.collidepoint(mx, my) and selected_mode is not None:
                    return selected_mode, selected_preset, difficulty

        screen.fill((20, 20, 20))

        title = title_font.render(f"Block World! V: {GAME_VERSION}", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(screen_width // 2, 130)))

        draw_button(mode_survival, "Survival mode", mode_survival.collidepoint(mx, my),
                    selected=(selected_mode == "survival"))
        draw_button(mode_creative, "Creative mode", mode_creative.collidepoint(mx, my),
                    selected=(selected_mode == "creative"))

        wtxt = button_font.render("World:", True, (255, 255, 255))
        screen.blit(wtxt, (CENTER_X - 180, Y_PRESET - 40))

        for name, rect in preset_buttons.items():
            draw_button(rect, name.capitalize(), rect.collidepoint(mx, my),
                        selected=(name == selected_preset), fill=(55, 55, 55))

        if selected_mode == "survival":
            txt = f"Hard Mode: {'ON' if difficulty == 'hard' else 'OFF'}"
            color = (255, 80, 80) if difficulty == "hard" else (220, 220, 220)
            draw_button(hard_button, txt, hard_button.collidepoint(mx, my),
                        selected=(difficulty == "hard"), text_color=color, fill=(55, 55, 55))

        if selected_mode is None:
            draw_button(start_button, "Start (pick mode)", start_button.collidepoint(mx, my),
                        selected=False, text_color=(160, 160, 160), fill=(45, 45, 45))
        else:
            draw_button(start_button, "START", start_button.collidepoint(mx, my),
                        selected=False, text_color=(255, 255, 255), fill=(80, 80, 80))

        pygame.display.flip()

# ==========================================================
# TOOLBAR
# ==========================================================
def build_toolbar_slots(mode, inventory):
    ids = []
    if mode == "creative":
        for bid in sorted(BLOCKS.keys()):
            if bid != VOID:
                ids.append(bid)
    else:
        for bid in sorted(BLOCKS.keys()):
            if bid == VOID:
                continue
            if inventory.get(bid, 0) > 0:
                ids.append(bid)
    ids.append(DELETE)

    slots = []
    slot_size = 48
    slot_padding = 8
    y = view_height + 8
    for i, bid in enumerate(ids):
        x = slot_padding + i * (slot_size + slot_padding)
        rect = pygame.Rect(x, y, slot_size, slot_size)
        slots.append((rect, bid))
    return slots

def draw_toolbar(mode, slots, selected_block, inventory, mx, my):
    hovered_slot = None
    pygame.draw.rect(screen, (40, 40, 40), (0, view_height, screen_width, toolbar_height))

    for rect, bid in slots:
        if rect.collidepoint(mx, my):
            hovered_slot = rect

        if bid == DELETE:
            pygame.draw.rect(screen, (180, 50, 50), rect)
            txt = font.render("X", True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=rect.center))
        else:
            img = block_images.get(bid)
            if img:
                screen.blit(pygame.transform.scale(img, (rect.w, rect.h)), rect.topleft)

            if mode == "survival":
                cnt = inventory.get(bid, 0)
                ctext = small_font.render(str(cnt), True, (255, 255, 255))
                screen.blit(ctext, (rect.x + 4, rect.y + 4))

        if bid == selected_block:
            pygame.draw.rect(screen, (255, 255, 255), rect, 3)

        if rect == hovered_slot:
            pygame.draw.rect(screen, (255, 255, 0), rect, 2)

    return hovered_slot

# ==========================================================
# SAVES
# ==========================================================
SAVE_DIR = BASE_DIR

def save_game(slot, data):
    path = os.path.join(SAVE_DIR, f"save_slot_{slot}.dat")
    with open(path, "wb") as f:
        pickle.dump(data, f)

def load_game(slot):
    path = os.path.join(SAVE_DIR, f"save_slot_{slot}.dat")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return pickle.load(f)

def save_exists(slot):
    return os.path.exists(os.path.join(SAVE_DIR, f"save_slot_{slot}.dat"))
# ==========================================================
# -------------------- GAME LOOP ---------------------------
# ==========================================================
def run_game(mode, preset, difficulty):
    global better_grass_enabled

    hard = (difficulty == "hard")

    base_zombie_speed_factor = HARD_ZOMBIE_SPEED_FACTOR if hard else NORMAL_ZOMBIE_SPEED_FACTOR
    base_zombie_hits_to_kill = HARD_ZOMBIE_HITS if hard else NORMAL_ZOMBIE_HITS
    dirt_spawn_chance = HARD_DIRT_SPAWN if hard else NORMAL_DIRT_SPAWN
    house_spawn_chance = HARD_HOUSE_SPAWN if hard else NORMAL_HOUSE_SPAWN
    base_damage_mult = HARD_DAMAGE_MULT if hard else 1.0

    show_options_menu = False
    show_save_menu = False

    # ======================================================
    # ---------------- WORLD SETUP --------------------------
    # ======================================================
    world, altar_pos = generate_world(preset, difficulty)

    # ======================================================
    # ---------------- WORLD HELPERS ------------------------
    # ======================================================
    def get_block(r, c):
        if 0 <= r < world_rows and 0 <= c < world_cols:
            return world[r][c]
        return VOID

    def solid_at(px_, py_):
        c = int(px_ // blocksize)
        r = int(py_ // blocksize)
        bid = get_block(r, c)
        return bid == VOID or (bid in SOLID_BLOCKS)

    def find_safe_spawn(start_px, start_py, max_radius_tiles=20):
        start_r = int(start_py // blocksize)
        start_c = int(start_px // blocksize)

        for radius in range(max_radius_tiles + 1):
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    r = start_r + dr
                    c = start_c + dc
                    if 0 <= r < world_rows and 0 <= c < world_cols:
                        bid = get_block(r, c)
                        if bid != VOID and bid not in SOLID_BLOCKS:
                            x = c * blocksize + blocksize / 2
                            y = r * blocksize + blocksize / 2
                            if not solid_at(x, y):
                                return x, y
        return blocksize, blocksize

    def zombie_solid_at(x, y):
        h = ZOMBIE_HITBOX // 2 - 1
        for ox, oy in [(-h, -h), (h, -h), (-h, h), (h, h)]:
            if solid_at(x + ox, y + oy):
                return True
        return False

    def mineable(bid):
        return bid in {DIRT, WOOD, LEAVES, STONE, BRICK, CORE}

    # ======================================================
    # ---------------- PLAYER INIT --------------------------
    # ======================================================
    inventory = {bid: 0 for bid in BLOCKS.keys()}
    px = (world_cols * blocksize) // 2
    py = (world_rows * blocksize) // 2
    px, py = find_safe_spawn(px, py)

    respawn_x, respawn_y = px, py

    selected_block = DELETE if mode == "survival" else GRASS

    health = float(MAX_HEALTH)
    damage_timer = 0
    frames_since_damage = 999999
    heal_tick_timer = 0

    invuln_timer = RESPAWN_IMMUNITY_FRAMES if mode == "survival" else 0

    # altar state
    altar_broken = False
    altar_pause_timer = 0

    # DROPS (items on ground)
    dropped_items = []  # each: {"bid":id,"x":float,"y":float}

    # visuals
    blink_timer = 0
    blink_interval = 180
    blink_duration = 8
    angle = 0

    # mining
    mine_target = None
    mine_progress = 0
    mining = False
    MINE_TIME = 45

    # Day/Night cycle state
    cycle_frame = 0
    is_night = False
    blood_moon = False
    prev_is_night = False

    # UI rectangles
    options_button_rect = pygame.Rect(screen_width - 36, 8, 28, 28)
    menu_rect = pygame.Rect(screen_width - 220, 40, 200, 130)
    quit_rect = pygame.Rect(menu_rect.x + 10, menu_rect.y + 10, 180, 30)
    grass_rect = pygame.Rect(menu_rect.x + 10, menu_rect.y + 50, 180, 30)
    save_rect = pygame.Rect(menu_rect.x + 10, menu_rect.y + 90, 180, 30)

    save_menu_rect = pygame.Rect(screen_width // 2 - 180, 120, 360, 260)
    slot_rects = [pygame.Rect(save_menu_rect.x + 40, save_menu_rect.y + 60 + i * 50, 280, 40) for i in range(3)]
    back_rect = pygame.Rect(save_menu_rect.x + 100, save_menu_rect.y + 210, 160, 36)

    # ======================================================
    # -------- STRUCTURE DETECTION (PATCHES / HOUSES) -------
    # ======================================================
    def find_dirt_patches():
        seen = set()
        patches = []
        for r in range(world_rows):
            for c in range(world_cols):
                if world[r][c] != DIRT or (r, c) in seen:
                    continue
                q = deque([(r, c)])
                seen.add((r, c))
                cells = []
                while q:
                    rr, cc = q.popleft()
                    cells.append((rr, cc))
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        r2, c2 = rr + dr, cc + dc
                        if 0 <= r2 < world_rows and 0 <= c2 < world_cols:
                            if world[r2][c2] == DIRT and (r2, c2) not in seen:
                                seen.add((r2, c2))
                                q.append((r2, c2))
                if cells:
                    patches.append(cells)
        return patches

    def find_houses():
        houses_ = []
        for r in range(0, world_rows - 3):
            for c in range(0, world_cols - 3):
                ok = True
                for rr in range(r, r + 4):
                    for cc in range(c, c + 4):
                        inside = (r + 1 <= rr <= r + 2) and (c + 1 <= cc <= c + 2)
                        if inside:
                            if world[rr][cc] != WOOD:
                                ok = False
                                break
                        else:
                            if world[rr][cc] != BRICK:
                                ok = False
                                break
                    if not ok:
                        break
                if ok:
                    houses_.append((r, c))
        return houses_

    dirt_patches = find_dirt_patches()
    houses = find_houses()

    patch_spawn_cells = []
    for cells in dirt_patches:
        rs = sorted([p[0] for p in cells])
        cs = sorted([p[1] for p in cells])
        patch_spawn_cells.append((rs[len(rs) // 2], cs[len(cs) // 2]))

    house_spawn_cells = []
    for (r, c) in houses:
        candidates = [
            (r - 1, c + 1), (r - 1, c + 2),
            (r + 4, c + 1), (r + 4, c + 2),
            (r + 1, c - 1), (r + 2, c - 1),
            (r + 1, c + 4), (r + 2, c + 4),
        ]
        chosen = None
        for rr, cc in candidates:
            if 0 <= rr < world_rows and 0 <= cc < world_cols:
                bid = get_block(rr, cc)
                if bid != VOID and bid not in SOLID_BLOCKS:
                    chosen = (rr, cc)
                    break
        if chosen is None:
            chosen = (r + 1, c + 1)
        house_spawn_cells.append(chosen)

    house_wood_tiles = []
    for (r, c) in houses:
        house_wood_tiles.append([(r + 1, c + 1), (r + 1, c + 2), (r + 2, c + 1), (r + 2, c + 2)])

    def house_is_active(i):
        for rr, cc in house_wood_tiles[i]:
            if get_block(rr, cc) == WOOD:
                return True
        return False

    # ======================================================
    # -------- "SEEN CHUNKS" FOR SPAWNS ---------------------
    # ======================================================
    CHUNK_SIZE_TILES = 16
    CHUNK_VISIBILITY_MARGIN_TILES = 2
    SPAWN_CHECK_FRAMES = 20

    seen_chunks = set()

    def tile_to_chunk(tr, tc):
        return (tr // CHUNK_SIZE_TILES, tc // CHUNK_SIZE_TILES)

    def in_seen_chunk(tr, tc):
        return tile_to_chunk(tr, tc) in seen_chunks

    def mark_seen_chunks(cam_x, cam_y):
        start_col = int(cam_x // blocksize) - CHUNK_VISIBILITY_MARGIN_TILES
        start_row = int(cam_y // blocksize) - CHUNK_VISIBILITY_MARGIN_TILES
        end_col = start_col + base_cols + 3 + CHUNK_VISIBILITY_MARGIN_TILES * 2
        end_row = start_row + base_rows + 3 + CHUNK_VISIBILITY_MARGIN_TILES * 2

        start_col = max(0, start_col)
        start_row = max(0, start_row)
        end_col = min(world_cols - 1, end_col)
        end_row = min(world_rows - 1, end_row)

        c0 = start_col // CHUNK_SIZE_TILES
        c1 = end_col // CHUNK_SIZE_TILES
        r0 = start_row // CHUNK_SIZE_TILES
        r1 = end_row // CHUNK_SIZE_TILES

        for cr in range(r0, r1 + 1):
            for cc in range(c0, c1 + 1):
                seen_chunks.add((cr, cc))

    # ======================================================
    # ------------------- ZOMBIES ---------------------------
    # ======================================================
    zombies = []
    dirt_spawned = set()

    house_period_frames = int(HOUSE_RESPAWN_SECONDS * FPS)
    house_next_spawn_frame = [0 for _ in range(len(houses))]

    def spawn_zombie_at_tile(tr, tc, hp_override=None):
        if len(zombies) >= MAX_ZOMBIES_TOTAL:
            return False
        bid = get_block(tr, tc)
        if bid == VOID or bid in SOLID_BLOCKS:
            return False
        zx = tc * blocksize + blocksize / 2
        zy = tr * blocksize + blocksize / 2
        if zombie_solid_at(zx, zy):
            return False
        hp = int(base_zombie_hits_to_kill) if hp_override is None else int(hp_override)
        zombies.append({"x": float(zx), "y": float(zy), "hp": hp})
        return True

    def spawn_from_seen_sources(frame_):
        for i, (tr, tc) in enumerate(patch_spawn_cells):
            if i in dirt_spawned:
                continue
            if not in_seen_chunk(tr, tc):
                continue
            if random.random() < dirt_spawn_chance:
                spawn_zombie_at_tile(tr, tc)
            dirt_spawned.add(i)

        if blood_moon:
            return

        for i, (tr, tc) in enumerate(house_spawn_cells):
            if not in_seen_chunk(tr, tc):
                continue
            if not house_is_active(i):
                continue
            if frame_ < house_next_spawn_frame[i]:
                continue

            house_next_spawn_frame[i] = frame_ + house_period_frames
            if random.random() < house_spawn_chance:
                spawn_zombie_at_tile(tr, tc)

    # ======================================================
    # ---------------- PATHFINDING MAP ----------------------
    # ======================================================
    dist_map = {}

    def can_step(tr, tc):
        bid = get_block(tr, tc)
        return (bid != VOID) and (bid not in SOLID_BLOCKS)

    def rebuild_dist_map():
        nonlocal dist_map
        pr = int(py // blocksize)
        pc = int(px // blocksize)

        top = max(0, pr - PATH_RADIUS_TILES)
        bot = min(world_rows - 1, pr + PATH_RADIUS_TILES)
        left = max(0, pc - PATH_RADIUS_TILES)
        right = min(world_cols - 1, pc + PATH_RADIUS_TILES)

        if not can_step(pr, pc):
            dist_map = {}
            return

        q = deque()
        d = {}
        q.append((pr, pc))
        d[(pr, pc)] = 0

        neigh = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        if hard:
            neigh = neigh + [(-1, -1), (-1, 1), (1, -1), (1, 1)]

        while q:
            r, c = q.popleft()
            base = d[(r, c)]
            if base >= PATH_RADIUS_TILES * 2:
                continue

            for dr, dc in neigh:
                rr, cc = r + dr, c + dc
                if rr < top or rr > bot or cc < left or cc > right:
                    continue
                if (rr, cc) in d:
                    continue
                if not can_step(rr, cc):
                    continue

                if hard and dr != 0 and dc != 0:
                    if not can_step(r + dr, c) or not can_step(r, c + dc):
                        continue

                d[(rr, cc)] = base + 1
                q.append((rr, cc))

        dist_map = d

    last_player_axis = "x"

    def choose_next_cell(zr, zc, pr, pc):
        if not dist_map:
            return None
        if (zr, zc) not in dist_map:
            return None

        here = dist_map[(zr, zc)]
        best_cell = None
        best_dist = here

        if hard:
            neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
        else:
            if last_player_axis == "x":
                neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
            else:
                neighbors = [(0, -1), (0, 1), (-1, 0), (1, 0)]

        for dr, dc in neighbors:
            rr, cc = zr + dr, zc + dc
            if (rr, cc) not in dist_map:
                continue

            if hard and dr != 0 and dc != 0:
                if not can_step(zr + dr, zc) or not can_step(zr, zc + dc):
                    continue

            dd = dist_map[(rr, cc)]
            if dd < best_dist:
                best_dist = dd
                best_cell = (rr, cc)

        if not hard:
            axis_target = None
            if last_player_axis == "x" and zr != pr:
                cand = []
                for rr, cc in [(zr - 1, zc), (zr + 1, zc)]:
                    if (rr, cc) in dist_map and dist_map[(rr, cc)] < dist_map[(zr, zc)]:
                        cand.append((rr, cc))
                if cand:
                    cand.sort(key=lambda t: abs(t[0] - pr))
                    axis_target = cand[0]
            elif last_player_axis == "y" and zc != pc:
                cand = []
                for rr, cc in [(zr, zc - 1), (zr, zc + 1)]:
                    if (rr, cc) in dist_map and dist_map[(rr, cc)] < dist_map[(zr, zc)]:
                        cand.append((rr, cc))
                if cand:
                    cand.sort(key=lambda t: abs(t[1] - pc))
                    axis_target = cand[0]

            if axis_target is not None:
                best_cell = axis_target

        return best_cell

    # ======================================================
    # ---------------- DEATH / RESPAWN -----------------------
    # ======================================================
    def apply_death_penalty():
        for bid in list(inventory.keys()):
            if bid == VOID:
                continue
            inventory[bid] = int(inventory.get(bid, 0) // 2)

    def respawn_player():
        nonlocal px, py, health, damage_timer, frames_since_damage, heal_tick_timer, invuln_timer
        px, py = find_safe_spawn(respawn_x, respawn_y)
        health = float(MAX_HEALTH)
        damage_timer = 0
        frames_since_damage = 999999
        heal_tick_timer = 0
        invuln_timer = RESPAWN_IMMUNITY_FRAMES

    # ======================================================
    # ---------------- MAIN LOOP ----------------------------
    # ======================================================
    frame = 0
    running = True

    while running:
        clock.tick(FPS)
        frame += 1

        mx, my = pygame.mouse.get_pos()

        if altar_pause_timer > 0:
            altar_pause_timer -= 1

        paused = show_options_menu or show_save_menu or (altar_pause_timer > 0)

        # blink timer always ticks
        blink_timer += 1
        if blink_timer > blink_interval + blink_duration:
            blink_timer = 0

        # Day/Night cycle ticks only when not paused
        if mode == "survival" and (not paused):
            prev_is_night = is_night

            cycle_frame = (cycle_frame + 1) % CYCLE_FRAMES
            is_night = (cycle_frame >= DAY_FRAMES)

            if (not prev_is_night) and is_night:
                chance = BLOOD_MOON_CHANCE_HARD if hard else BLOOD_MOON_CHANCE_NORMAL
                blood_moon = (random.random() < chance)
                if blood_moon:
                    for (tr, tc) in patch_spawn_cells:
                        spawn_zombie_at_tile(tr, tc)

            if prev_is_night and (not is_night):
                blood_moon = False
                for z in zombies:
                    z["hp"] = 1

        # invulnerability timer
        if not paused and invuln_timer > 0:
            invuln_timer -= 1

        # damage cooldown / passive heal
        if not paused:
            if damage_timer > 0:
                damage_timer -= 1

            frames_since_damage += 1
            if health < MAX_HEALTH and frames_since_damage >= HEAL_DELAY_FRAMES:
                heal_tick_timer += 1
                if heal_tick_timer >= HEAL_TICK_FRAMES:
                    heal_tick_timer = 0
                    health = min(float(MAX_HEALTH), health + HEAL_AMOUNT)

        # ======================================================
        # ---------------- PLAYER MOVEMENT ----------------------
        # ======================================================
        if not paused:
            dx = dy = 0
            keys = pygame.key.get_pressed()
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                dy -= 1
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                dy += 1
            if keys[pygame.K_a] or keys[pygame.K_LEFT]:
                dx -= 1
            if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
                dx += 1

            if dx != 0 or dy != 0:
                last_player_axis = "x" if abs(dx) >= abs(dy) else "y"

            if dx or dy:
                l = math.hypot(dx, dy)
                dx /= l
                dy /= l

            nx = px + dx * player_speed
            ny = py + dy * player_speed
            h = HITBOX_SIZE // 2 - 1

            if not any(solid_at(nx + ox, py + oy) for ox, oy in [(-h, -h), (h, -h), (-h, h), (h, h)]):
                px = nx
            if not any(solid_at(px + ox, ny + oy) for ox, oy in [(-h, -h), (h, -h), (-h, h), (h, h)]):
                py = ny

        world_px_w = world_cols * blocksize
        world_px_h = world_rows * blocksize
        px = max(0, min(px, world_px_w - 1))
        py = max(0, min(py, world_px_h - 1))

        # ======================================================
        # PICK UP DROPPED ITEMS
        # ======================================================
        if not paused:
            for it in dropped_items[:]:
                if math.hypot(px - it["x"], py - it["y"]) <= ITEM_PICKUP_RADIUS:
                    inventory[it["bid"]] = inventory.get(it["bid"], 0) + 1
                    dropped_items.remove(it)

        # ======================================================
        # ---------------- CAMERA / SEEN / SPAWNS --------------
        # ======================================================
        cam_x = px - screen_width // 2
        cam_y = py - view_height // 2
        cam_x = max(-screen_width // 2, min(cam_x, world_px_w - screen_width // 2))
        cam_y = max(-view_height // 2, min(cam_y, world_px_h - view_height // 2))

        mark_seen_chunks(cam_x, cam_y)

        if mode == "survival" and (not paused) and frame % SPAWN_CHECK_FRAMES == 0:
            spawn_from_seen_sources(frame)

        # ======================================================
        # ---------------- AIM ANGLE ----------------------------
        # ======================================================
        cx = screen_width // 2
        cy = view_height // 2
        if mx != cx or my != cy:
            angle = -math.degrees(math.atan2(mx - cx, -(my - cy)))

        hovered_cell = None
        if my < view_height:
            c = int((mx + cam_x) // blocksize)
            r = int((my + cam_y) // blocksize)
            hovered_cell = (r, c)

        toolbar_slots = build_toolbar_slots(mode, inventory)

        # ======================================================
        # ---------------- ZOMBIE UPDATE ------------------------
        # ======================================================
        if mode == "survival" and (not paused):
            if frame % PATH_UPDATE_FRAMES == 0:
                rebuild_dist_map()

            speed_mult = ALTAR_ZOMBIE_SPEED_MULT if altar_broken else 1.0
            z_speed = player_speed * speed_mult * (
                BLOOD_MOON_Z_SPEED_FACTOR if (is_night and blood_moon) else base_zombie_speed_factor
            )

            pr = int(py // blocksize)
            pc = int(px // blocksize)

            for z in zombies:
                zr = int(z["y"] // blocksize)
                zc = int(z["x"] // blocksize)

                vx = px - z["x"]
                vy = py - z["y"]
                dist_to_player = math.hypot(vx, vy)
                if dist_to_player > 0:
                    vx /= dist_to_player
                    vy /= dist_to_player

                best_cell = choose_next_cell(zr, zc, pr, pc)
                if best_cell is not None:
                    tx = best_cell[1] * blocksize + blocksize / 2
                    ty = best_cell[0] * blocksize + blocksize / 2
                    mvx = tx - z["x"]
                    mvy = ty - z["y"]
                    md = math.hypot(mvx, mvy)
                    if md > 0:
                        vx = mvx / md
                        vy = mvy / md

                nxz = z["x"] + vx * z_speed
                nyz = z["y"] + vy * z_speed
                if not zombie_solid_at(nxz, z["y"]):
                    z["x"] = nxz
                if not zombie_solid_at(z["x"], nyz):
                    z["y"] = nyz

                if invuln_timer > 0:
                    continue

                dist_now = math.hypot(px - z["x"], py - z["y"])
                if dist_now < 20 and damage_timer == 0 and health > 0:
                    dmg_mult = base_damage_mult
                    if is_night and blood_moon:
                        dmg_mult *= BLOOD_MOON_DAMAGE_MULT

                    health = max(0.0, health - (1.0 * dmg_mult))
                    damage_timer = ZOMBIE_DAMAGE_COOLDOWN
                    frames_since_damage = 0
                    heal_tick_timer = 0

        # ======================================================
        # ---------------- DEATH CHECK --------------------------
        # ======================================================
        if mode == "survival" and health <= 0.0:
            apply_death_penalty()
            respawn_player()

        # ======================================================
        # ---------------- EVENTS -------------------------------
        # ======================================================
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_x:
                    selected_block = DELETE
                if pygame.K_1 <= e.key <= pygame.K_9:
                    idx = e.key - pygame.K_1
                    ids = [bid for _, bid in toolbar_slots]
                    if 0 <= idx < len(ids):
                        selected_block = ids[idx]

            if e.type == pygame.MOUSEBUTTONDOWN:
                if options_button_rect.collidepoint(mx, my):
                    show_options_menu = not show_options_menu
                    if show_options_menu:
                        show_save_menu = False
                    continue

                # -------- SAVE MENU --------
                if show_save_menu:
                    clicked_slot = None
                    for i, rect in enumerate(slot_rects):
                        if rect.collidepoint(mx, my):
                            clicked_slot = i + 1
                            break

                    if clicked_slot is not None:
                        payload = {
                            "world": world,
                            "px": px,
                            "py": py,
                            "respawn_x": respawn_x,
                            "respawn_y": respawn_y,
                            "inventory": inventory,
                            "better_grass": better_grass_enabled,
                            "mode": mode,
                            "preset": preset,
                            "difficulty": difficulty,
                            "version": GAME_VERSION,
                            "health": health,
                            "zombies": zombies,
                            "dirt_spawned": list(dirt_spawned),
                            "seen_chunks": list(seen_chunks),
                            "house_next_spawn_frame": list(house_next_spawn_frame),
                            "frames_since_damage": frames_since_damage,
                            "heal_tick_timer": heal_tick_timer,
                            "invuln_timer": invuln_timer,
                            "cycle_frame": cycle_frame,
                            "is_night": is_night,
                            "blood_moon": blood_moon,
                            "dropped_items": dropped_items,
                            "altar_pos": altar_pos,
                            "altar_broken": altar_broken,
                        }

                        if e.button == 3:
                            save_game(clicked_slot, payload)
                        else:
                            if save_exists(clicked_slot):
                                data = load_game(clicked_slot)
                                if data:
                                    world = data.get("world", world)
                                    px = float(data.get("px", px))
                                    py = float(data.get("py", py))
                                    respawn_x = float(data.get("respawn_x", respawn_x))
                                    respawn_y = float(data.get("respawn_y", respawn_y))
                                    inventory = data.get("inventory", inventory)
                                    better_grass_enabled = data.get("better_grass", better_grass_enabled)
                                    health = float(data.get("health", health))
                                    zombies = data.get("zombies", zombies)
                                    dirt_spawned = set(data.get("dirt_spawned", list(dirt_spawned)))
                                    seen_chunks = set(data.get("seen_chunks", list(seen_chunks)))
                                    house_next_spawn_frame = list(data.get("house_next_spawn_frame", house_next_spawn_frame))
                                    frames_since_damage = int(data.get("frames_since_damage", frames_since_damage))
                                    heal_tick_timer = int(data.get("heal_tick_timer", heal_tick_timer))
                                    invuln_timer = int(data.get("invuln_timer", invuln_timer))
                                    cycle_frame = int(data.get("cycle_frame", cycle_frame))
                                    is_night = bool(data.get("is_night", is_night))
                                    blood_moon = bool(data.get("blood_moon", blood_moon))
                                    dropped_items = data.get("dropped_items", [])
                                    altar_pos = tuple(data.get("altar_pos", altar_pos))
                                    altar_broken = bool(data.get("altar_broken", altar_broken))
                                    dist_map = {}
                                    selected_block = DELETE if mode == "survival" else GRASS
                            else:
                                save_game(clicked_slot, payload)

                        show_save_menu = False
                        continue

                    if back_rect.collidepoint(mx, my):
                        show_save_menu = False
                        continue

                    continue

                # -------- OPTIONS MENU --------
                if show_options_menu:
                    if quit_rect.collidepoint(mx, my):
                        show_options_menu = False
                        return
                    if grass_rect.collidepoint(mx, my):
                        better_grass_enabled = not better_grass_enabled
                        show_options_menu = False
                        continue
                    if save_rect.collidepoint(mx, my):
                        show_save_menu = True
                        show_options_menu = False
                        continue
                    continue

                if paused:
                    continue

                # -------- zombie attack (LMB) --------
                attacked = False
                if mode == "survival" and e.button == 1 and my < view_height:
                    mxw = mx + cam_x
                    myw = my + cam_y
                    for z in zombies[:]:
                        if math.hypot(z["x"] - mxw, z["y"] - myw) < 24:
                            z["hp"] -= 1
                            if z["hp"] <= 0:
                                zombies.remove(z)
                            attacked = True
                            break
                if attacked:
                    continue

                # -------- toolbar click --------
                if my >= view_height:
                    for rect, bid in toolbar_slots:
                        if rect.collidepoint(mx, my):
                            selected_block = bid
                            break
                    continue

                # -------- world click --------
                if hovered_cell:
                    r, c = hovered_cell
                    bid = get_block(r, c)
                    if bid == VOID:
                        continue

                    if mode == "creative":
                        if selected_block == DELETE:
                            world[r][c] = GRASS
                        else:
                            world[r][c] = selected_block
                    else:
                        # survival place (RMB) - only place onto GRASS
                        if pygame.mouse.get_pressed()[2]:
                            if selected_block != DELETE and inventory.get(selected_block, 0) > 0:
                                if bid == GRASS:
                                    world[r][c] = selected_block
                                    inventory[selected_block] -= 1

                        # survival mine (LMB)
                        if e.button == 1:
                            if mineable(bid):
                                mine_target = (r, c)
                                mine_progress = 0
                                mining = True

            if e.type == pygame.MOUSEBUTTONUP:
                if e.button == 1:
                    mining = False
                    mine_target = None
                    mine_progress = 0

        # ======================================================
        # ---------------- MINING (HOLD) ------------------------
        # ======================================================
        if (not paused) and mode == "survival" and mining and mine_target and pygame.mouse.get_pressed()[0]:
            r, c = mine_target
            if hovered_cell != mine_target:
                mining = False
                mine_target = None
                mine_progress = 0
            else:
                bid = get_block(r, c)
                if bid == VOID or (not mineable(bid)):
                    mining = False
                    mine_target = None
                    mine_progress = 0
                else:
                    mine_progress += 1
                    need = CORE_MINE_TIME if bid == CORE else MINE_TIME
                    if mine_progress >= need:
                        # DROP ITEM (not instant inventory)
                        drop_x = c * blocksize + blocksize / 2
                        drop_y = r * blocksize + blocksize / 2
                        dropped_items.append({"bid": bid, "x": float(drop_x), "y": float(drop_y)})

                        # altar break trigger
                        if bid == CORE and (not altar_broken):
                            altar_broken = True
                            altar_pause_timer = ALTAR_BROKEN_PAUSE_FRAMES
                            print("[DEBUG] ALTAR BROKEN!")

                        world[r][c] = GRASS
                        mine_progress = 0
                        mining = False
                        mine_target = None
        # ======================================================
        # ---------------- RENDER -------------------------------
        # ======================================================
        start_col = int(cam_x // blocksize)
        start_row = int(cam_y // blocksize)
        end_col = start_col + base_cols + 3
        end_row = start_row + base_rows + 3

        screen.fill((0, 0, 0))

        # world
        for rr in range(start_row, end_row):
            for cc in range(start_col, end_col):
                bid = get_block(rr, cc)
                img = get_block_img(bid, (mode == "survival" and is_night), better_grass_enabled)
                if img:
                    screen.blit(img, (cc * blocksize - cam_x, rr * blocksize - cam_y))

        # DROPS (draw after world, before player)
        for it in dropped_items:
            img = block_images.get(it["bid"])
            if img:
                screen.blit(
                    img,
                    (it["x"] - cam_x - blocksize / 2, it["y"] - cam_y - blocksize / 2)
                )

        # zombies
        if mode == "survival":
            for z in zombies:
                sx = z["x"] - cam_x
                sy = z["y"] - cam_y
                body_col = (180, 40, 40) if (is_night and blood_moon) else (40, 180, 40)
                pygame.draw.rect(screen, body_col, (sx - 12, sy - 12, 24, 24))
                pygame.draw.rect(screen, (0, 0, 0), (sx - 12, sy - 18, 24, 4))
                hpw = int(24 * max(0.0, z["hp"]) / float(max(1, HARD_ZOMBIE_HITS if hard else NORMAL_ZOMBIE_HITS)))
                pygame.draw.rect(screen, (255, 0, 0), (sx - 12, sy - 18, hpw, 4))

        # hover highlight
        if hovered_cell:
            rr, cc = hovered_cell
            pygame.draw.rect(
                screen, (255, 255, 0),
                (cc * blocksize - cam_x, rr * blocksize - cam_y, blocksize, blocksize),
                2
            )

        # mining bar
        if mode == "survival" and mining:
            bid = get_block(mine_target[0], mine_target[1]) if mine_target else None
            need = CORE_MINE_TIME if bid == CORE else MINE_TIME
            bar_w = 220
            bar_h = 16
            x = screen_width // 2 - bar_w // 2
            y = view_height - 26
            pygame.draw.rect(screen, (120, 120, 120), (x, y, bar_w, bar_h))
            fill = int(bar_w * (mine_progress / max(1, need)))
            pygame.draw.rect(screen, (255, 220, 0), (x, y, fill, bar_h))

        # player sprite (blink)
        base_img = player_eyeclosed_img if (blink_interval <= blink_timer < blink_interval + blink_duration) else player_img
        rot = pygame.transform.rotate(base_img, angle)
        screen.blit(rot, rot.get_rect(center=(cx, cy)))

        # invulnerability shield
        if mode == "survival" and invuln_timer > 0:
            pulse = 6 + int(4 * math.sin(frame * 0.25))
            pygame.draw.circle(screen, (255, 255, 0), (cx, cy), 22 + pulse, 2)

        # health bar
        if mode == "survival":
            bar_x = 12
            bar_y = 12
            bar_w = 140
            bar_h = 16
            pygame.draw.rect(screen, (40, 40, 40), (bar_x - 2, bar_y - 2, bar_w + 4, bar_h + 4))
            pygame.draw.rect(screen, (120, 0, 0), (bar_x, bar_y, bar_w, bar_h))
            fill = int(bar_w * (max(0.0, health) / float(MAX_HEALTH)))
            pygame.draw.rect(screen, (220, 40, 40), (bar_x, bar_y, fill, bar_h))
            hp_label = small_font.render("HP", True, (255, 255, 255))
            screen.blit(hp_label, (bar_x, bar_y - 16))

            if cycle_frame < DAY_FRAMES:
                t = DAY_FRAMES - cycle_frame
                phase = "DAY"
            else:
                t = CYCLE_FRAMES - cycle_frame
                phase = "NIGHT"
            secs_left = int(t / FPS)
            info = f"{phase} {secs_left:02d}s"
            if is_night and blood_moon:
                info += "  BLOOD MOON!"
            if altar_broken:
                info += "  ALTAR BROKEN!"
            info_txt = small_font.render(info, True, (255, 255, 255))
            screen.blit(info_txt, (bar_x, bar_y + 24))

        # options button
        pygame.draw.rect(screen, (60, 60, 60), options_button_rect, border_radius=6)
        dots = font.render("⋮", True, (255, 255, 255))
        screen.blit(dots, dots.get_rect(center=options_button_rect.center))

        # altar broken pause text
        if altar_pause_timer > 0:
            txt = title_font.render("ALTAR BROKEN", True, (255, 60, 60))
            screen.blit(txt, txt.get_rect(center=(screen_width // 2, view_height // 2)))

        # paused overlay text (menus)
        if (show_options_menu or show_save_menu):
            overlay = font.render("Menu open, world paused", True, (255, 255, 255))
            screen.blit(overlay, overlay.get_rect(center=(screen_width // 2, view_height // 2)))

        # options menu
        if show_options_menu:
            pygame.draw.rect(screen, (30, 30, 30), menu_rect, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255), menu_rect, 2, border_radius=8)

            for rect in [quit_rect, grass_rect, save_rect]:
                pygame.draw.rect(screen, (60, 60, 60), rect)
                if rect.collidepoint(mx, my):
                    pygame.draw.rect(screen, (255, 255, 0), rect, 2)

            qtxt = font.render("Quit & New Game", True, (255, 255, 255))
            gtxt = font.render(
                f"Better Grass: {'ON' if better_grass_enabled else 'OFF'}",
                True,
                (255, 220, 0) if better_grass_enabled else (200, 200, 200),
            )
            stxt = font.render("Save / Load", True, (255, 255, 255))

            screen.blit(qtxt, qtxt.get_rect(center=quit_rect.center))
            screen.blit(gtxt, gtxt.get_rect(center=grass_rect.center))
            screen.blit(stxt, stxt.get_rect(center=save_rect.center))

        # save menu
        if show_save_menu:
            pygame.draw.rect(screen, (25, 25, 25), save_menu_rect, border_radius=10)
            pygame.draw.rect(screen, (255, 255, 255), save_menu_rect, 2, border_radius=10)

            title = font.render("Save / Load", True, (255, 255, 255))
            screen.blit(title, title.get_rect(center=(save_menu_rect.centerx, save_menu_rect.y + 25)))

            for i, rect in enumerate(slot_rects):
                exists = save_exists(i + 1)
                pygame.draw.rect(screen, (60, 60, 60), rect)
                label = f"Slot {i + 1} : {'Saved' if exists else 'Empty'}"
                txt = font.render(label, True, (255, 255, 255))
                screen.blit(txt, txt.get_rect(center=rect.center))
                if rect.collidepoint(mx, my):
                    pygame.draw.rect(screen, (255, 255, 0), rect, 2)

            hint = small_font.render("Left Click: Load/Save    Right Click: Overwrite", True, (200, 200, 200))
            screen.blit(hint, (save_menu_rect.x + 40, save_menu_rect.y + 185))

            pygame.draw.rect(screen, (80, 80, 80), back_rect)
            if back_rect.collidepoint(mx, my):
                pygame.draw.rect(screen, (255, 255, 0), back_rect, 2)
            btxt = font.render("Back", True, (255, 255, 255))
            screen.blit(btxt, btxt.get_rect(center=back_rect.center))

        # toolbar
        draw_toolbar(mode, toolbar_slots, selected_block, inventory, mx, my)

        pygame.display.flip()

# ==========================================================
# ENTRY
# ==========================================================
while True:
    mode, preset, difficulty = start_menu()
    run_game(mode, preset, difficulty)

pygame.quit()
