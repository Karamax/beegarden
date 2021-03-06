#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pygame
from pygame.locals import *
from math import *
import random

import time
import os

SCREENRECT = None
MAX_LAYERS = 3
SPRITES_GROUPS = [pygame.sprite.Group() for i in range(MAX_LAYERS + 1)]
NEAR_RADIUS = 20
RANDOM_POINT_BORDER = 42


class BaseSprite(pygame.sprite.DirtySprite):
    """Класс отображения объектов на экране"""
    _img_file_name = 'empty.png'
    _layer = 0
    radius = 1
    speed = 3
    _sprites_count = 0

    def __init__(self, pos=None):
        """Создать объект в указанном месте"""

        if self._layer > MAX_LAYERS:
            self._layer = MAX_LAYERS
        if self._layer < 0:
            self._layer = 0
        self.containers = self.containers, SPRITES_GROUPS[self._layer]
        pygame.sprite.Sprite.__init__(self, self.containers)

        self.image = load_image(self._img_file_name, -1)
        self.images = [self.image, pygame.transform.flip(self.image, 1, 0)]
        self.rect = self.image.get_rect()

        if pos is None:
            self.coord = Point(100, 100)
        else:
            self.coord = Point(pos)
        self.target_coord = Point(0, 0)
        self.rect.center = self.coord.to_screen()

        self.vector = Vector()
        self.is_moving = False
        self.course = self.vector.angle
        self.shot = False

        self.load_value = 0
        self.load_value_px = 0

        BaseSprite._sprites_count += 1
        self._id = BaseSprite._sprites_count

    def __str__(self):
        return 'sprite %s: %s %s %s %s' % (self._id, self.coord, self.vector, self.is_moving, self.is_turning)

    def __repr__(self):
        return str(self)

    x = property(lambda self: self.coord.int_x, doc="текущая позиция X объекта")
    y = property(lambda self: self.coord.int_y, doc="текущая позиция Y объекта")
    w = property(lambda self: self.rect.width, doc="ширина спрайта")
    h = property(lambda self: self.rect.height, doc="высота спрайта")

    def _set_load(self, value):
        """Внутренняя, установить бар загрузки"""
        if value > 100:
            value = 100
        if value < 0:
            value = 0
        self.load_value = value
        self.load_value_px = int((value / 100.0) * self.w)

    def update(self):
        """Внутренняя функция для обновления переменных отображения"""
        if self.vector.dx >= 0:
            self.image = self.images[1].copy()
        else:
            self.image = self.images[0].copy()
        #print self.course, self.vector.angle
        if self.is_moving:
            self.coord.add(self.vector)
            self.rect.center = self.coord.to_screen()
            if self.near(self.target_coord):
                self.stop()
                self.on_stop_at_target()

        if self.load_value_px:
            pygame.draw.line(self.image, (0, 255, 7), (0, 0), (self.load_value_px, 0), 3)

        if not SCREENRECT.contains(self.rect):
            if self.rect.top < SCREENRECT.top:
                self.rect.top = SCREENRECT.top
            if self.rect.bottom > SCREENRECT.bottom:
                self.rect.bottom = SCREENRECT.bottom
            if self.rect.left < SCREENRECT.left:
                self.rect.left = SCREENRECT.left
            if self.rect.right > SCREENRECT.right:
                self.rect.right = SCREENRECT.right
            self.stop()

    def move(self, direction):
        """ Задать движение в направлении <угол в градусах>, <скорость> """
        self.vector = Vector(direction=direction, module=self.speed)
        self.is_moving = True

    def move_at(self, target):
        """ Задать движение к указанной точке <объект/точка/координаты>, <скорость> """
        if type(target) in (type(()), type([])):
            target = Point(target)
        elif isinstance(target, Point):
            pass
        elif isinstance(target, BaseSprite):
            target = target.coord
        else:
            raise Exception("move_at: target %s must be coord or point or sprite!" % target)
        self.target_coord = target
        self.vector = Vector(point1=self.coord, point2=self.target_coord, module=self.speed)
        self.is_moving = True

    def stop(self):
        """ Остановить объект """
        self.is_moving = False

    def on_stop_at_target(self):
        """Обработчик события 'остановка у цели' """
        pass

    def distance_to(self, obj):
        """ Расстояние до объекта <объект/точка>"""
        if isinstance(obj, BaseSprite):
            return self.coord.distance_to(obj.coord)
        if isinstance(obj, Point):
            return self.coord.distance_to(obj)
        raise Exception("sprite.distance_to: obj %s must be Sprite or Point!" % obj)

    def near(self, obj, radius=NEAR_RADIUS):
        """ Проверка близости к объекту <объект/точка>"""
        return self.distance_to(obj) <= radius


class HoneyHolder():
    """Класс объекта, который может нести мёд"""
    honey_speed = 1

    def __init__(self, honey_loaded, honey_max):
        """Задать начальние значения: honey_loaded - сколько изначально мёда, honey_max - максимум"""
        self._honey = honey_loaded
        if honey_max == 0:
            raise Exception("honey_max cant be zero!")
        self._honey_max = honey_max

        self._source = None
        self._target = None
        self._state = 'stop'

        self._set_load_hh()

    honey = property(lambda self: self._honey, doc="""Количество мёда у объекта""")

    def on_honey_loaded(self):
        """Обработчик события 'мёд загружен' """
        pass

    def on_honey_unloaded(self):
        """Обработчик события 'мёд разгружен' """
        pass

    def load_honey_from(self, source):
        """Загрузить мёд от ... """
        self._state = 'loading'
        self._source = source

    def unload_honey_to(self, target):
        """Разгрузить мёд в ... """
        self._target = target
        self._state = 'unloading'

    def is_full(self):
        """полностью заполнен?"""
        return self.honey >= self._honey_max

    def _update(self):
        """Внутренняя функция для обновления переменных отображения"""
        if self._state == 'moving':
            self._source = None
            self._target = None
            return
        if self._source:
            honey = self._source._get_honey()
            if honey:
                self._put_honey(honey)
                if self.honey >= self._honey_max:
                    self.on_honey_loaded()
                    self._source = None
                    self._state = 'stop'
                else:
                    self._state = 'loading'
            else:
                self.on_honey_loaded()
                self._source = None
                self._state = 'stop'
        if self._target:
            honey = self._get_honey()
            self._target._put_honey(honey)
            if self.honey == 0:
                self.on_honey_unloaded()
                self._target = None
                self._state = 'stop'
            else:
                self._state = 'unloading'

    def _get_honey(self):
        """Взять мёд у объекта"""
        if self._honey > self.honey_speed:
            self._honey -= self.honey_speed
            self._set_load_hh()
            return self.honey_speed
        elif self._honey > 0:
            value = self._honey
            self._honey = 0
            self._set_load_hh()
            return value
        return 0.0

    def _put_honey(self, value):
        """Отдать мёд объекту"""
        self._honey += value
        if self._honey > self._honey_max:
            self._honey = self._honey_max
        self._set_load_hh()

    def _set_load_hh(self):
        """Внутренняя функция отрисовки бара"""
        load_value = int((float(self._honey) / self._honey_max) * 100.0)
        BaseSprite._set_load(self, load_value)


class Bee(BaseSprite, HoneyHolder):
    """Пчела. Может летать по экрану и носить мёд."""
    _img_file_name = 'bee.png'
    _layer = 2
    team = 1
    my_beehive = None
    flowers = []

    def __init__(self, pos=None):
        """создать пчелу в указанной точке экрана"""
        if self.team > 1:
            self._img_file_name = 'bee-2.png'
        self.my_beehive = Scene.get_beehive(self.team)
        pos = self.my_beehive.coord
        BaseSprite.__init__(self, pos)
        self.speed = float(self.speed) - random.random()
        HoneyHolder.__init__(self, 0, 100)
        self.on_born()

    def __str__(self):
        return 'bee(%s,%s) %s %s' % (self.x, self.y, self._state, BaseSprite.__str__(self))

    def __repr__(self):
        return str(self)

    def update(self):
        """Внутренняя функция для обновления переменных отображения"""
        HoneyHolder._update(self)
        BaseSprite.update(self)

    def move_at(self, target):
        """ Задать движение к указанной точке <объект/точка/координаты>, <скорость> """
        self.target = target
        self._state = 'moving'
        BaseSprite.move_at(self, target)

    def on_stop_at_target(self):
        """Обработчик события 'остановка у цели' """
        self._state = 'stop'
        if isinstance(self.target, Flower):
            self.on_stop_at_flower(self.target)
        elif isinstance(self.target, BeeHive):
            self.on_stop_at_beehive(self.target)
        else:
            pass

    def on_born(self):
        """Обработчик события 'рождение' """
        pass

    def on_stop_at_flower(self, flower):
        """Обработчик события 'остановка у цветка' """
        pass

    def on_stop_at_beehive(self, beehive):
        """Обработчик события 'остановка у улья' """
        pass


class BeeHive(BaseSprite, HoneyHolder):
    """Улей. Стоит там где поставили и содержит мёд."""
    _img_file_name = 'beehive.png'

    def __init__(self, pos=None, max_honey=4000):
        """создать улей в указанной точке экрана"""
        BaseSprite.__init__(self, pos)
        HoneyHolder.__init__(self, 0, max_honey)
        self.honey_meter = HoneyMeter(pos=(pos[0] - 24, pos[1] - 37))

    def move(self, direction):
        """Заглушка - улей не может двигаться"""
        pass

    def move_at(self, target_pos):
        """Заглушка - улей не может двигаться"""
        pass

    def update(self):
        """Внутренняя функция для обновления переменных отображения"""
        self.honey_meter.set_value(self.honey)
        HoneyHolder._update(self)
        BaseSprite.update(self)


class Flower(BaseSprite, HoneyHolder):
    """Цветок. Источник мёда."""
    _img_file_name = 'romashka.png'

    def __init__(self, pos=None):
        """Создать цветок в указанном месте.
        Если не указано - то в произвольном месте в квадрате ((200,200),(край экрана - 50,край экрана - 50))"""
        if not pos:
            pos = (random.randint(200, SCREENRECT.width - 50), random.randint(200, SCREENRECT.height - 50))
        BaseSprite.__init__(self, pos)
        honey = random.randint(100, 200)
        HoneyHolder.__init__(self, honey, honey)

    def move(self, direction):
        """Заглушка - цветок не может двигаться"""
        pass

    def move_at(self, target_pos):
        """Заглушка - цветок не может двигаться"""
        pass

    def update(self):
        """Внутренняя функция для обновления переменных отображения"""
        HoneyHolder._update(self)
        BaseSprite.update(self)


class Scene:
    """Сцена игры. Содержит статичные элементы"""
    _flower_size = 100
    _behive_size = 50
    _flower_jitter = 0.72
    beehives = []

    def __init__(self, flowers_count=5, beehives_count=1, speed=5):
        self._place_flowers(flowers_count)
        self._place_beehives(beehives_count)
        self._set_game_speed(speed)

    def _place_flowers(self, flowers_count):
        field_width = SCREENRECT.width - self._flower_size * 2
        field_height = SCREENRECT.height - self._flower_size * 2 - self._behive_size
        if field_width < 100 or field_height < 100:
            raise Exception("Too little field...")
#        print "field", field_width, field_height

        cell_size = int(round(sqrt(float(field_width * field_height) / flowers_count)))
        while True:
            cells_in_width = int(round(field_width / cell_size))
            cells_in_height = int(round(field_height / cell_size))
            cells_count = cells_in_width * cells_in_height
            if cells_count >= flowers_count:
                break
            cell_size -= 1
        cell_numbers = [i for i in range(cells_count)]
#        print "cells: size", cell_size, "count", cells_count, "in w/h", cells_in_width, cells_in_height

        field_width = cells_in_width * cell_size
        field_height = cells_in_height * cell_size
        x0 = int((SCREENRECT.width - field_width) / 2)
        y0 = int((SCREENRECT.height - field_height) / 2) + self._behive_size
#        print "field", field_width, field_height, x0, y0

        min_random = int((1.0 - self._flower_jitter) * (cell_size / 2.0))
        max_random = cell_size - min_random

        self.flowers = []
        while len(self.flowers) < flowers_count:
            cell_number = random.choice(cell_numbers)
            cell_numbers.remove(cell_number)
            cell_x = (cell_number % cells_in_width) * cell_size
            cell_y = (cell_number // cells_in_width) * cell_size
            dx = random.randint(min_random, max_random)
            dy = random.randint(min_random, max_random)
            pos = Point(x0 + cell_x + dx, y0 + cell_y + dy)
            self.flowers.append(Flower(pos))
        Bee.flowers = self.flowers

    def _place_beehives(self, beehives_count):
        max_honey = 0
        for flower in self.flowers:
            max_honey += flower.honey
        if beehives_count in (1, 2):
            if beehives_count == 2:
                max_honey /= 2.0
            max_honey = int(round((max_honey / 1000.0) * 1.3)) * 1000
            if max_honey < 1000:
                max_honey = 1000
            Scene.beehives.append(BeeHive(pos=(90, 75), max_honey=max_honey))
            if beehives_count == 2:
                self.beehives.append(BeeHive(pos=(SCREENRECT.width - 90, 75), max_honey=max_honey))
        else:
            raise Exception("Only 2 beehives!")

    @classmethod
    def get_beehive(cls, team):
        # TODO сделать автоматическое распределение ульев - внизу, по кол-ву команд
        try:
            return cls.beehives[team - 1]
        except IndexError:
            return cls.beehives[0]

    def _set_game_speed(self, speed):
        if speed > NEAR_RADIUS:
            speed = NEAR_RADIUS
        BaseSprite.speed = speed
        honey_speed = int(speed / 2.0)
        if honey_speed < 1:
            honey_speed = 1
        HoneyHolder.honey_speed = honey_speed


def load_image(name, colorkey=None):
    """Загрузить изображение из файла"""
    fullname = os.path.join('data', name)
    try:
        image = pygame.image.load(fullname)
    except pygame.error, message:
        print "Cannot load image:", name
        raise SystemExit(message)
        #image = image.convert()
    if colorkey is not None:
        if colorkey is -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey, RLEACCEL)
    return image


class Point():
    """Класс точки на экране"""

    int_x = property(lambda self: round(self.x), doc="Округленная до пиксела координата X")
    int_y = property(lambda self: round(self.y), doc="Округленная до пиксела координата Y")

    def __init__(self, arg1=0, arg2=0):
        """Создать точку. Можно создать из другой точки, из списка/тьюпла или из конкретных координат"""
        try:  # arg1 is Point
            self.x = arg1.x
            self.y = arg1.y
        except AttributeError:
            try:  # arg1 is tuple or list
                self.x, self.y = arg1
            except:  # arg1 & arg2 is numeric
                self.x, self.y = arg1, arg2

    def to_screen(self):
        """Преобразовать координаты к экранным"""
        return self.int_x, SCREENRECT.height - self.int_y

    def add(self, vector):
        """Прибавить вектор - точка смещается на вектор"""
        self.x += vector.dx
        self.y += vector.dy

    def sub(self, vector):
        """Вычесть вектор - точка смещается на "минус" вектор"""
        self.add(-vector)

    def distance_to(self, point2):
        """Расстояние до другой точки"""
        return sqrt(pow(self.x - point2.x, 2) + pow(self.y - point2.y, 2))

    def near(self, point2, radius=NEAR_RADIUS):
        """Признак расположения рядом с другой точкой, рядом - это значит ближе, чем радиус"""
        return self.distance_to(point2) < radius

    def __eq__(self, point2):
        """Сравнение двух точек на равенство целочисленных координат"""
        #~ if point2:
            #~ print self, point2
        if self.int_x == point2.int_x and self.int_y == point2.int_y:
            return True
        return False

    def __str__(self):
        """Преобразование к строке"""
        return 'point(%s,%s)' % (self.x, self.y)

    def __repr__(self):
        """Представление """
        return str(self)

    def __iter__(self):
        yield self.x
        yield self.y

    def __getitem__(self, ind):
        if ind:
            return self.y
        return self.x

    def __nonzero__(self):
        if self.x and self.y:
            return 1
        return 0


class Vector():
    """Класс математического вектора"""

    def __init__(self, point1=None, point2=None, direction=None, module=None, dx=None, dy=None):
        """
        Создать вектор. Можно создать из двух точек (длинной в модуль, если указан),
        а можно указать направление и модуль вектора.
        """
        self.dx = 0
        self.dy = 0

        if dx and dy:
            self.dx, self.dy = dx, dy
        elif point1 or point2:  # если заданы точки
            if not point1:
                point1 = Point(0, 0)
            if not point2:
                point2 = Point(0, 0)
            self.dx = float(point2.x - point1.x)
            self.dy = float(point2.y - point1.y)
        elif direction:  # ... или задано направление
            direction = (direction * pi) / 180
            self.dx = sin(direction)
            self.dy = cos(direction)

        self.module = self._determine_module()
        if module:  # если задана длина вектора, то ограничиваем себя :)
            if self.module:
                self.dx *= module / self.module
                self.dy *= module / self.module
            self.module = module

        self.angle = self._determine_angle()

    def add(self, vector2):
        """Сложение векторов"""
        self.dx += vector2.dx
        self.dy += vector2.dy
        self.module = self._determine_module()
        self.angle = self._determine_angle()

    def _determine_module(self):
        return sqrt(self.dx * self.dx + self.dy * self.dy)

    def _determine_angle(self):
        angle = 0
        if self.dx == 0:
            if self.dy >= 0:
                return 90
            else:
                return  270
        else:
            angle = atan(self.dy / self.dx) * (180 / pi)
            #print self.dx, self.dy, angle
            if self.dx < 0:
                angle += 180
        return angle

    def __str__(self):
        return 'vector([%.2f,%.2f],{%.2f,%.2f})' % (self.dx, self.dy, self.angle, self.module)

    def __repr__(self):
        return str(self)

    def __nonzero__(self):
        """Проверка на пустоту"""
        return int(self.module)

    def __neg__(self):
        return Vector(dx=-self.dx, dy=-self.dy)


class GameEngine:
    """Игровой движок. Выполняет все функции по отображению спрайтов и взаимодействия с пользователем"""

    def __init__(self, name, background_color=None, max_fps=60, resolution=None):
        """Создать игру. """
        global SCREENRECT

        pygame.init()
        if background_color is None:
            background_color = (87, 144, 40)
        if resolution is None:
            resolution = (1024, 768)
        SCREENRECT = Rect((0, 0), resolution)
        self.screen = pygame.display.set_mode(SCREENRECT.size)
        pygame.display.set_caption(name)

        self.background = pygame.Surface(self.screen.get_size())  # и ее размер
        self.background = self.background.convert()
        self.background.fill(background_color)  # заполняем цветом
        self.screen.blit(self.background, (0, 0))
        pygame.display.flip()

        self.all = pygame.sprite.LayeredUpdates()
        BaseSprite.containers = self.all
        Fps.containers = self.all
        HoneyMeter.containers = self.all

        global clock
        clock = pygame.time.Clock()
        self.fps_meter = Fps(color=(255, 255, 0))
        self.max_fps = max_fps

        self.debug = False

    def _draw_scene(self):
        # TODO ускорить через начальную отрисовку всех цветков и ульев в бакграунд
        # clear/erase the last drawn sprites
        self.all.clear(self.screen, self.background)
        #update all the sprites
        self.all.update()
        #draw the scene
        dirty = self.all.draw(self.screen)
        pygame.display.update(dirty)
        #cap the framerate
        clock.tick(self.max_fps)

    def _proceed_keyboard(self):
        one_step = False
        for event in pygame.event.get():
            if (event.type == QUIT) or (event.type == KEYDOWN and event.key == K_ESCAPE):
                self.halt = True
            if event.type == KEYDOWN and event.key == K_f:
                self.fps_meter.show = not self.fps_meter.show
            if event.type == KEYDOWN and event.key == K_d:
                self.debug = not self.debug
            if event.type == KEYDOWN and event.key == K_s:
                one_step = True
        if self.debug and not one_step:
            return False
        return True

    def go(self, debug=False):
        self.debug = debug
        if self.debug:
            self._draw_scene()
        self.halt = False
        while not self.halt:
            if self._proceed_keyboard():
                self._draw_scene()


class Fps(pygame.sprite.DirtySprite):
    """Отображение FPS игры"""
    _layer = 5

    def __init__(self, color=(255, 255, 255)):
        """Создать индикатор FPS"""
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.show = False
        self.font = pygame.font.Font(None, 27)
        self.color = color
        self.image = self.font.render('-', 0, self.color)
        self.rect = self.image.get_rect()
        self.rect = self.rect.move(SCREENRECT.width - 100, 10)
        self.fps = []

    def update(self):
        """Обновить значение FPS"""
        global clock
        current_fps = clock.get_fps()
        del self.fps[100:]
        self.fps.append(current_fps)
        if self.show:
            fps = sum(self.fps) / len(self.fps)
            msg = '%5.0f FPS' % fps
        else:
            msg = ''
        self.image = self.font.render(msg, 1, self.color)


class HoneyMeter(pygame.sprite.DirtySprite):
    """Отображение кол-ва мёда"""
    _layer = MAX_LAYERS

    def __init__(self, pos, color=(255, 255, 0)):
        self.containers = self.containers, SPRITES_GROUPS[self._layer]
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.font = pygame.font.Font(None, 27)
        self.color = color
        self.image = self.font.render('-', 0, self.color)
        self.rect = self.image.get_rect()
        self.rect = self.rect.move(pos[0], SCREENRECT.height - pos[1])

    def set_value(self, value):
        self.value = value

    def update(self):
        msg = '%5.0f' % self.value
        self.image = self.font.render(msg, 1, self.color)


def random_number(a=0, b=300):
    """
        Выдать случайное целое из диапазона [a,b]
    """
    return random.randint(a, b)


def _get_random_coordinate(high):
    return random_number(RANDOM_POINT_BORDER, high - RANDOM_POINT_BORDER)


def random_point():
    """
        Сгенерировать случнайную точку внутри области рисования
    """
    x = _get_random_coordinate(SCREENRECT.width)
    y = _get_random_coordinate(SCREENRECT.height)
    return Point(x, y)


class WorkerBee(Bee):
    team = 1
    all_bees = []

    def is_other_bee_target(self, flower):
        for bee in WorkerBee.all_bees:
            if hasattr(bee, 'flower') and bee.flower and bee.flower._id == flower._id:
                return True
        return False

    def get_nearest_flower(self):
        flowers_with_honey = [flower for flower in self.flowers if flower.honey > 0]
        if not flowers_with_honey:
            return None
        nearest_flower = None
        for flower in flowers_with_honey:
            if self.is_other_bee_target(flower):
                continue
            if nearest_flower is None or self.distance_to(flower) < self.distance_to(nearest_flower):
                nearest_flower = flower
        return nearest_flower

    def go_next_flower(self):
        if self.is_full():
            self.move_at(self.my_beehive)
        else:
            self.flower = self.get_nearest_flower()
            if self.flower is not None:
                self.move_at(self.flower)
            elif self.honey > 0:
                self.move_at(self.my_beehive)
            else:
                i = random_number(0, len(self.flowers) - 1)
                self.move_at(self.flowers[i])

    def on_born(self):
        WorkerBee.all_bees.append(self)
        self.go_next_flower()

    def on_stop_at_flower(self, flower):
        if flower.honey > 0:
            self.load_honey_from(flower)
        else:
            self.go_next_flower()

    def on_honey_loaded(self):
        self.go_next_flower()

    def on_stop_at_beehive(self, beehive):
        self.unload_honey_to(beehive)

    def on_honey_unloaded(self):
        self.go_next_flower()


class GreedyBee(WorkerBee):
    team = 2

    def get_nearest_flower(self):
        flowers_with_honey = [flower for flower in self.flowers if flower.honey > 0]
        if not flowers_with_honey:
            return None
        nearest_flower = None
        max_honey = 0
        for flower in flowers_with_honey:
            distance = self.distance_to(flower)
            if distance > 300:
                continue
            if flower.honey > max_honey:
                nearest_flower = flower
                max_honey = flower.honey
            elif flower.honey == max_honey:
                if nearest_flower is None:
                    nearest_flower = flower
                elif distance < self.distance_to(nearest_flower):
                    nearest_flower = flower
        if nearest_flower:
            return nearest_flower
        return random.choice(flowers_with_honey)

if __name__ == '__main__':

    game = GameEngine("My little garden", resolution=(1000, 500))
    scene = Scene(beehives_count=2, flowers_count=80, speed=40)

    bees = [WorkerBee() for i in range(10)]
    bees_2 = [GreedyBee() for i in range(10)]

    game.go(debug=False)
