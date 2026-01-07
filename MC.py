import pygame
import os
import random
import math

# ---------- CONFIG ----------
blocksize = 32
base_cols = 25
base_rows = 15
world_multiplier = 15
toolbar_height = 64

screen_width = base_cols * blocksize
screen_height = base_rows * blocksize + toolbar_height

world_cols = base_cols * world_multiplier
world_rows = base_rows * world_multiplier

player_speed = 4

# ---------- BLOCK DEFINITIONS ----------
BLOCKS = {
    1: "grass",
    3: "wood",
    4: "leaves",
    5: "water",
    6: "stone",
    7: "brick",
}
GRASS = 1
WOOD = 3
LEAVES = 4
WATER = 5
SOLID_BLOCKS = {WOOD, LEAVES, 6, 7}
PLAYER_SIZE = 32
HITBOX_SIZE = 24
DELETE = -1
selected_block = GRASS



# ---------- INIT ----------
pygame.init()
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("BlockWorld")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- LOAD IMAGES ----------
block_images = {}
for block_id, name in BLOCKS.items():
    img = pygame.image.load(os.path.join(BASE_DIR, f"{name}.png")).convert_alpha()
    img = pygame.transform.scale(img, (blocksize, blocksize))
    block_images[block_id] = img

player_img_original = pygame.image.load(os.path.join(BASE_DIR, "player.png")).convert_alpha()
player_img_original = pygame.transform.scale(player_img_original, (32, 32))

# ---------- WORLD GENERATION ----------
world = [[GRASS for _ in range(world_cols)] for _ in range(world_rows)]

def area_is_clear(top, left, height, width):
    for r in range(top - 1, top + height + 1):
        for c in range(left - 1, left + width + 1):
            if r < 0 or c < 0 or r >= world_rows or c >= world_cols:
                return False
            if world[r][c] != GRASS:
                return False
    return True

for _ in range(80):
    for _ in range(80):
        size = random.randint(3, 5)
        row = random.randint(1, world_rows - size - 1)
        col = random.randint(1, world_cols - size - 1)
        if area_is_clear(row, col, size, size):
            for r in range(size):
                for c in range(size):
                    world[row + r][col + c] = WATER
            break

for _ in range(250):
    for _ in range(120):
        row = random.randint(2, world_rows - 3)
        col = random.randint(2, world_cols - 3)
        footprint = [
            (row, col),
            (row - 1, col),
            (row + 1, col),
            (row, col - 1),
            (row, col + 1),
        ]
        min_r = min(r for r, _ in footprint)
        max_r = max(r for r, _ in footprint)
        min_c = min(c for _, c in footprint)
        max_c = max(c for _, c in footprint)
        if area_is_clear(min_r, min_c, max_r - min_r + 1, max_c - min_c + 1):
            world[row][col] = WOOD
            world[row - 1][col] = LEAVES
            world[row + 1][col] = LEAVES
            world[row][col - 1] = LEAVES
            world[row][col + 1] = LEAVES
            break
def is_solid_at(px, py):
    col = int(px // blocksize)
    row = int(py // blocksize)
    if 0 <= row < world_rows and 0 <= col < world_cols:
        return world[row][col] in SOLID_BLOCKS
    return True

# ---------- TOOLBAR ----------
toolbar_slots = []
slot_size = 48
slot_padding = 8
toolbar_y = base_rows * blocksize + 8

for i, block_id in enumerate(list(BLOCKS.keys()) + [DELETE]):
    x = slot_padding + i * (slot_size + slot_padding)
    rect = pygame.Rect(x, toolbar_y, slot_size, slot_size)
    toolbar_slots.append((rect, block_id))

# ---------- PLAYER ----------
player_x = (world_cols * blocksize) // 2
player_y = (world_rows * blocksize) // 2
player_angle = 0

# ---------- MAIN LOOP ----------
running = True
while running:
    clock.tick(60)

    hovered_slot = None
    hovered_cell = None

    mx, my = pygame.mouse.get_pos()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:
            if pygame.K_1 <= event.key <= pygame.K_9:
                key_id = event.key - pygame.K_1
                if key_id in BLOCKS:
                    selected_block = key_id
            if event.key == pygame.K_x:
                selected_block = DELETE

        if event.type == pygame.MOUSEBUTTONDOWN:
            if my >= base_rows * blocksize:
                for rect, block_id in toolbar_slots:
                    if rect.collidepoint(mx, my):
                        selected_block = block_id
                        break
            else:
                col = int((mx + cam_x) // blocksize)
                row = int((my + cam_y) // blocksize)
                if 0 <= row < world_rows and 0 <= col < world_cols:
                    world[row][col] = GRASS if selected_block == DELETE else selected_block

    keys = pygame.key.get_pressed()
    dx = dy = 0
    if keys[pygame.K_w] or keys[pygame.K_UP]:
        dy -= 1
    if keys[pygame.K_s] or keys[pygame.K_DOWN]:
        dy += 1
    if keys[pygame.K_a] or keys[pygame.K_LEFT]:
        dx -= 1
    if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
        dx += 1

    if dx or dy:
        length = math.hypot(dx, dy)
        dx /= length
        dy /= length

    next_x = player_x + dx * player_speed
    next_y = player_y + dy * player_speed

    half = HITBOX_SIZE // 2
    edge = half - 1

    def solid(px, py):
        c = int(px // blocksize)
        r = int(py // blocksize)
        if 0 <= r < world_rows and 0 <= c < world_cols:
            return world[r][c] in SOLID_BLOCKS
        return True

    if not any(
        solid(next_x + ox, player_y + oy)
        for ox, oy in [(-edge, -edge), (edge, -edge), (-edge, edge), (edge, edge)]
    ):
        player_x = next_x

    if not any(
        solid(player_x + ox, next_y + oy)
        for ox, oy in [(-edge, -edge), (edge, -edge), (-edge, edge), (edge, edge)]
    ):
        player_y = next_y

    world_px_w = world_cols * blocksize
    world_px_h = world_rows * blocksize
    player_x = max(0, min(player_x, world_px_w))
    player_y = max(0, min(player_y, world_px_h))

    cam_x = player_x - screen_width // 2
    cam_y = player_y - (screen_height - toolbar_height) // 2
    cam_x = max(0, min(cam_x, world_px_w - screen_width))
    cam_y = max(0, min(cam_y, world_px_h - (screen_height - toolbar_height)))

    cx = screen_width // 2
    cy = (screen_height - toolbar_height) // 2
    dxm = mx - cx
    dym = my - cy
    if dxm or dym:
        player_angle = -math.degrees(math.atan2(dxm, -dym))

    if my < base_rows * blocksize:
        col = int((mx + cam_x) // blocksize)
        row = int((my + cam_y) // blocksize)
        if 0 <= row < world_rows and 0 <= col < world_cols:
            hovered_cell = (row, col)

    start_col = int(cam_x // blocksize)
    start_row = int(cam_y // blocksize)
    end_col = start_col + base_cols + 2
    end_row = start_row + base_rows + 2

    screen.fill((0, 0, 0))

    for r in range(start_row, end_row):
        for c in range(start_col, end_col):
            if 0 <= r < world_rows and 0 <= c < world_cols:
                img = block_images.get(world[r][c])
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

    rotated = pygame.transform.rotate(player_img_original, player_angle)
    rect = rotated.get_rect(center=(screen_width // 2, (screen_height - toolbar_height) // 2))
    screen.blit(rotated, rect.topleft)

    pygame.draw.rect(
        screen,
        (40, 40, 40),
        (0, base_rows * blocksize, screen_width, toolbar_height),
    )

    for rect, block_id in toolbar_slots:
        if rect.collidepoint(mx, my):
            hovered_slot = rect

        if block_id == DELETE:
            pygame.draw.rect(screen, (180, 50, 50), rect)
            txt = font.render("X", True, (255, 255, 255))
            screen.blit(txt, txt.get_rect(center=rect.center))
        else:
            img = pygame.transform.scale(block_images[block_id], (rect.width, rect.height))
            screen.blit(img, rect.topleft)

        if block_id == selected_block:
            pygame.draw.rect(screen, (255, 255, 255), rect, 3)

        if rect == hovered_slot:
            pygame.draw.rect(screen, (255, 255, 0), rect, 2)

    pygame.display.flip()

pygame.quit()
