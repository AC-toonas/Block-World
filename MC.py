import pygame
import os

# ---------- CONFIG ----------
blocksize = 32
world_cols = 25
world_rows = 15
toolbar_height = 64

screen_width = world_cols * blocksize
screen_height = world_rows * blocksize + toolbar_height

# ---------- BLOCK DEFINITIONS ----------
BLOCKS = {
    0: "sky",
    1: "grass",
    2: "dirt",
    3: "wood",
    4: "leaves",
    5: "water",
    6: "stone",
    7: "brick",
    8: "wall",
}

DELETE = -1
selected_block = 1

# ---------- LOAD IMAGES ----------
block_images = {}

for block_id, name in BLOCKS.items():
    img = pygame.image.load(f"{name}.png").convert_alpha()
    img = pygame.transform.scale(img, (blocksize, blocksize))
    block_images[block_id] = img

# ---------- WORLD ----------
world = [[0 for _ in range(world_cols)] for _ in range(world_rows)]

# example ground
for c in range(world_cols):
    world[world_rows - 1][c] = 1 
    world[world_rows - 2][c] = 2 

# ---------- PYGAME ----------
pygame.init()
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("2D Creative World")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)

# ---------- TOOLBAR ----------
toolbar_slots = []
slot_size = 48
slot_padding = 8
toolbar_y = world_rows * blocksize + 8

for i, block_id in enumerate(list(BLOCKS.keys()) + [DELETE]):
    x = slot_padding + i * (slot_size + slot_padding)
    rect = pygame.Rect(x, toolbar_y, slot_size, slot_size)
    toolbar_slots.append((rect, block_id))

# ---------- DRAW ----------
def drawtile(row, col):
    block_id = world[row][col]
    img = block_images[block_id]
    screen.blit(img, (col * blocksize, row * blocksize))

def draw_toolbar(hovered_slot):
    y = world_rows * blocksize
    pygame.draw.rect(screen, (40, 40, 40), (0, y, screen_width, toolbar_height))

    for rect, block_id in toolbar_slots:
        if block_id == DELETE:
            pygame.draw.rect(screen, (180, 50, 50), rect)
            text = font.render("X", True, (255, 255, 255))
            screen.blit(text, text.get_rect(center=rect.center))
        else:
            img = pygame.transform.scale(block_images[block_id], (rect.width, rect.height))
            screen.blit(img, rect.topleft)

        if block_id == selected_block:
            pygame.draw.rect(screen, (255, 255, 255), rect, 3)

        if rect == hovered_slot:
            pygame.draw.rect(screen, (255, 255, 0), rect, 2)

# ---------- MAIN LOOP ----------
running = True
while running:
    clock.tick(60)

    hovered_cell = None
    hovered_slot = None
    mx, my = pygame.mouse.get_pos()

    if my < world_rows * blocksize:
        col = mx // blocksize
        row = my // blocksize
        if 0 <= row < world_rows and 0 <= col < world_cols:
            hovered_cell = (row, col)
    else:
        for rect, block_id in toolbar_slots:
            if rect.collidepoint(mx, my):
                hovered_slot = rect
                break

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
            if hovered_cell:
                r, c = hovered_cell
                world[r][c] = 0 if selected_block == DELETE else selected_block
            elif hovered_slot:
                for rect, block_id in toolbar_slots:
                    if rect == hovered_slot:
                        selected_block = block_id
                        break

    screen.fill((0, 0, 0))

    for r in range(world_rows):
        for c in range(world_cols):
            drawtile(r, c)

    if hovered_cell:
        r, c = hovered_cell
        pygame.draw.rect(
            screen, (255, 255, 0),
            (c * blocksize, r * blocksize, blocksize, blocksize), 2
        )

    draw_toolbar(hovered_slot)
    pygame.display.flip()

pygame.quit()
