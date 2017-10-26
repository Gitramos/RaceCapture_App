#
# Race Capture App
#
# Copyright (C) 2014-2017 Autosport Labs
#
# This file is part of the Race Capture App
#
# This is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the GNU General Public License for more details. You should
# have received a copy of the GNU General Public License along with
# this code. If not, see <http://www.gnu.org/licenses/>.

from kivy.uix.bubble import Bubble, BubbleButton
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.app import Builder
from kivy.logger import Logger
from kivy.metrics import sp

Builder.load_string('''
<WarnLabel>
    canvas.before:
        Color:
            rgba: (1.0, 0, 0, 0.5)
        Rectangle:
            pos: self.pos
            size: self.size
''')

class WarnLabel(Label):
    pass

class BubblePos():
    x = 0
    y = 0
    top = 0
    right = 0
    def __init__(self, **kwargs):
        self.x = kwargs.get('x', self.x)
        self.y = kwargs.get('y', self.y)
        self.right = kwargs.get('right', self.right)
        self.top = kwargs.get('top', self.top)

class CenteredBubble(Bubble):
            
    def center_below(self, widget):
        bubble_width = self.size[0]
        bubble_height = self.size[1]

        pos = widget.center
        x = pos[0]
        y = widget.top
        half_width = bubble_width / 2
        x = x - half_width

        window = widget.get_root_window()
        if x < 0: x = 0
        if x > window.width: x = window.width - bubble_width
        if y - bubble_height < 0: y = bubble_height
        if y > window.height: y = window.height - bubble_height
        self.x = x
        self.y = y

    def center_above(self, widget):
        bubble_width = self.size[0]
        bubble_height = self.size[1]
        
        pos = widget.center
        pos = widget.to_window(*pos)
        x = pos[0]
        y = pos[1]
        x = x - (bubble_width / 2)

        window = widget.get_root_window()
        if x < 0: x = 0
        if x > window.width: x = window.width - bubble_width
        if y > window.height: y = window.height - bubble_height
        self.x = x
        self.y = y

    def center_on(self, widget):
        bubble_width = self.size[0]
        bubble_height = self.size[1]
        
        pos = widget.center
        pos = widget.to_window(*pos)
        x = pos[0]
        y = pos[1]
        half_width = bubble_width / 2
        half_height = bubble_height / 2
        x = x - half_width
        y = y - half_height

        window = widget.get_root_window()
        if x < 0: x = 0
        if x > window.width: x = window.width - bubble_width
        if y > window.height: y = window.height - bubble_height
        self.x = x
        self.y = y
        
        
    def center_on_limited(self, widget):
                        
        bubble_width = self.size[0]
        bubble_height = self.size[1]
        
        
        center = widget.center
        x = center[0]
        y = center[1]
        half_width = bubble_width / 2
        half_height = bubble_height / 2
        x = x - half_width
        y = y - half_height
        
        window = widget.get_root_window()
        if window is not None:
            if x < 0: x = 0
            if x > window.width: x = window.width - bubble_width
            if y < 0: y = 0
            if y > window.height: y = window.height - bubble_height
        
            self.limit_to = BubblePos(x=x,y=y,top=y + bubble_height, right=x + bubble_width)            
        
    def dismiss(self):
        try:
            self.parent.remove_widget(self)
        except:
            pass
        
    def auto_dismiss_timeout(self, timeout):
        Clock.schedule_once(lambda dt: self.dismiss(), timeout)
