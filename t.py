import os
from pprint import pformat
import importlib.util
from mimetypes import guess_all_extensions

os.environ['SDL_VIDEODRIVER'] = 'x11'
os.environ['SDL_RENDER_DRIVER'] = 'software'

import time
from pgzero_stub import *
import pgzrun
from pgzhelper import *
from math import sin, cos, radians, sqrt
from random import randrange, choice

WIDTH = 2500
HEIGHT = 2000

ship_dx = 0
ship_dy = 0

ship_speed = 0
ship_angle = 0
rotate_speed = 0
dx = dy = 0

def near_edges():
    side = choice(['north', 'south', 'east', 'west'])
    # angle 0 = up
    # angle -90 = right
    # angle 90 = left
    # angle 180 = down
    if side == 'south':
        angle = randrange(-70, 70)
        x = randrange(WIDTH // 4, WIDTH * 3 // 4)
        y = HEIGHT + 100
    elif side == 'north':
        angle = randrange(90 + 45, 180 + 45)
        x = randrange(WIDTH // 4, WIDTH * 3 // 4)
        y = -100
    elif side == 'east':
        angle = randrange(45, 180 - 45)
        x = WIDTH + 100
        y = randrange(HEIGHT // 4, HEIGHT * 3 // 4)
    elif side == 'west':
        angle = randrange(-180 + 45, -45)
        x = -100
        y = randrange(HEIGHT // 4, HEIGHT * 3 // 4)
    return (x, y, angle)

def highscore_db_write():
    data = { 'highscores': game.highscores }
    with open('hsdb.py', 'w') as f:
        for key, value in data.items():
            f.write(f"{key} = {pformat(value)}\n\n")

def highscore_db_read():
    try:
        spec = importlib.util.spec_from_file_location("database", "hsdb.py")
        db = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(db)

        highscores = db.highscores
    except FileNotFoundError:
        highscores = [{'initials':'', 'score':0}] * 10
    return highscores

class Game:
    def __init__(self):
        self.initial_lives = 4
        self.nr_asteroids = { 0: 3, 1: 4, 2:5 }
        self.speed = { 0: 1.0, 1:1.5, 2:2.0 }
        self.initials = ""
        self.highscores = highscore_db_read()
        self.font = pygame.font.Font('images/Hyperspace.otf', 100)
        self.font_medium = pygame.font.Font('images/Hyperspace.otf', 150)
        self.font_large = pygame.font.Font('images/Hyperspace.otf', 300)
        # 20 points for a large asteroid, 50 for a medium, and 100 for a small one. Flying saucers award higher points: 200 for a large saucer and 1,000 for a small one. A bonus ship is also awarded for every 10,000
        self.scores = {
            'big': 20,
            'medium': 50,
            'small': 100,
            'ufo':200,
            'small-ufo':1000,
        }
        self.extra_life = 10000

        # top, left coord or score
        self.score_x = 200
        self.score_y = 10
        self.lives_x = self.score_x + 50
        self.lives_y = self.score_y + 180

        highscore_db_read()
        self.init()

    def init(self):
        self.level = 0
        self.ship = Ship()
        self.bullets = [ Bullet() for _ in range(10) ]
        self.lives = Lives(self)
        self.ufo = Ufo()
        self.asteroids = None
        self.exploding_ship = None
        self.score = 0
        self.prev_score = 0
        self.game_over = False
        self.get_highscore = False
        self.show_highscore = False
        self.restart = False
        self.init_asteroids()

    def over(self):
        self.game_over = True
        min_score = min( [ x['score'] for x in game.highscores ] )
        if game.score >= min_score:
            self.get_highscore = True
        else:
            self.show_highscore = True

    def init_asteroids(self):
        self.asteroids = [ Asteroid(-300, -300, self.speed.get(self.level,3.0)) for _ in range(self.nr_asteroids.get(self.level, 7)) ]

    def level_update(self):
        if not(any( [ a.asteroid_in_flight for a in self.asteroids ] )):
            self.level += 1
            print("level up",self.level)
            self.init_asteroids()

    def score_update(self):
        if (self.score // self.extra_life - self.prev_score // self.extra_life) > 0:
            self.lives.lives += 1
        self.prev_score = self.score


class Ufo:
    def __init__(self):
        self.x = 0
        self.y = 0
        self.in_flight = False
        self.ufo = Actor( "ufo", (200,200))
        self.ufo.scale = 2.5
        self.next_appearance = randrange(100,200)
        self.next_disappear = -1
        self.bullet = Bullet()
        self.debris = None

    def explode(self):
        self.in_flight = False
        self.next_appearance = randrange(100, 200)
        self.next_disappear = -1
        self.debris = Debris(self.x,self.y,self.ufo.width)

    def update(self):
        self.next_appearance -= 1
        self.next_disappear -= 1
        if not self.in_flight and self.next_appearance <= 0:
            self.in_flight = True
            self.x, self.y, self.angle = near_edges()
            self.ufo.center = self.x, self.y
            self.next_disappear = randrange(100,2000)
            self.next_change = randrange(300,1000)
            self.next_shot = randrange(200,500)

        if self.in_flight and self.next_disappear <= 0:
            self.in_flight = False
            self.next_appearance = randrange(100, 200)

        if self.in_flight:
            self.next_change -= 1
            self.next_shot -= 1
            if self.next_shot <= 0:
                self.next_shot = randrange(200, 500)
                self.bullet.bullet_angle = randrange(0, 360)
                self.bullet.bullet_in_flight = True
                self.bullet.bullet_x = self.x
                self.bullet.bullet_y = self.y
                self.bullet.bullet_speed = 12

            if self.next_change <= 0:
                self.next_change = randrange(300, 1000)
                self.angle = randrange(360)
            dx,dy = directional_movement(self.angle)
            self.x += dx * 2.5
            self.y += dy * 2.5
            self.ufo.center = self.x, self.y
            if self.ufo.bottom <= 0.0:
                self.ufo.top = HEIGHT
            elif self.ufo.top >= HEIGHT:
                self.ufo.bottom = 0
            if self.ufo.left >= WIDTH:
                self.ufo.right = 0
            elif self.ufo.right <= 0:
                self.ufo.left = WIDTH
            self.x, self.y = self.ufo.center

        if self.debris:
            self.debris.update()
        self.bullet.update()

    def draw(self):
        if self.in_flight:
            self.ufo.draw()
        self.bullet.draw()
        if self.debris:
            self.debris.draw()

class Bullet:
    def __init__(self):
        self.bullet_in_flight = False
        self.bullet_x = 0
        self.bullet_y = 0
        self.bullet_angle = 0
        self.bullet_speed = 0

    def update(self):
        if self.bullet_in_flight:
            bdy, bdx = directional_movement(self.bullet_angle)
            self.bullet_x += bdx * self.bullet_speed
            self.bullet_y -= bdy * self.bullet_speed

        if self.bullet_x < 0 or self.bullet_x > WIDTH or self.bullet_y < 0 or self.bullet_y > HEIGHT:
            self.bullet_in_flight = False

    def draw(self):
        if self.bullet_in_flight:
            screen.draw.filled_circle((self.bullet_x,self.bullet_y), 4, (255, 255, 255))


class Asteroid:
    def __init__(self,init_x,init_y,speed,asteroid_size='big'):
        self.asteroid_in_flight = True
        self.asteroid_x = init_x
        self.asteroid_y = init_y
        self.asteroid_angle = randrange(360)
        self.speed = speed # randrange(5,10) / 5.0
        self.size = asteroid_size
        self.debris = None

        if asteroid_size == 'big':
            self.actor = Actor("asteroid-a", center=(self.asteroid_x, self.asteroid_y))
            self.actor.scale = 0.6
        elif asteroid_size == 'medium':
            self.actor = Actor("asteroid-b", center=(self.asteroid_x, self.asteroid_y))
            self.actor.scale = 0.3
        elif asteroid_size == 'small':
            self.actor = Actor("asteroid-c", center=(self.asteroid_x, self.asteroid_y))
            self.actor.scale = 0.2

    def explode(self):
        self.debris = Debris(self.asteroid_x, self.asteroid_y, self.actor.width)

    def update(self):
        if self.asteroid_in_flight:
            bdy, bdx = directional_movement(self.asteroid_angle)
            self.asteroid_x += bdx * self.speed
            self.asteroid_y -= bdy * self.speed

        if self.asteroid_x < -200 or self.asteroid_x > WIDTH + 200 or self.asteroid_y < -200 or self.asteroid_y > HEIGHT + 200:
            # respawn
            self.asteroid_x, self.asteroid_y, self.asteroid_angle = near_edges()

        self.actor.center = (self.asteroid_x, self.asteroid_y)

        if self.debris:
            self.debris.update()

    def draw(self):
        if self.asteroid_in_flight:
            self.actor.draw()
        if self.debris:
            self.debris.draw()

class Ship:
    def __init__(self):
        self.respawn()
        self.actor = Actor("ship", center=(self.x, self.y))
        self.actor.scale = 2.0
        self.exploding = False
        self.teleport_counter = randrange(5, 15)

    def respawn(self):
        self.x = WIDTH // 2
        self.y = HEIGHT // 2
        self.dx = self.dy = 0
        self.angle = 0

    def teleport(self):
        while True:
            try_x = randrange(WIDTH)
            try_y = randrange(HEIGHT)
            self.x = try_x
            self.y = try_y
            self.actor.x = self.x
            self.actor.y = self.y
            collision = asteroid_vs_ship(game)
            if collision:
                if self.teleport_counter < 0:
                    self.teleport_counter = randrange(5,15)
                    game.exploding_ship = ExplodingShip(game.ship)
                    game.lives.lives -= 1
                    break
                else:
                    continue
            else:
                break

        self.teleport_counter -= 1

    def update(self):
        self.x += self.dx
        self.y -= self.dy

        ship = self.actor
        self.actor.center = (self.x, self.y)
        if ship.bottom <= 0.0:
            ship.top = HEIGHT
        elif ship.top >= HEIGHT:
            ship.bottom = 0
        if ship.left >= WIDTH:
            ship.right = 0
        elif ship.right <= 0:
            ship.left = WIDTH
        self.x, self.y = ship.center

        self.actor.angle = self.angle

    def thrust(self):
        bdy, bdx = directional_movement(self.angle)
        speed = sqrt( (self.dx+bdx*0.3)**2 + (self.dy+bdy*0.3)**2 )
        if speed < 8:
            self.dx += bdx * 0.3
            self.dy += bdy * 0.3
        self.actor.image = "ship-flame"
        self.actor.scale = 2.0

    def thrust_off(self):
        self.actor.image = "ship"
        self.actor.scale = 2.0

    def draw(self):
        self.actor.draw()

from dataclasses import dataclass

@dataclass
class DebriePiece:
    x : int
    y : int
    lifetime : int
    angle: int

class Debris:
    def __init__(self,x,y,width):
        nr_debris = width // 5
        self.pieces = []
        for deb in range(nr_debris):
            angle = deb * (360 / nr_debris) + randrange(-20, 20)
            self.pieces.append(DebriePiece(x,y,randrange(45, 160),angle))
        self.in_flight = True

    def update(self):
        if self.in_flight:
            any_left = False
            for p in self.pieces:
                if p.lifetime > 0:
                    any_left = True
                    dx, dy = directional_movement(p.angle + 90)
                    p.x += dx * 0.3
                    p.y += dy * 0.3
                    p.lifetime -= 1
            if not any_left:
                self.in_flight = False

    def draw(self):
        if self.in_flight:
            for p in self.pieces:
                if p.lifetime > 0:
                    screen.draw.filled_circle((p.x,p.y), 2, (255, 255, 255))

class ShipDebris:
    def __init__(self,x,y,length,angel,lifetime):
        self.x = x
        self.y = y
        self.in_flight = True
        self.angle = angel
        self.length = length
        self.lifetime = lifetime
    def update(self):
        if self.in_flight:
            dx, dy = directional_movement(self.angle + 90)
            self.x += dx * 0.3
            self.y += dy * 0.3
            self.lifetime -= 1
            if self.lifetime <= 0:
                self.in_flight = False

    def draw(self):
        if self.in_flight:
            dx, dy = directional_movement(self.angle)
            x1 = self.x + dx * self.length / 2
            y1 = self.y + dy * self.length / 2
            x2 = self.x - dx * self.length / 2
            y2 = self.y - dy * self.length / 2
            screen.draw.line((x1,y1),(x2, y2), (255, 255, 255))

class ExplodingShip:
    def __init__(self, ship):
        self.ship = ship
        self.debris = []
        for deb in range(6):
            angle = deb * (360/6) + randrange(-20,20)
            d = ShipDebris( ship.x, ship.y, randrange(30,75), angle, lifetime=randrange(45,160) )
            self.debris.append(d)
    def draw(self):
        for d in self.debris:
            d.draw()
    def update(self):
        for d in self.debris:
            d.update()
    def done(self):
        return all( [ not d.in_flight for d in self.debris ])

class Lives:
    def __init__(self,game):
        self.lives = game.initial_lives
        self.life_symbols = []
        x = game.lives_x
        for l in range(15): # max lives
            a = Actor("ship", center=(x, game.lives_y ))
            a.scale = 2.5
            x += a.width * 1.1
            self.life_symbols.append(a)

    def draw(self):
        for l in range(self.lives):
            self.life_symbols[l].draw()

def display_score(score):
    scoreStr = str("%02d" % score)
    scoreText = game.font.render(scoreStr, True, (255, 255, 255))
    scoreTextRect = scoreText.get_rect(left = game.score_x, top = game.score_y )
    screen.blit(scoreText, scoreTextRect)

def display_end():
    end_text = game.font_large.render("GAME OVER", True, (255, 255, 255))
    end_rect = end_text.get_rect(centerx = WIDTH//2, centery = HEIGHT//2 - 150 )
    screen.blit(end_text, end_rect)


def display_high_dialog():
    hi_text = game.font_medium.render("TOP 10 SCORE", True, (255, 255, 255))
    hi_rect = hi_text.get_rect(centerx = WIDTH//2, centery = HEIGHT//2 + 100 )
    screen.blit(hi_text, hi_rect)
    init_text = game.font_medium.render(f"ENTER INITIALS:{game.initials}", True, (255, 255, 255))
    init_rect = init_text.get_rect(centerx = WIDTH//2, centery = HEIGHT//2 + 250 )
    screen.blit(init_text, init_rect)

def display_highscores():
    hi_text = game.font_medium.render("TOP 10 SCORE", True, (255, 255, 255))
    hi_rect = hi_text.get_rect( centerx = WIDTH//2, centery = HEIGHT//2 - 600 )
    screen.blit(hi_text, hi_rect)

    y = HEIGHT//2 - 600 + 140
    for item in sorted(game.highscores, key=lambda x: x['score'], reverse=True):
        istr = "--" if len(item['initials']) == 0 else item['initials']
        sstr = f"{istr}  {item['score']}"
        hi_text = game.font_medium.render(sstr, True, (255, 255, 255))
        hi_rect = hi_text.get_rect(x=WIDTH // 2 - 400, centery=y)
        screen.blit(hi_text, hi_rect)
        y += 140


game = Game()


def bullets_hit_asteroids( game ):
    for bullet in game.bullets:
        if bullet.bullet_in_flight:
            for asteroid in game.asteroids:
                if asteroid.asteroid_in_flight:
                    if asteroid.actor.collidepoint( bullet.bullet_x, bullet.bullet_y ):
                        # - bullet should be destroyed
                        bullet.bullet_in_flight = False
                        # - asteroid should be split in two (if it is big or medium size, if small then just destroyed)
                        asteroid.asteroid_in_flight = False
                        game.score += game.scores[asteroid.size]
                        if asteroid.size in ['big','medium']:
                            new_size = {'big':'medium', 'medium':'small'}[asteroid.size]
                            ast1 = Asteroid( asteroid.asteroid_x, asteroid.asteroid_y, asteroid.speed, new_size )
                            game.asteroids.append( ast1 )
                            ast2 = Asteroid( asteroid.asteroid_x, asteroid.asteroid_y, asteroid.speed, new_size )
                            game.asteroids.append( ast2 )
                        else:
                            asteroid.explode()
                        break

def bullets_hit_ufo(game):
    for bullet in game.bullets:
        if bullet.bullet_in_flight:
            if game.ufo.in_flight:
                if game.ufo.ufo.collidepoint(bullet.bullet_x, bullet.bullet_y):
                    # - bullet should be destroyed
                    bullet.bullet_in_flight = False
                    game.ufo.in_flight = False
                    game.ufo.explode()
                    game.score += game.scores['ufo']

def ufo_bullet_vs_ship( game ):
    if game.ufo.bullet.bullet_in_flight:
        if game.ship.actor.collidepoint( game.ufo.bullet.bullet_x, game.ufo.bullet.bullet_y ):
            return True
    return False

def ufo_vs_ship( game ):
    if game.ufo.in_flight:
        if game.ship.actor.colliderect( game.ufo.ufo ):
            return True
    return False

def asteroid_vs_ship( game ):
    for asteroid in game.asteroids:
        if asteroid.asteroid_in_flight:
            if asteroid.actor.colliderect( game.ship.actor ):
                return True
    return False



def draw():
    if game.restart:
        return
    screen.clear()
    for ast in game.asteroids:
        ast.draw()
    for bull in game.bullets:
        bull.draw()
    if game.exploding_ship:
        game.exploding_ship.draw()
    else:
        game.ship.draw()
    game.lives.draw()
    game.ufo.draw()
    display_score(game.score)
    if game.game_over and not game.show_highscore:
        display_end()
    if game.get_highscore:
        display_high_dialog()
    if game.show_highscore:
        display_highscores()

def directional_movement( angle ):
    tangle = angle + 90.0
    tangle = radians( tangle)

    delta_x = sin(tangle)
    delta_y = cos(tangle)
    return delta_x, delta_y

def rotate( rotate_speed ):
    if rotate_speed > 0:
        if rotate_speed <= 0.4:
            rotate_speed = 0
        else:
            rotate_speed -= 0.4
    elif rotate_speed < 0:
        if rotate_speed > -0.4:
            rotate_speed = 0
        else:
            rotate_speed += 0.4

    if rotate_speed < -5:
        rotate_speed = -5
    elif rotate_speed >= 5:
        rotate_speed = 5

    return rotate_speed

def update():
    global rotate_speed
    global bullets

    if game.restart:
        game.restart = False
        game.init()
        return

    game.ship.angle += rotate_speed

    if not game.game_over:
        if keyboard.W:
            game.ship.thrust()

        if keyboard.A:
            rotate_speed += 0.5
        elif keyboard.D:
            rotate_speed -= 0.5

        rotate_speed = rotate( rotate_speed )

        game.ship.angle += rotate_speed

        bullets_hit_asteroids( game )
        bullets_hit_ufo( game )
        collision = asteroid_vs_ship( game )
        collision = collision or ufo_vs_ship( game )
        collision = collision or ufo_bullet_vs_ship( game )

        if collision and not game.exploding_ship:
            game.exploding_ship = ExplodingShip(game.ship)
            game.lives.lives -= 1
            if game.lives.lives == 0:
                game.over()

        if game.exploding_ship and game.exploding_ship.done():
            game.exploding_ship = None
            game.ship.respawn()

    for bull in game.bullets:
        bull.update()
    for ast in game.asteroids:
        ast.update()
    if game.exploding_ship:
        game.exploding_ship.update()
    else:
        game.ship.update()
    game.ufo.update()
    game.level_update()
    game.score_update()

def on_key_down(key,mod,unicode):
    global rotate_speed
    global game

    if game.game_over:
        if game.get_highscore:
            if key == keys.RETURN:
                game.show_highscore = True
                game.get_highscore = False
                game.highscores.append( {'initials':game.initials, 'score':game.score} )
                game.highscores = sorted(game.highscores, key=lambda x: x['score'], reverse=True)[:10]
                highscore_db_write()
            elif key == keys.BACKSPACE:
                if len(game.initials) > 0:
                    game.initials = game.initials[:-1]
            elif unicode != "":
                if len(game.initials) < 2:
                    game.initials += unicode
        elif game.show_highscore:
            game.restart = True
        return

    if key == keys.A:
        rotate_speed += 0.4
    elif key == keys.D:
        rotate_speed -= 0.4
    elif key == keys.W:
        game.ship.thrust()
    elif key == keys.S:
        game.ship.teleport()

    elif key == keys.SPACE:
        for bull in game.bullets:
            if not bull.bullet_in_flight:
                bull.bullet_in_flight = True
                bull.bullet_x = game.ship.x
                bull.bullet_y = game.ship.y
                bull.bullet_angle = game.ship.angle
                bull.bullet_speed = 12
                break



def on_key_up(key):
    if key == keys.W:
        game.ship.thrust_off()

pgzrun.go()

