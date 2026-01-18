import pygame
import os
import random
import math
import pickle

# ---------- VERSION ----------
GAME_VERSION = "Alpha-0.25"

# ---------- CONFIG ----------
blocksize = 32
base_cols = 25
base_rows = 15
world_multiplier = 15
toolbar_height = 64

screen_width = base_cols * blocksize
view_height = base_rows * blocksize
screen_height = view_height + toolbar_height

world_cols = base_cols * world_multiplier
world_rows = base_rows * world_multiplier

player_speed = 4
PLAYER_SIZE = 32
HITBOX_SIZE = 24

# ---------- OPTIONS ----------
better_grass_enabled = False
show_options_menu = False
show_save_menu = False

# ---------- BLOCK DEFINITIONS ----------
BLOCKS = {
    0: "void",
    1: "grass",
    2: "dirt",
    3: "wood",
    4: "leaves",
    5: "water",
    6: "stone",
    7: "brick",
}

GRASS = 1
DIRT = 2
WOOD = 3
LEAVES = 4
WATER = 5
STONE = 6
BRICK = 7

SOLID_BLOCKS = {WOOD, LEAVES, STONE, BRICK}
DELETE = -1

# ---------- INIT ----------
pygame.init()
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Block World")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
small_font = pygame.font.SysFont(None, 18)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- LOAD IMAGES ----------
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

def tint_image(img, tint):
    s = img.copy()
    overlay = pygame.Surface(s.get_size(), pygame.SRCALPHA)
    overlay.fill(tint)
    s.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return s

grass_normal = block_images.get(GRASS)
grass_dark = tint_image(grass_normal, (120, 180, 120, 255)) if grass_normal else None

# ---------- WORLD GENERATION ----------
def generate_world(preset):
    world = [[GRASS for _ in range(world_cols)] for _ in range(world_rows)]

    def area_is_clear(top, left, height, width, pad=1):
        for r in range(top - pad, top + height + pad):
            for c in range(left - pad, left + width + pad):
                if r < 0 or c < 0 or r >= world_rows or c >= world_cols:
                    return False
                if world[r][c] != GRASS:
                    return False
        return True

    if preset == "free":
        return world

    crowded = (preset == "crowded")

    lake_count = 60 if crowded else 30
    tree_count = 250 if crowded else 140

    house_count = 55 if crowded else 28
    rock_vein_count = 150 if crowded else 85
    big_tree_count = 80 if crowded else 42
    dirt_patch_count = 220 if crowded else 130

    # ---------- LAKES (FIRST) ----------
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

    # ---------- SMALL TREES ----------
    for _ in range(tree_count):
        for _ in range(120):
            row = random.randint(2, world_rows - 3)
            col = random.randint(2, world_cols - 3)
            min_r = row - 1
            min_c = col - 1
            if area_is_clear(min_r, min_c, 3, 3, pad=2):
                world[row][col] = WOOD
                world[row - 1][col] = LEAVES
                world[row + 1][col] = LEAVES
                world[row][col - 1] = LEAVES
                world[row][col + 1] = LEAVES
                break

    # ---------- HOUSES (2x2 WOOD, 1-TILE BRICK RING) ----------
    # footprint is 4x4 (brick border), centered wood 2x2
    for _ in range(house_count):
        for _ in range(140):
            r0 = random.randint(2, world_rows - 6)
            c0 = random.randint(2, world_cols - 6)
            top = r0
            left = c0
            if area_is_clear(top, left, 4, 4, pad=2):
                for r in range(top, top + 4):
                    for c in range(left, left + 4):
                        if (top + 1 <= r <= top + 2) and (left + 1 <= c <= left + 2):
                            world[r][c] = WOOD
                        else:
                            world[r][c] = BRICK
                break

    # ---------- ROCK VEINS (RANDOM STONE IN 4x4) ----------
    for _ in range(rock_vein_count):
        for _ in range(140):
            top = random.randint(2, world_rows - 6)
            left = random.randint(2, world_cols - 6)
            if area_is_clear(top, left, 4, 4, pad=2):
                n = random.randint(6, 12)
                cells = [(top + r, left + c) for r in range(4) for c in range(4)]
                random.shuffle(cells)
                for i in range(n):
                    rr, cc = cells[i]
                    world[rr][cc] = STONE
                break

    # ---------- BIG TREES (2x2 WOOD + LEAF LAYER + 2x2 LEAF ON EACH SIDE) ----------
    # footprint is 6x6: rows r-2..r+3, cols c-2..c+3 where (r,c) is trunk top-left
    for _ in range(big_tree_count):
        for _ in range(160):
            r = random.randint(3, world_rows - 5)
            c = random.randint(3, world_cols - 5)
            top = r - 2
            left = c - 2
            if area_is_clear(top, left, 6, 6, pad=2):
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

    # ---------- DIRT PATCHES (VARIOUS SIZES) ----------
    patch_sizes = [(1, 2), (2, 1), (2, 2), (2, 3), (3, 2)]
    for _ in range(dirt_patch_count):
        for _ in range(120):
            h, w = random.choice(patch_sizes)
            top = random.randint(2, world_rows - h - 3)
            left = random.randint(2, world_cols - w - 3)
            if area_is_clear(top, left, h, w, pad=2):
                for rr in range(top, top + h):
                    for cc in range(left, left + w):
                        world[rr][cc] = DIRT
                break

    return world

# ---------- START MENU ----------
def start_menu():
    title_font = pygame.font.SysFont(None, 64)
    button_font = pygame.font.SysFont(None, 36)

    mode_survival = pygame.Rect(screen_width // 2 - 160, 240, 320, 60)
    mode_creative = pygame.Rect(screen_width // 2 - 160, 320, 320, 60)

    preset_normal = pygame.Rect(screen_width // 2 - 220, 420, 140, 52)
    preset_crowded = pygame.Rect(screen_width // 2 - 70, 420, 140, 52)
    preset_free = pygame.Rect(screen_width // 2 + 80, 420, 140, 52)

    selected_mode = None
    selected_preset = "normal"

    while True:
        mx, my = pygame.mouse.get_pos()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                exit()
            if e.type == pygame.MOUSEBUTTONDOWN:
                if mode_survival.collidepoint(mx, my):
                    selected_mode = "survival"
                if mode_creative.collidepoint(mx, my):
                    selected_mode = "creative"
                if preset_normal.collidepoint(mx, my):
                    selected_preset = "normal"
                if preset_crowded.collidepoint(mx, my):
                    selected_preset = "crowded"
                if preset_free.collidepoint(mx, my):
                    selected_preset = "free"
                if selected_mode is not None:
                    if mode_survival.collidepoint(mx, my) or mode_creative.collidepoint(mx, my):
                        return selected_mode, selected_preset

        screen.fill((20, 20, 20))

        title = title_font.render(f"Block World! V: {GAME_VERSION}", True, (255, 255, 255))
        screen.blit(title, title.get_rect(center=(screen_width // 2, 140)))

        play = button_font.render("Play:", True, (255, 255, 255))
        screen.blit(play, (screen_width // 2 - 160, 200))

        pygame.draw.rect(screen, (60, 60, 60), mode_survival)
        pygame.draw.rect(screen, (60, 60, 60), mode_creative)

        if mode_survival.collidepoint(mx, my):
            pygame.draw.rect(screen, (255, 255, 255), mode_survival, 3)
        if mode_creative.collidepoint(mx, my):
            pygame.draw.rect(screen, (255, 255, 255), mode_creative, 3)

        t1 = button_font.render("Survival mode", True, (255, 255, 255))
        t2 = button_font.render("Creative mode", True, (255, 255, 255))
        screen.blit(t1, t1.get_rect(center=mode_survival.center))
        screen.blit(t2, t2.get_rect(center=mode_creative.center))

        wtxt = button_font.render("World:", True, (255, 255, 255))
        screen.blit(wtxt, (screen_width // 2 - 160, 392))

        for rect, name in [(preset_normal, "Normal"), (preset_crowded, "Crowded"), (preset_free, "Free")]:
            pygame.draw.rect(screen, (60, 60, 60), rect)
            if rect.collidepoint(mx, my):
                pygame.draw.rect(screen, (255, 255, 255), rect, 3)
            if name.lower() == selected_preset:
                pygame.draw.rect(screen, (255, 255, 0), rect, 3)
            lab = small_font.render(name, True, (255, 255, 255))
            screen.blit(lab, lab.get_rect(center=rect.center))

        pygame.display.flip()

# ---------- TOOLBAR ----------
def build_toolbar_slots(mode, inventory):
    ids = []
    if mode == "creative":
        for bid in sorted(BLOCKS.keys()):
            if bid != 0:
                ids.append(bid)
    else:
        for bid in sorted(BLOCKS.keys()):
            if bid == 0:
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

# ---------- SAVES ----------
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

# ---------- GAME ----------
def run_game(mode, preset):
    global better_grass_enabled, show_options_menu, show_save_menu

    world = generate_world(preset)

    inventory = {bid: 0 for bid in BLOCKS.keys()}
    px = (world_cols * blocksize) // 2
    py = (world_rows * blocksize) // 2

    selected_block = DELETE if mode == "survival" else GRASS

    def get_block(r, c):
        if 0 <= r < world_rows and 0 <= c < world_cols:
            return world[r][c]
        return 0

    blink_timer = 0
    blink_interval = 180
    blink_duration = 8

    angle = 0

    mine_target = None
    mine_progress = 0
    mining = False
    MINE_TIME = 45

    options_button_rect = pygame.Rect(screen_width - 36, 8, 28, 28)
    menu_rect = pygame.Rect(screen_width - 220, 40, 200, 130)
    quit_rect = pygame.Rect(menu_rect.x + 10, menu_rect.y + 10, 180, 30)
    grass_rect = pygame.Rect(menu_rect.x + 10, menu_rect.y + 50, 180, 30)
    save_rect = pygame.Rect(menu_rect.x + 10, menu_rect.y + 90, 180, 30)

    save_menu_rect = pygame.Rect(screen_width // 2 - 180, 120, 360, 260)
    slot_rects = [pygame.Rect(save_menu_rect.x + 40, save_menu_rect.y + 60 + i * 50, 280, 40) for i in range(3)]
    back_rect = pygame.Rect(save_menu_rect.x + 100, save_menu_rect.y + 210, 160, 36)

    def solid_at(px_, py_):
        c = int(px_ // blocksize)
        r = int(py_ // blocksize)
        bid = get_block(r, c)
        return bid == 0 or (bid in SOLID_BLOCKS)

    def mineable(bid):
        return bid in {GRASS, DIRT, WOOD, LEAVES}

    running = True
    while running:
        clock.tick(60)
        blink_timer += 1
        if blink_timer > blink_interval + blink_duration:
            blink_timer = 0

        mx, my = pygame.mouse.get_pos()

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

        cam_x = px - screen_width // 2
        cam_y = py - view_height // 2
        cam_x = max(-screen_width // 2, min(cam_x, world_px_w - screen_width // 2))
        cam_y = max(-view_height // 2, min(cam_y, world_px_h - view_height // 2))

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
                    show_save_menu = False
                    continue

                if show_save_menu:
                    clicked_slot = None
                    for i, rect in enumerate(slot_rects):
                        if rect.collidepoint(mx, my):
                            clicked_slot = i + 1
                            break

                    if clicked_slot is not None:
                        if e.button == 3:
                            save_game(clicked_slot, {
                                "world": world,
                                "px": px,
                                "py": py,
                                "inventory": inventory,
                                "better_grass": better_grass_enabled,
                                "mode": mode,
                                "preset": preset,
                                "version": GAME_VERSION,
                            })
                        else:
                            if save_exists(clicked_slot):
                                data = load_game(clicked_slot)
                                if data:
                                    world = data.get("world", world)
                                    px = data.get("px", px)
                                    py = data.get("py", py)
                                    inventory = data.get("inventory", inventory)
                                    better_grass_enabled = data.get("better_grass", better_grass_enabled)
                                    selected_block = DELETE if mode == "survival" else GRASS
                            else:
                                save_game(clicked_slot, {
                                    "world": world,
                                    "px": px,
                                    "py": py,
                                    "inventory": inventory,
                                    "better_grass": better_grass_enabled,
                                    "mode": mode,
                                    "preset": preset,
                                    "version": GAME_VERSION,
                                })
                        show_save_menu = False
                        continue

                    if back_rect.collidepoint(mx, my):
                        show_save_menu = False
                        continue

                    continue

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

                if my >= view_height:
                    for rect, bid in toolbar_slots:
                        if rect.collidepoint(mx, my):
                            selected_block = bid
                            break
                else:
                    if hovered_cell:
                        r, c = hovered_cell
                        bid = get_block(r, c)

                        if bid == 0:
                            continue

                        if mode == "creative":
                            if selected_block == DELETE:
                                if 0 <= r < world_rows and 0 <= c < world_cols:
                                    world[r][c] = GRASS
                            else:
                                if 0 <= r < world_rows and 0 <= c < world_cols:
                                    world[r][c] = selected_block
                        else:
                            if pygame.mouse.get_pressed()[2]:
                                if selected_block != DELETE and inventory.get(selected_block, 0) > 0:
                                    if get_block(r, c) == GRASS or get_block(r, c) == WATER:
                                        if 0 <= r < world_rows and 0 <= c < world_cols:
                                            world[r][c] = selected_block
                                            inventory[selected_block] -= 1
                            if e.button == 1:
                                if mineable(bid) and bid != GRASS and bid != WATER:
                                    mine_target = (r, c)
                                    mine_progress = 0
                                    mining = True

            if e.type == pygame.MOUSEBUTTONUP:
                if e.button == 1:
                    mining = False
                    mine_target = None
                    mine_progress = 0

        if mode == "survival" and mining and mine_target and pygame.mouse.get_pressed()[0]:
            r, c = mine_target
            if hovered_cell != mine_target:
                mining = False
                mine_target = None
                mine_progress = 0
            else:
                bid = get_block(r, c)
                if bid == 0 or not mineable(bid) or bid in {GRASS, WATER}:
                    mining = False
                    mine_target = None
                    mine_progress = 0
                else:
                    mine_progress += 1
                    if mine_progress >= MINE_TIME:
                        if bid == GRASS:
                            inventory[DIRT] += 1
                        else:
                            inventory[bid] = inventory.get(bid, 0) + 1

                        if 0 <= r < world_rows and 0 <= c < world_cols:
                            world[r][c] = GRASS
                        mine_progress = 0
                        mining = False
                        mine_target = None

        start_col = int(cam_x // blocksize)
        start_row = int(cam_y // blocksize)
        end_col = start_col + base_cols + 3
        end_row = start_row + base_rows + 3

        screen.fill((0, 0, 0))

        for r in range(start_row, end_row):
            for c in range(start_col, end_col):
                bid = get_block(r, c)
                if bid == GRASS and better_grass_enabled and grass_dark:
                    img = grass_dark
                else:
                    img = block_images.get(bid)
                if img:
                    screen.blit(img, (c * blocksize - cam_x, r * blocksize - cam_y))

        if hovered_cell:
            r, c = hovered_cell
            pygame.draw.rect(
                screen,
                (255, 255, 0),
                (c * blocksize - cam_x, r * blocksize - cam_y, blocksize, blocksize),
                2,
            )

        if mode == "survival" and mining:
            bar_w = 220
            bar_h = 16
            x = screen_width // 2 - bar_w // 2
            y = view_height - 26
            pygame.draw.rect(screen, (120, 120, 120), (x, y, bar_w, bar_h))
            fill = int(bar_w * (mine_progress / MINE_TIME))
            pygame.draw.rect(screen, (255, 220, 0), (x, y, fill, bar_h))

        if blink_interval <= blink_timer < blink_interval + blink_duration:
            base_img = player_eyeclosed_img
        else:
            base_img = player_img

        rot = pygame.transform.rotate(base_img, angle)
        screen.blit(rot, rot.get_rect(center=(cx, cy)))

        pygame.draw.rect(screen, (60, 60, 60), options_button_rect, border_radius=6)
        dots = font.render("⋮", True, (255, 255, 255))
        screen.blit(dots, dots.get_rect(center=options_button_rect.center))

        if show_options_menu:
            pygame.draw.rect(screen, (30, 30, 30), menu_rect, border_radius=8)
            pygame.draw.rect(screen, (255, 255, 255), menu_rect, 2, border_radius=8)

            pygame.draw.rect(screen, (60, 60, 60), quit_rect)
            pygame.draw.rect(screen, (60, 60, 60), grass_rect)
            pygame.draw.rect(screen, (60, 60, 60), save_rect)

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

            hint = small_font.render(
                "Left Click: Load / Save    Right Click: Overwrite Save",
                True,
                (200, 200, 200),
            )
            screen.blit(hint, (save_menu_rect.x + 40, save_menu_rect.y + 185))

            pygame.draw.rect(screen, (80, 80, 80), back_rect)
            btxt = font.render("Back", True, (255, 255, 255))
            screen.blit(btxt, btxt.get_rect(center=back_rect.center))

        draw_toolbar(mode, toolbar_slots, selected_block, inventory, mx, my)

        pygame.display.flip()

# ---------- ENTRY ----------
while True:
    mode, preset = start_menu()
    run_game(mode, preset)

pygame.quit()
