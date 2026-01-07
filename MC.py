import pygame
import os
import random
import math

# ---------- CONFIG ----------
GAME_VERSION = "Alpha-0.03"

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
PLAYER_SIZE = 32
HITBOX_SIZE = 24

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
WOOD = 3
LEAVES = 4
WATER = 5
SOLID_BLOCKS = {3, 4, 6, 7}

DELETE = -1
selected_block = GRASS

# ---------- INIT ----------
pygame.init()
screen = pygame.display.set_mode((screen_width, screen_height))
pygame.display.set_caption("Block World")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 24)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------- LOAD IMAGES ----------
block_images = {}
for block_id, name in BLOCKS.items():
    path = os.path.join(BASE_DIR, f"{name}.png")
    if os.path.exists(path):
        img = pygame.image.load(path).convert_alpha()
        img = pygame.transform.scale(img, (blocksize, blocksize))
        block_images[block_id] = img

def tint_image(img, tint):
    t = img.copy()
    s = pygame.Surface(t.get_size(), pygame.SRCALPHA)
    s.fill(tint)
    t.blit(s, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    return t

if GRASS in block_images:
    block_images[GRASS] = tint_image(block_images[GRASS], (150, 200, 150, 255))

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
        r = random.randint(1, world_rows - size - 1)
        c = random.randint(1, world_cols - size - 1)
        if area_is_clear(r, c, size, size):
            for y in range(size):
                for x in range(size):
                    world[r + y][c + x] = WATER
            break

for _ in range(250):
    for _ in range(120):
        r = random.randint(2, world_rows - 3)
        c = random.randint(2, world_cols - 3)
        pts = [(r,c),(r-1,c),(r+1,c),(r,c-1),(r,c+1)]
        min_r = min(p[0] for p in pts)
        max_r = max(p[0] for p in pts)
        min_c = min(p[1] for p in pts)
        max_c = max(p[1] for p in pts)
        if area_is_clear(min_r, min_c, max_r-min_r+1, max_c-min_c+1):
            world[r][c] = WOOD
            world[r-1][c] = LEAVES
            world[r+1][c] = LEAVES
            world[r][c-1] = LEAVES
            world[r][c+1] = LEAVES
            break

# ---------- TOOLBAR ----------
toolbar_slots = []
slot_size = 48
slot_padding = 8
toolbar_y = base_rows * blocksize + 8

for i, block_id in enumerate(list(BLOCKS.keys()) + [DELETE]):
    x = slot_padding + i * (slot_size + slot_padding)
    toolbar_slots.append((pygame.Rect(x, toolbar_y, slot_size, slot_size), block_id))

# ---------- PLAYER ----------
player_x = (world_cols * blocksize) // 2
player_y = (world_rows * blocksize) // 2
player_angle = 0

# ---------- START MENU ----------
def start_menu():
    title_font = pygame.font.SysFont(None, 64)
    button_font = pygame.font.SysFont(None, 36)

    title = title_font.render(f"Block World! V: {GAME_VERSION}", True, (255,255,255))
    b1 = pygame.Rect(screen_width//2-150, 250, 300, 60)
    b2 = pygame.Rect(screen_width//2-150, 330, 300, 60)

    while True:
        mx, my = pygame.mouse.get_pos()
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                exit()
            if e.type == pygame.MOUSEBUTTONDOWN:
                if b1.collidepoint(mx,my):
                    return "survival"
                if b2.collidepoint(mx,my):
                    return "creative"

        screen.fill((20,20,20))
        screen.blit(title, title.get_rect(center=(screen_width//2,140)))

        pygame.draw.rect(screen,(60,60,60),b1)
        pygame.draw.rect(screen,(60,60,60),b2)

        if b1.collidepoint(mx,my):
            pygame.draw.rect(screen,(255,255,255),b1,3)
        if b2.collidepoint(mx,my):
            pygame.draw.rect(screen,(255,255,255),b2,3)

        t1 = button_font.render("Survival Mode",True,(255,255,255))
        t2 = button_font.render("Creative Mode",True,(255,255,255))

        screen.blit(t1,t1.get_rect(center=b1.center))
        screen.blit(t2,t2.get_rect(center=b2.center))

        pygame.display.flip()

# ---------- GAME LOOP ----------
def run_game(mode):
    global player_x, player_y, player_angle, selected_block

    running = True
    while running:
        clock.tick(60)
        hovered_slot = None
        hovered_cell = None
        mx, my = pygame.mouse.get_pos()

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            if e.type == pygame.KEYDOWN:
                if pygame.K_1 <= e.key <= pygame.K_9:
                    k = e.key - pygame.K_1
                    if k in BLOCKS:
                        selected_block = k
                if e.key == pygame.K_x:
                    selected_block = DELETE
            if e.type == pygame.MOUSEBUTTONDOWN:
                if my >= base_rows * blocksize:
                    for r,b in toolbar_slots:
                        if r.collidepoint(mx,my):
                            selected_block = b
                            break
                else:
                    c = int((mx + cam_x) // blocksize)
                    r = int((my + cam_y) // blocksize)
                    if 0 <= r < world_rows and 0 <= c < world_cols:
                        world[r][c] = GRASS if selected_block == DELETE else selected_block

        keys = pygame.key.get_pressed()
        dx = dy = 0
        if keys[pygame.K_w]: dy -= 1
        if keys[pygame.K_s]: dy += 1
        if keys[pygame.K_a]: dx -= 1
        if keys[pygame.K_d]: dx += 1
        if dx or dy:
            l = math.hypot(dx,dy)
            dx/=l; dy/=l

        nx = player_x + dx*player_speed
        ny = player_y + dy*player_speed
        h = HITBOX_SIZE//2-1

        def solid(px,py):
            c = int(px//blocksize)
            r = int(py//blocksize)
            if 0<=r<world_rows and 0<=c<world_cols:
                return world[r][c] in SOLID_BLOCKS
            return True

        if not any(solid(nx+ox,player_y+oy) for ox,oy in [(-h,-h),(h,-h),(-h,h),(h,h)]):
            player_x = nx
        if not any(solid(player_x+ox,ny+oy) for ox,oy in [(-h,-h),(h,-h),(-h,h),(h,h)]):
            player_y = ny

        cam_x = player_x - screen_width//2
        cam_y = player_y - (screen_height-toolbar_height)//2
        cam_x = max(0,min(cam_x,world_cols*blocksize-screen_width))
        cam_y = max(0,min(cam_y,world_rows*blocksize-(screen_height-toolbar_height)))

        cx = screen_width//2
        cy = (screen_height-toolbar_height)//2
        if mx!=cx or my!=cy:
            player_angle = -math.degrees(math.atan2(mx-cx, -(my-cy)))

        if my < base_rows*blocksize:
            c = int((mx+cam_x)//blocksize)
            r = int((my+cam_y)//blocksize)
            if 0<=r<world_rows and 0<=c<world_cols:
                hovered_cell = (r,c)

        sc = int(cam_x//blocksize)
        sr = int(cam_y//blocksize)

        screen.fill((0,0,0))
        for r in range(sr,sr+base_rows+2):
            for c in range(sc,sc+base_cols+2):
                if 0<=r<world_rows and 0<=c<world_cols:
                    img = block_images.get(world[r][c])
                    if img:
                        screen.blit(img,(c*blocksize-cam_x,r*blocksize-cam_y))

        if hovered_cell:
            r,c = hovered_cell
            pygame.draw.rect(screen,(255,255,0),(c*blocksize-cam_x,r*blocksize-cam_y,blocksize,blocksize),2)

        rot = pygame.transform.rotate(player_img_original,player_angle)
        screen.blit(rot,rot.get_rect(center=(cx,cy)))

        pygame.draw.rect(screen,(40,40,40),(0,base_rows*blocksize,screen_width,toolbar_height))
        for r,b in toolbar_slots:
            if r.collidepoint(mx,my):
                hovered_slot = r
            if b == DELETE:
                pygame.draw.rect(screen,(180,50,50),r)
                t = font.render("X",True,(255,255,255))
                screen.blit(t,t.get_rect(center=r.center))
            else:
                if b in block_images:
                    screen.blit(pygame.transform.scale(block_images[b],(r.w,r.h)),r.topleft)
            if b == selected_block:
                pygame.draw.rect(screen,(255,255,255),r,3)
            if r == hovered_slot:
                pygame.draw.rect(screen,(255,255,0),r,2)

        pygame.display.flip()

# ---------- ENTRY ----------
mode = start_menu()
run_game(mode)
pygame.quit()
