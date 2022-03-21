import pygame
import numpy as np
from icecream import ic as print
import socket
import threading
import time

import sys
from os.path import join, dirname
sys.path.insert(0, join(dirname(__file__), '../'))
from informer import Informer
from proto.python_out import marker_pb2, geometry_msgs_pb2, path_msgs_pb2, cmd_msgs_pb2
from config_5g import cfg_server


HOST_ADDRESS = '127.0.0.1'
BLACK = (0, 0, 0)
GREY = (192, 192, 192)
BLUE = (0, 0, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
WHITE = (255, 255, 255)
WINDOW_WIDTH = 2000
WINDOW_HEIGHT = 2000
ROBOT_SIZE = 10
BUTTON_WIDTH = 300
BUTTON_HEIGHT = 100
BUTTON_LIGHT = (170, 170, 170)
BUTTON_DARK = (100, 100, 100)
BUTTON_GOAL_X = 50
BUTTON_GOAL_Y = 50
BUTTON_LASER_X = 50
BUTTON_LASER_Y = 200
BUTTON_BAIDU_X = 50
BUTTON_BAIDU_Y = 350
BUTTON_SATELLITE_X = 50
BUTTON_SATELLITE_Y = 500
# read map
LASER_MAP = pygame.image.load('./maps/laser_map.jpg')
BAIDU_MAP = pygame.image.load('./maps/baidu_map.png')
SATELLITE_MAP = pygame.image.load('./maps/satellite_map.png')
DISPLAY_MAP = LASER_MAP
map_offset = np.array([0, 0])
robot_goal = None
robot_pos = []
bounding_box = []
path_pos = []
# flags
map_draging = False
goal_setting = False

class Receiver(object):
    def __init__(self, addr=HOST_ADDRESS, port=23333):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addr = addr
        self.port = port
        self.sock.settimeout(1.0)
        self.sock.bind((self.addr, self.port))
        self.thread = threading.Thread(target=self.receive_data)
        self.thread.start()
        self.timeout = False

    def receive_data(self):
        while True:
            try:
                data, _ = self.sock.recvfrom(4096)
                data = data.decode("utf-8").split(';')
                MAP_WIDTH, MAP_HEIGHT = DISPLAY_MAP.get_size()
                offset = np.array([WINDOW_WIDTH//2 - MAP_WIDTH//2, WINDOW_HEIGHT//2 - MAP_HEIGHT//2])
                global path_pos
                path_pos = [np.array([float(pos.split(',')[0]), float(pos.split(',')[1])]) + offset
                            for pos in data if pos != '']
                print(path_pos, len(path_pos))
                self.timeout = False
            except socket.timeout:
                self.timeout = True
            time.sleep(0.01)
            
def parse_message(message):
    global bounding_box
    bounding_box = []
    marker_list = marker_pb2.MarkerList()
    marker_list.ParseFromString(message)
    for marker in marker_list.marker_list:
        bounding_box.append(marker.pose.position.x, marker.pose.position.y)

def parse_odometry(message):
    global robot_pos
    odometry = geometry_msgs_pb2.Pose()
    odometry.ParseFromString(message)
    robot_pos = [[odometry.position.x, odometry.position.y]]

def parse_cmd(message):
    global global_cmd
    cmd = cmd_msgs_pb2.Cmd()
    cmd.ParseFromString(message)
    global_cmd = cmd

def send_path(server, path_list):
    path = path_msgs_pb2.Path()
    for i in range(len(path_list)):
        pose = path_msgs_pb2.Pose2D()
        pose.x = path_list[i][0]
        pose.y = path_list[i][0]
        pose.theta = path_list[i][0]

        path.poses.append(pose)

    sent_data = path.SerializeToString()
    print('send', len(sent_data))
    server.send_path(sent_data)

class Server(Informer):
    def msg_recv(self):
        self.recv('msg', parse_message)

    def odm_recv(self):
        self.recv('odm', parse_odometry)

    def send_path(self, message):
        self.send(message, 'path')

def sendGoal(goal):
    print(goal, type(goal))
    goal_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    goal_sock.sendto(bytes(str(goal[0]) + ',' + str(goal[1]), 'ascii'), (HOST_ADDRESS, 23334))

def screen2pos(x, y):
    MAP_WIDTH, MAP_HEIGHT = DISPLAY_MAP.get_size()
    pos = np.array([x, y]) - np.array([WINDOW_WIDTH//2 - MAP_WIDTH//2, WINDOW_HEIGHT//2 - MAP_HEIGHT//2])
    return pos

def pos2screen(x, y):
    return x, y

def drawRobots():
    for pos in robot_pos:
        pygame.draw.circle(SCREEN, BLUE, pos + map_offset, int(ROBOT_SIZE*2))
        
def drawGoal():
    if robot_goal is not None:
        pygame.draw.circle(SCREEN, GREEN, robot_goal + map_offset, int(ROBOT_SIZE*5))

def drawBoundingBox():
    for pos in bounding_box:
        x, y = pos + map_offset
        pygame.draw.rect(SCREEN, RED, pygame.Rect(x, y, 60, 100), 10)
        
def drawPath():
    if len(path_pos) > 1:
        pygame.draw.lines(SCREEN, GREEN, False, path_pos, 10)

def drawButton():
    # font settings
    FONT = pygame.font.SysFont('Corbel', 75)

    # get mouse position
    mouse = pygame.mouse.get_pos()

    # button: set goal
    text = FONT.render('Set Goal', True, WHITE)
    if BUTTON_GOAL_X <= mouse[0] <= BUTTON_GOAL_X + BUTTON_WIDTH and BUTTON_GOAL_Y <= mouse[1] <= BUTTON_GOAL_Y + BUTTON_HEIGHT:
        pygame.draw.rect(SCREEN, BUTTON_LIGHT, [BUTTON_GOAL_X, BUTTON_GOAL_Y, BUTTON_WIDTH, BUTTON_HEIGHT])
    else:
        pygame.draw.rect(SCREEN, BUTTON_DARK, [BUTTON_GOAL_X, BUTTON_GOAL_Y, BUTTON_WIDTH, BUTTON_HEIGHT])
    SCREEN.blit(text, (BUTTON_GOAL_X+45, BUTTON_GOAL_Y+25))
    # button: laser map
    text = FONT.render('LASER', True, WHITE)
    if BUTTON_LASER_X <= mouse[0] <= BUTTON_LASER_X + BUTTON_WIDTH and BUTTON_LASER_Y <= mouse[1] <= BUTTON_LASER_Y + BUTTON_HEIGHT:
        pygame.draw.rect(SCREEN, BUTTON_LIGHT, [BUTTON_LASER_X, BUTTON_LASER_Y, BUTTON_WIDTH, BUTTON_HEIGHT])
    else:
        pygame.draw.rect(SCREEN, BUTTON_DARK, [BUTTON_LASER_X, BUTTON_LASER_Y, BUTTON_WIDTH, BUTTON_HEIGHT])
    SCREEN.blit(text, (BUTTON_LASER_X+60, BUTTON_LASER_Y+25))
    # button: baidu map
    text = FONT.render('BAIDU', True, WHITE)
    if BUTTON_BAIDU_X <= mouse[0] <= BUTTON_BAIDU_X + BUTTON_WIDTH and BUTTON_BAIDU_Y <= mouse[1] <= BUTTON_BAIDU_Y + BUTTON_HEIGHT:
        pygame.draw.rect(SCREEN, BUTTON_LIGHT, [BUTTON_BAIDU_X, BUTTON_BAIDU_Y, BUTTON_WIDTH, BUTTON_HEIGHT])
    else:
        pygame.draw.rect(SCREEN, BUTTON_DARK, [BUTTON_BAIDU_X, BUTTON_BAIDU_Y, BUTTON_WIDTH, BUTTON_HEIGHT])
    SCREEN.blit(text, (BUTTON_BAIDU_X+65, BUTTON_BAIDU_Y+25))
    # button: satellite map
    text = FONT.render('SATELLITE', True, WHITE)
    if BUTTON_SATELLITE_X <= mouse[0] <= BUTTON_SATELLITE_X + BUTTON_WIDTH and BUTTON_SATELLITE_Y <= mouse[1] <= BUTTON_SATELLITE_Y + BUTTON_HEIGHT:
        pygame.draw.rect(SCREEN, BUTTON_LIGHT, [BUTTON_SATELLITE_X, BUTTON_SATELLITE_Y, BUTTON_WIDTH, BUTTON_HEIGHT])
    else:
        pygame.draw.rect(SCREEN, BUTTON_DARK, [BUTTON_SATELLITE_X, BUTTON_SATELLITE_Y, BUTTON_WIDTH, BUTTON_HEIGHT])
    SCREEN.blit(text, (BUTTON_SATELLITE_X+10, BUTTON_SATELLITE_Y+25))

def drawMaps():
    WINDOW_WIDTH, WINDOW_HEIGHT = pygame.display.get_surface().get_size()
    MAP_WIDTH, MAP_HEIGHT = DISPLAY_MAP.get_size()
    map_pos = np.array([WINDOW_WIDTH//2 - MAP_WIDTH//2, WINDOW_HEIGHT//2 - MAP_HEIGHT//2]) + map_offset
    SCREEN.blit(DISPLAY_MAP, map_pos)


if __name__ == "__main__":
    pygame.init()
    SCREEN = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))#, pygame.RESIZABLE)
    CLOCK = pygame.time.Clock()
    SCREEN.fill(GREY)
    data_receiver = Receiver()
    try:
        server = Server(cfg_server)
    except:
        pass

    while True:
        SCREEN.fill(GREY)
        drawMaps()
        drawGoal()
        drawRobots()
        drawBoundingBox()
        drawPath()
        drawButton()

        for event in pygame.event.get():
            mods = pygame.key.get_mods()
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN and mods & pygame.KMOD_CTRL:
                if event.button == 1:            
                    map_draging = True
                    start_pos = event.pos
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # get mouse position
                mouse = pygame.mouse.get_pos()
                # button: set goal
                if BUTTON_GOAL_X <= mouse[0] <= BUTTON_GOAL_X + BUTTON_WIDTH and BUTTON_GOAL_Y <= mouse[1] <= BUTTON_GOAL_Y + BUTTON_HEIGHT:
                    goal_setting = True
                elif goal_setting:
                    goal_setting = False
                    robot_goal = mouse - map_offset
                    sendGoal(screen2pos(*robot_goal))
                # button: laser map
                elif BUTTON_LASER_X <= mouse[0] <= BUTTON_LASER_X + BUTTON_WIDTH and BUTTON_LASER_Y <= mouse[1] <= BUTTON_LASER_Y + BUTTON_HEIGHT:
                    DISPLAY_MAP = LASER_MAP
                # button: baidu map
                elif BUTTON_BAIDU_X <= mouse[0] <= BUTTON_BAIDU_X + BUTTON_WIDTH and BUTTON_BAIDU_Y <= mouse[1] <= BUTTON_BAIDU_Y + BUTTON_HEIGHT:
                    DISPLAY_MAP = BAIDU_MAP
                # button: satellite map
                elif BUTTON_SATELLITE_X <= mouse[0] <= BUTTON_SATELLITE_X + BUTTON_WIDTH and BUTTON_SATELLITE_Y <= mouse[1] <= BUTTON_SATELLITE_Y + BUTTON_HEIGHT:
                    DISPLAY_MAP = SATELLITE_MAP
            elif event.type == pygame.MOUSEBUTTONUP and mods & pygame.KMOD_CTRL:
                if event.button == 1:            
                    map_draging = False
            elif event.type == pygame.MOUSEMOTION and mods & pygame.KMOD_CTRL:
                if map_draging:
                    end_pos = event.pos
                    map_offset = map_offset + end_pos - start_pos
                    start_pos = end_pos

        pygame.display.update()
