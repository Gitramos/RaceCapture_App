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

import kivy
kivy.require('1.10.0')
from kivy.logger import Logger
from kivy.app import Builder
from kivy.clock import Clock
from kivy.uix.anchorlayout import AnchorLayout
from iconbutton import IconButton
from autosportlabs.racecapture.views.analysis.customizechannelsview import CustomizeChannelsView
from autosportlabs.racecapture.views.analysis.markerevent import SourceRef
from autosportlabs.racecapture.settings.prefs import UserPrefs
from kivy.uix.popup import Popup
from kivy.uix.stacklayout import StackLayout
from kivy.properties import BooleanProperty, ObjectProperty
Builder.load_file('autosportlabs/racecapture/views/analysis/analysiswidget.kv')

class OptionsButton(AnchorLayout):
    pass

class AnalysisWidget(AnchorLayout):
    """
    The base for all analysis UI widgets
    
    This base class can handle the addition / removal of laps selected for viewing.
    Selected laps are the basis for determining what data is displayed in a particular widget.
    
    Extend this class directly when you want to create a widget that specifically controls the data to be displayed, such as
    the analysis map.
    """
    options_enabled = BooleanProperty(None)
    laps_selected = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(AnalysisWidget, self).__init__(**kwargs)
        self.selected_laps = {}
        self.settings = None
        self.settings = kwargs.get('settings', None)
        self.datastore = kwargs.get('datastore', None)
        Clock.schedule_once(lambda dt: self.add_option_buttons())

    def add_option_buttons(self):
        '''
        Override this to add additional buttons to the widget's floating toolbar
        '''
        pass

    def append_option_button(self, button):
        self.ids.options_bar.add_widget(button)

    def on_options_enabled(self, instance, value):
        if value == False:
            self.remove_widget(self.ids.options_button)
        else:
            options = self.ids.options_button
            self.remove_widget(options)
            self.add_widget(options)

    def on_options(self, *args):
        pass

    def on_lap_added(self, source_ref):
        """
        Event to indicate a lap was added
        :param source_ref the lap reference
        :type source_ref string
        """
        pass

    def on_lap_removed(self, source_ref):
        """
        Indicate a lap was removed
        :param source_ref the lap reference
        :type source_ref string
        """
        pass

    def add_lap(self, source_ref):
        '''
        Add a lap specified by the source reference
        :param source_ref indicating the selected session / lap
        :type SourceRef
        '''
        self.selected_laps[str(source_ref)] = source_ref
        self.on_lap_added(source_ref)
        self.laps_selected = True

    def remove_lap(self, source_ref):
        '''
        Remove a lap specified by the source reference
        :param source_ref indicating the selected session / lap
        :type SourceRef
        '''
        self.on_lap_removed(source_ref)
        self.selected_laps.pop(str(source_ref), None)
        self.laps_selected = bool(self.selected_laps)

    def _filter_suggested_channels(self, channels):
        """
        Filter list of channels to ensure they are valid
        """
        return [c for c in channels if len(c.strip()) > 0 ]

    def _get_suggested_channels(self):
        suggested_channels = self.settings.userPrefs.get_pref_list('analysis_preferences', 'selected_analysis_channels')
        suggested_channels = self._filter_suggested_channels(suggested_channels)
        available_channels = [c.name for c in self.datastore.channel_list]
        suggested_channels = [c for c in suggested_channels if c in available_channels]
        if len(suggested_channels) == 0:
            suggested_channels = UserPrefs.DEFAULT_ANALYSIS_CHANNELS
        return suggested_channels

    def _set_suggested_channels(self, channels):
        self.settings.userPrefs.set_pref_list('analysis_preferences', 'selected_analysis_channels', channels)

class GeoAnalysisWidget(AnalysisWidget):
    """
    An analysis widget that is aware of location data
    """

    def add_reference_mark(self, source, color):
        """
        Add a reference mark for the specified source
        :param source the key representing the reference mark
        :type source string
        :param color the color of the reference mark
        :type color list
        """
        pass

    def remove_reference_mark(self, source):
        """
        Removes the specified reference mark
        :param source the key for the reference mark to remove
        :type source string
        """
        pass

    def update_reference_mark(self, source, point):
        """
        Update the specified reference mark
        :param source the key for the reference mark
        :type source string
        :param point the updated point
        :type GeoPoint
        """
        pass

    def add_map_path(self, source_ref, path, color):
        """
        Add a map path for the specified session/lap source reference
        :param source_ref the lap/session reference
        :type source_ref SourceRef
        :param path a list of points representing the map path
        :type path list
        :param color the path of the color
        :type color list
        """
        pass

    def remove_map_path(self, source_ref):
        """
        Remove the map path for the specified session/lap source reference
        :param source_ref the source session/lap reference
        :type source_ref SourceRef
        """
        pass


class ChannelAnalysisWidget(AnalysisWidget):
    """
    A base widget that can select one or more channels to display.
    
    Extend this class if you want to make a general purpose widget that shows one or more channels.
    """
    sessions = ObjectProperty(None)
    channels_selected = BooleanProperty(False)

    def __init__(self, **kwargs):
        super(ChannelAnalysisWidget, self).__init__(**kwargs)
        self._popup = None
        self.selected_channels = []
        self.register_event_type('on_channel_selected')

    def on_sessions(self, instance, value):
        self.refresh_view()

    def on_lap_added(self, source_ref):
        if len(self.selected_channels) == 0:
            suggested_channels = self._get_suggested_channels()
            self.merge_selected_channels(suggested_channels)
        else:
            self._add_unselected_channels(self.selected_channels, source_ref)

    def on_lap_removed(self, source_ref):
        for channel in self.selected_channels:
            self.remove_channel(channel, source_ref)
        self.refresh_view()

    def on_channel_selected(self, value):
        pass

    def _add_unselected_channels(self, channels, source_ref):
        '''
        Override this to add a channel / lap reference combo to the view
        '''
        pass

    def remove_channel(self, channel, source_ref):
        '''
        Override this function to remove a channel / lap reference combo from the view
        '''
        pass

    def refresh_view(self):
        '''
        Override this to refresh / re-draw the view
        '''
        pass

    def _add_channels_all_laps(self, channels):
        for source_ref in self.selected_laps.itervalues():
            self._add_unselected_channels(channels, source_ref)

    def _remove_channel_all_laps(self, channel):
        for k, v in self.selected_laps.iteritems():
            self.remove_channel(channel, k)
        self.refresh_view()

    def merge_selected_channels(self, updated_channels):
        current = self.selected_channels
        removed = [c for c in current if c not in updated_channels]
        added = [c for c in updated_channels if c not in current]

        for c in removed:
            current.remove(c)
            self._remove_channel_all_laps(c)

        for c in added:
            current.append(c)
        self._add_channels_all_laps(added)
        self.channels_selected = bool(self.selected_channels)
        self.dispatch('on_channel_selected', self.selected_channels)
        return current

    def select_channels(self, selected_channels):
        channels = self.merge_selected_channels(selected_channels)
        self._set_suggested_channels(channels)

    def _channels_customized(self, instance, updated_channels):
        self._dismiss_popup()
        self.select_channels(updated_channels)

    def on_options(self, *args):
        self.show_customize_dialog()

    def show_customize_dialog(self):
        content = CustomizeChannelsView(datastore=self.datastore, current_channels=self.selected_channels)
        content.bind(on_channels_customized=self._channels_customized)

        popup = Popup(title="Customize Channels", content=content, size_hint=(0.7, 0.7))
        popup.bind(on_dismiss=self.popup_dismissed)
        popup.open()
        self._popup = popup

    def popup_dismissed(self, *args):
        self._popup = None

    def _dismiss_popup(self, *args):
        if self._popup:
            self._popup.dismiss()
            self._popup = None
