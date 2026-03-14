
import pygame, random, sys, time

pygame.init()
try:
    pygame.mixer.init()
except Exception:
    pass

# ---------- CONFIG ----------
WINDOW_W, WINDOW_H = 740, 640
PIXEL_SCALE = 2
BASE_W = WINDOW_W // PIXEL_SCALE
BASE_H = WINDOW_H // PIXEL_SCALE

CELL = 16
COLS = BASE_W // CELL
ROWS = BASE_H // CELL

SCREEN = pygame.display.set_mode((WINDOW_W, WINDOW_H))
BASE_SURF = pygame.Surface((BASE_W, BASE_H))

CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont("consolas", 20)
BIG = pygame.font.SysFont("consolas", 28)

# Colors
BG = (12, 12, 12)
GRID = (24, 24, 24)
HEAD = (0, 200, 0)
TAIL = (0, 100, 0)
FOOD = (200, 30, 30)
UI_COL = (180, 180, 180)
TITLE_COL = (0, 220, 0)
SCANLINE_COL = (0,0,0,30)  # semi-transparent black for scanlines

START_LEN = 3
FLASH_DURATION = 1.0
HIGHSCORE_FILE = "highscore.txt"

# Optional sounds
def try_load(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None

SND_EAT = try_load("eat.wav")
SND_DEATH = try_load("death.wav")
SND_MOVE = try_load("move.wav")
SND_POWER = try_load("powerup.wav")

# ---------- UTIL ----------
def grid_rect(pos):
    x, y = pos
    return pygame.Rect(x * CELL, y * CELL, CELL, CELL)

def rand_cell(exclude=set()):
    while True:
        p = (random.randint(0, COLS - 1), random.randint(0, ROWS - 1))
        if p not in exclude:
            return p

def load_highscore():
    try:
        with open(HIGHSCORE_FILE, "r") as f:
            return int(f.read().strip() or 0)
    except Exception:
        return 0

def save_highscore(v):
    try:
        with open(HIGHSCORE_FILE, "w") as f:
            f.write(str(int(v)))
    except Exception:
        pass

# ---------- CLASSES ----------
class Snake:
    def __init__(self, head_pos, length=START_LEN):
        self.segments = [head_pos]
        for i in range(1, length):
            self.segments.append((head_pos[0]-i, head_pos[1]))
        self.dir = (1,0)
        self.grow_pending = 0

    def head(self):
        return self.segments[0]

    def step(self):
        x, y = self.head()
        dx, dy = self.dir
        new = (x+dx, y+dy)
        self.segments.insert(0,new)
        if self.grow_pending > 0:
            self.grow_pending -= 1
        else:
            self.segments.pop()

    def set_dir(self, nd):
        if (nd[0]*-1, nd[1]*-1) == self.dir and len(self.segments) >1:
            return
        self.dir = nd

    def grow(self,n=1):
        self.grow_pending += n

class Game:
    def __init__(self):
        self.high = load_highscore()
        self.reset()

    def reset(self):
        center = (COLS//2, ROWS//2)
        self.snake = Snake(center)
        self.food = rand_cell(set(self.snake.segments))
        self.score = 0
        self.flash_until = 0.0
        self.paused = False
        self.game_over = False
        self.base_speed = 8
        self.last_tick = time.time()

    def step(self):
        if self.paused or self.game_over:
            return
        self.snake.step()
        if SND_MOVE:
            try: SND_MOVE.play()
            except: pass
        # eat check
        if self.snake.head() == self.food:
            self.score +=1
            if SND_EAT:
                try: SND_EAT.play()
                except: pass
            self.snake.grow(1)
            self.flash_until = time.time() + FLASH_DURATION
            self.food = rand_cell(set(self.snake.segments))
        # collisions
        hx, hy = self.snake.head()
        if not (0<=hx<COLS and 0<=hy<ROWS) or self.snake.head() in self.snake.segments[1:]:
            self.trigger_game_over()

    def trigger_game_over(self):
        self.game_over = True
        if SND_DEATH:
            try: SND_DEATH.play()
            except: pass
        if self.score>self.high:
            self.high=self.score
            save_highscore(self.high)

    def draw(self, surf):
        surf.fill(BG)
        # grid
        for gx in range(0, BASE_W, CELL):
            pygame.draw.line(surf, GRID, (gx,0),(gx,BASE_H))
        for gy in range(0, BASE_H, CELL):
            pygame.draw.line(surf, GRID, (0,gy),(BASE_W,gy))
        # food
        pulse = 2 if int(time.time()*3)%2==0 else 1
        fr = grid_rect(self.food).inflate(-pulse,-pulse)
        pygame.draw.rect(surf, FOOD, fr)
        # tail flash
        now = time.time()
        if now < self.flash_until:
            for seg in self.snake.segments[1:]:
                pygame.draw.rect(surf, TAIL, grid_rect(seg))
        # head with glow
        hx, hy = self.snake.head()
        hr = grid_rect((hx,hy))
        glow = pygame.Rect(hr.x-2, hr.y-2, hr.width+4, hr.height+4)
        s = pygame.Surface((glow.width, glow.height),pygame.SRCALPHA)
        s.fill((0,210,0,50))
        surf.blit(s,(glow.x,glow.y))
        pygame.draw.rect(surf,HEAD,hr)
        # HUD
        score_surf = FONT.render(f"S:{self.score}  H:{self.high}", True, UI_COL)
        surf.blit(score_surf,(4,4))
        if self.paused:
            p = BIG.render("PAUSED", True, UI_COL)
            surf.blit(p,(BASE_W//2 - p.get_width()//2, BASE_H//2 - 20))
        if self.game_over:
            over = BIG.render("GAME OVER", True, (220,80,80))
            surf.blit(over,(BASE_W//2 - over.get_width()//2, BASE_H//2 -28))
            info = FONT.render("R - Restart    M - Menu", True, UI_COL)
            surf.blit(info,(BASE_W//2 - info.get_width()//2, BASE_H//2 +8))
        # CRT scanlines
        for y in range(0, BASE_H, 2):
            pygame.draw.line(surf, (0,0,0,30), (0,y),(BASE_W,y))

# ---------- MENU ----------
def draw_menu(surface, selected_idx):
    surface.fill(BG)
    title_s = BIG.render("BLIND SNAKE", True, TITLE_COL)
    surface.blit(title_s, (BASE_W//2 - title_s.get_width()//2,40))
    opts = ["START", "QUIT"]
    for i,opt in enumerate(opts):
        col = TITLE_COL if i==selected_idx else UI_COL
        t = FONT.render(opt,True,col)
        surface.blit(t,(BASE_W//2 - t.get_width()//2,140+i*36))
    ctrl_lines = [
        "Arrow keys - Move",
        "TAB - reveal tail briefly",
        "SPACE - pause",
        "Eat food -> tail flashes 1s"
    ]
    for i,line in enumerate(ctrl_lines):
        t = FONT.render(line,True,(140,200,255))
        surface.blit(t,(20,BASE_H-90+i*18))

# ---------- MAIN ----------
def main():
    game = Game()
    in_menu = True
    menu_idx = 0
    tick_accum = 0.0
    last_time = time.time()
    while True:
        now = time.time()
        dt = now - last_time
        last_time = now
        tick_accum += dt
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                save_highscore(game.high)
                pygame.quit()
                sys.exit()
            if in_menu:
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_UP:
                        menu_idx=(menu_idx-1)%3
                    elif event.key==pygame.K_DOWN:
                        menu_idx=(menu_idx+1)%3
                    elif event.key in [pygame.K_RETURN, pygame.K_SPACE]:
                        if menu_idx==0:
                            in_menu=False
                            game.reset()
                        elif menu_idx==1: pass
                        elif menu_idx==2:
                            save_highscore(game.high)
                            pygame.quit()
                            sys.exit()
                    elif event.key==pygame.K_ESCAPE:
                        save_highscore(game.high)
                        pygame.quit()
                        sys.exit()
            else:
                if event.type==pygame.KEYDOWN:
                    if event.key==pygame.K_UP: game.snake.set_dir((0,-1))
                    elif event.key==pygame.K_DOWN: game.snake.set_dir((0,1))
                    elif event.key==pygame.K_LEFT: game.snake.set_dir((-1,0))
                    elif event.key==pygame.K_RIGHT: game.snake.set_dir((1,0))
                    elif event.key==pygame.K_TAB: game.flash_until=time.time()+1.0
                    elif event.key==pygame.K_SPACE: game.paused=not game.paused
                    elif event.key==pygame.K_r and game.game_over: game.reset()
                    elif event.key==pygame.K_m: in_menu=True
                    elif event.key==pygame.K_ESCAPE:
                        save_highscore(game.high)
                        pygame.quit()
                        sys.exit()
        # Tick
        sec_per_tick=1.0/game.base_speed
        while tick_accum>=sec_per_tick:
            tick_accum-=sec_per_tick
            if not in_menu:
                game.step()
        # Draw
        if in_menu: draw_menu(BASE_SURF, menu_idx)
        else: game.draw(BASE_SURF)
        # scale for pixelated CRT
        scaled=pygame.transform.scale(BASE_SURF,(WINDOW_W,WINDOW_H))
        SCREEN.blit(scaled,(0,0))
        pygame.display.flip()
        CLOCK.tick(60)

if __name__=="__main__":
    main()
