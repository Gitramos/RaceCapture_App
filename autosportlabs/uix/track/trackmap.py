import kivy
import math
kivy.require('1.9.0')
from kivy.uix.label import Label
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.widget import Widget
from kivy.uix.scatter import Scatter
from kivy.graphics import Rectangle
from kivy.app import Builder
from kivy.metrics import sp
from kivy.graphics import Color, Line
from autosportlabs.racecapture.geo.geopoint import GeoPoint
from utils import *

Builder.load_file('autosportlabs/uix/track/trackmap.kv')

class Point(object):
    x = 0.0
    y = 0.0
    def __init__(self, x, y):
        self.x = x
        self.y = y
    
class MarkerPoint(Point):
    def __init__(self, color):
        super(MarkerPoint, self).__init__(0, 0)
        self.color = color
    
class TrackPath(object):
    def __init__(self, path, color):
        self.color = color
        self.path = path

class TrackMap(Widget):
    trackWidthScale = 0.01
    marker_width_scale = 0.02
    path_width_scale = 0.002
    trackColor = (1.0, 1.0, 1.0, 0.5)
    MIN_PADDING = sp(1)
    offsetPoint = Point(0,0)
    globalRatio = 0
    heightPadding = 0
    widthPadding = 0
    
    minXY = Point(-1, -1)
    maxXY = Point(-1, -1)

    #The trackmap
    mapPoints = []
    scaled_map_points = []

    #The map paths
    paths = {}
    scaled_paths = {}
    
    #markers for trackmap
    marker_points = {}
    
    def set_trackColor(self, color):
        self.trackColor = color
        self.update_map()
        
    def get_trackColor(self):
        return self.trackColor
        
    trackColor = property(get_trackColor, set_trackColor)

    def __init__(self, **kwargs):
        super(TrackMap, self).__init__(**kwargs)
        self.bind(pos=self.update_map)
        self.bind(size=self.update_map)

    def add_path(self, key, path, color):
        points = []
        for geo_point in path:
            point = self._project_point(geo_point)
            points.append(point);

        min_x = self.minXY.x
        min_y = self.minXY.y

        for point in points:
            point.x = point.x - min_x
            point.y = point.y - min_y

        self.paths[key] = TrackPath(points, color)
        self.update_map()

    def remove_path(self, key):
        self.paths.pop(key, None)
        self.scaled_paths.pop(key, None)
        self._draw_current_map()

    def add_marker(self, key, color):
        self.marker_points[key] = MarkerPoint(color)

    def remove_marker(self, key):
        if self.marker_points.get(key):
            del self.marker_points[key]
            self._draw_current_map()

    def get_marker(self, key):
        return self.marker_points.get(key)

    def update_marker(self, key, geoPoint):
        marker_point = self.marker_points.get(key)
        if marker_point is not None:
            point = self._offset_point(self._project_point(geoPoint))
            marker_point.x = point.x
            marker_point.y = point.y
            self._draw_current_map()
        
    def update_map(self, *args):
        
        paddingBothSides = self.MIN_PADDING * 2
        
        width = self.size[0] 
        height = self.size[1]
        
        left = self.pos[0]
        bottom = self.pos[1]
        
        # the actual drawing space for the map on the image
        mapWidth = width - paddingBothSides;
        mapHeight = height - paddingBothSides;

        #determine the width and height ratio because we need to magnify the map to fit into the given image dimension
        mapWidthRatio = float(mapWidth) / float(self.maxXY.x)
        mapHeightRatio = float(mapHeight) / float(self.maxXY.y)

        # using different ratios for width and height will cause the map to be stretched. So, we have to determine
        # the global ratio that will perfectly fit into the given image dimension
        self.globalRatio = min(mapWidthRatio, mapHeightRatio);

        #now we need to readjust the padding to ensure the map is always drawn on the center of the given image dimension
        self.heightPadding = (height - (self.globalRatio * self.maxXY.y)) / 2.0
        self.widthPadding = (width - (self.globalRatio * self.maxXY.x)) / 2.0
        self.offsetPoint = self.minXY;
        
        #track outline
        points = self.mapPoints
        scaled_map_points = []
        for point in points:
            scaledPoint = self.scalePoint(point, self.height, left, bottom)
            scaled_map_points.append(scaledPoint.x)
            scaled_map_points.append(scaledPoint.y)
        self.scaled_map_points = scaled_map_points

        paths = self.paths
        scaled_paths = {}
        for key, track_path in paths.iteritems():
            scaled_path_points = []
            for point in track_path.path:
                scaled_path_point = self.scalePoint(point, self.height, left, bottom)
                scaled_path_points.append(scaled_path_point.x)
                scaled_path_points.append(scaled_path_point.y)
            scaled_paths[key] = scaled_path_points

        self.scaled_paths = scaled_paths
        self._draw_current_map()

    def _draw_current_map(self):
        left = self.pos[0]
        bottom = self.pos[1]        
        self.canvas.clear()
        with self.canvas:
            #draw the main track map
            Color(*self.trackColor)
            Line(points=self.scaled_map_points, width=sp(self.trackWidthScale * self.height), closed=True, joint='round')
            marker_size = self.marker_width_scale * self.height

            #draw all of the traces
            for key, path in self.scaled_paths.iteritems():
                Color(*self.paths[key].color)
                Line(points=path, width=sp(self.path_width_scale * self.height), closed=True)

            #draw the markers
            for marker_point in self.marker_points.itervalues():
                scaledPoint = self.scalePoint(marker_point, self.height, left, bottom)                
                Color(*marker_point.color)
                Line(circle=(scaledPoint.x, scaledPoint.y, marker_size), width=marker_size, closed=True)

         
    def setTrackPoints(self, geoPoints):
        self.genMapPoints(geoPoints)
        self.update_map()
        
    def _offset_point(self, point):
        point.x = point.x - self.minXY.x
        point.y = point.y - self.minXY.y
        return point
        
    def _project_point(self, geoPoint):
        latitude = geoPoint.latitude * float(math.pi / 180.0)
        longitude = geoPoint.longitude * float(math.pi / 180.0)
        point = Point(longitude, float(math.log(math.tan((math.pi / 4.0) + 0.5 * latitude))))
        return point;

    def scalePoint(self, point, height, left, bottom):
        adjustedX = int((self.widthPadding + (point.x * self.globalRatio))) + left
        #need to invert the Y since 0,0 starts at top left
        adjustedY = int((self.heightPadding + (point.y * self.globalRatio))) + bottom
        return Point(adjustedX, adjustedY)

    def genMapPoints(self, geoPoints):
        points = []
        
        # min and max coordinates, used in the computation below
        minXY = Point(-1, -1)
        maxXY = Point(-1, -1)
        
        for geoPoint in geoPoints:
            point = self._project_point(geoPoint)
            minXY.x = point.x if minXY.x == -1 else min(minXY.x, point.x)
            minXY.y = point.y if minXY.y == -1 else min(minXY.y, point.y)
            points.append(point);
        
        # now, we need to keep track the max X and Y values
        for point in points:
            point.x = point.x - minXY.x
            point.y = point.y - minXY.y
            maxXY.x = point.x if maxXY.x == -1 else max(maxXY.x, point.x)
            maxXY.y = point.y if maxXY.y == -1 else max(maxXY.y, point.y);
                
        self.minXY = minXY
        self.maxXY = maxXY                
        self.mapPoints =  points        
        
        
