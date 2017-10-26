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
kivy.require('1.9.1')
from kivy.properties import ObjectProperty, ListProperty, StringProperty, NumericProperty
from kivy.app import Builder
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.boxlayout import BoxLayout
from kivy.graphics.transformation import Matrix
from kivy.uix.screenmanager import Screen, SwapTransition
from kivy.uix.popup import Popup
from autosportlabs.racecapture.views.analysis.analysispage import AnalysisPage
from autosportlabs.uix.track.racetrackview import RaceTrackView
from autosportlabs.racecapture.geo.geopoint import GeoPoint
from autosportlabs.racecapture.datastore import Filter
from autosportlabs.widgets.scrollcontainer import ScrollContainer
from autosportlabs.racecapture.views.util.viewutils import format_laptime
from iconbutton import IconButton, LabelIconButton
from autosportlabs.uix.legends.laplegends import GradientLapLegend, LapLegend
from autosportlabs.uix.options.optionsview import OptionsView, BaseOptionsScreen
from autosportlabs.racecapture.views.channels.channelselectview import ChannelSelectView

# The scaling we use while we zoom
ANALYSIS_MAP_ZOOM_SCALE = 1.1
class AnalysisMap(AnalysisPage):
    """
    Displays a track map with options
    """
    Builder.load_string('''
<AnalysisMap>:
    options_enabled: True
    canvas.before:
        Color:
            rgba: ColorScheme.get_dark_background_translucent()
        Rectangle:
            pos: self.pos
            size: self.size

    Scatter:
        id: scatter
        auto_bring_to_front: False
        TrackMapView:
            id: track
            height: root.height
            width: root.width

    AnchorLayout:
        anchor_x: 'right'
        anchor_y: 'top'
        BoxLayout:
            orientation: 'horizontal'
            size_hint: (0.9, 1.0)
            AnchorLayout:
                id: top_bar
                size_hint_x: 0.75
                anchor_y: 'top'
                anchor_x: 'center'
                BoxLayout:
                    size_hint: (1.0, 0.1)
                    canvas.before:
                        Color:
                            rgba: ColorScheme.get_widget_translucent_background()
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    orientation: 'horizontal'
                    FieldLabel:
                        halign: 'center'
                        font_size: self.height * 0.8
                        id: track_name
            BoxLayout:
                id: legend_box
                orientation: 'vertical'
                size_hint_x: 0.4

                width: min(dp(300), 0.35 * root.width)
                BoxLayout:
                    canvas.before:
                        Color:
                            rgba: ColorScheme.get_widget_translucent_background()
                        Rectangle:
                            pos: self.pos
                            size: self.size
                    orientation: 'horizontal'
                    size_hint_y: 0.1
                    BoxLayout:
                        size_hint_x: 0.4
                    FieldLabel:
                        id: heat_channel_name
                        halign: 'center'
                        font_size: self.height * 0.8
                        size_hint_x: 0.6
                BoxLayout:
                    size_hint_y: 0.9
                    ScrollContainer:
                        id: scroller
                        do_scroll_x: False
                        do_scroll_y: True
                        GridLayout:
                            cols: 1
                            size_hint_y: None
                            height: max(self.minimum_height, scroller.height)
                            id: legend_list
                            padding: (sp(5), sp(5))
                            row_default_height: root.height * 0.12
                            row_force_default: True
                            canvas.before:
                                Color:
                                    rgba: ColorScheme.get_widget_translucent_background()
                                Rectangle:
                                    pos: self.pos
                                    size: self.size
    ''')

    SCROLL_FACTOR = 0.15
    track_manager = ObjectProperty(None)
    datastore = ObjectProperty(None)
    settings = ObjectProperty(None)

    def __init__(self, **kwargs):
        super(AnalysisMap, self).__init__(**kwargs)
        # Main settings
        self.track = None

        # State settings
        self.got_mouse = False
        self.heatmap_channel = None
        self.heatmap_channel_units = ''

        self.sources = {}
        Window.bind(on_motion=self.on_motion)


    def on_settings(self, instance, value):
        # initialize our preferences
        value.userPrefs.init_pref_section('analysis_map')

    def get_pref_track_selections(self):
        return self.settings.userPrefs.get_pref_list('analysis_map', 'track_selections')

    def set_pref_track_selections(self, selections):
        self.settings.userPrefs.set_pref_list('analysis_map', 'track_selections', selections)

    def refresh_view(self):
        self._refresh_lap_legends()

    def add_option_buttons(self):
        """
        Add additional buttons needed by this widget
        """
        self.append_option_button(IconButton(size_hint_x=0.15, text=u'\uf0b2', on_press=self.on_center_map))

    def on_center_map(self, *args):
        """
        Restore the track map to the default position/zoom/rotation
        """
        scatter = self.ids.scatter
        scatter.scale = 1
        scatter.rotation = 0
        scatter.transform = Matrix().translate(self.pos[0], self.pos[1], 0)


    def on_options(self, *args):
        self.got_mouse = False
        self.show_customize_dialog()

    def _set_heat_map(self, heatmap_channel):
        current_heatmap_channel = self.heatmap_channel

        for source in self.sources.itervalues():
            if current_heatmap_channel != heatmap_channel:
                self.remove_heat_values(source)
                if heatmap_channel:
                    self.add_heat_values(heatmap_channel, source)

        self.heatmap_channel = heatmap_channel
        self._refresh_lap_legends()
        self._update_legend_box_layout()

    def _update_legend_box_layout(self):
        """
        This will set the size of the box that contains
        the lap legend widgets
        """
        if self.heatmap_channel:
            self.ids.top_bar.size_hint_x = 0.6
            self.ids.legend_box.size_hint_x = 0.4
            units = self.heatmap_channel_units
            self.ids.heat_channel_name.text = '{} {}'.format(self.heatmap_channel, '' if len(units) == 0 else '({})'.format(units))
        else:
            self.ids.top_bar.size_hint_x = 0.75
            self.ids.legend_box.size_hint_x = 0.4
            self.ids.heat_channel_name.text = ''

    def _save_selected_trackmap(self, track):
        # save the selected track in preferences so it is remembered
        # for next time a track is selected in the nearby area.
        saved_tracks = self.get_pref_track_selections()

        nearby_tracks = self.track_manager.find_nearby_tracks(track.centerpoint)

        # we only want one selected track map set in a nearby area'.
        # if we find any previously saved tracks in the list of nearby tracks,
        # remove it.
        for nearby_track in nearby_tracks:
            if nearby_track.track_id in saved_tracks:
                # cull any other nearby tracks;
                # we will replace it with our selected track
                saved_tracks.remove(nearby_track.track_id)

        # ok, now add our selection
        saved_tracks.append(track.track_id)

        self.set_pref_track_selections(saved_tracks)

    def _update_trackmap(self, track_id):
        track = self.track_manager.get_track_by_id(track_id)
        if track is None:
            return

        self._save_selected_trackmap(track)
        self._select_track(track)

    def _select_track(self, track):
        if track != None:
            self.ids.track.setTrackPoints(track.map_points)
            self.ids.track_name.text = track.full_name
        else:
            self.ids.track_name.text = ''
            self.ids.track.setTrackPoints([])
        self.track = track

    def _customized(self, instance, values):
        self._update_trackmap(values.track_id)
        self._set_heat_map(values.heatmap_channel)

    def show_customize_dialog(self):
        """
        Display the customization dialog for this widget
        """

        current_track_id = None if self.track == None else self.track.track_id
        params = CustomizeParams(settings=self.settings, datastore=self.datastore, track_manager=self.track_manager)
        values = CustomizeValues(heatmap_channel=self.heatmap_channel, track_id=current_track_id)

        content = OptionsView(values)
        content.add_options_screen(CustomizeHeatmapView(name='heat', params=params, values=values), HeatmapButton())
        content.add_options_screen(CustomizeTrackView(name='track', params=params, values=values), TrackmapButton())

        popup = Popup(title="Customize Track Map", content=content, size_hint=(0.7, 0.7))
        content.bind(on_customized=self._customized)
        content.bind(on_close=lambda *args:popup.dismiss())
        popup.open()

    def on_touch_down(self, touch):
        self.got_mouse = True
        return super(AnalysisMap, self).on_touch_down(touch)

    def on_touch_up(self, touch):
        self.got_mouse = False
        return super(AnalysisMap, self).on_touch_up(touch)

    def on_motion(self, instance, event, motion_event):
        if self.got_mouse and motion_event.x > 0 and motion_event.y > 0 and self.collide_point(motion_event.x, motion_event.y):
            scatter = self.ids.scatter
            try:
                button = motion_event.button
                scale = scatter.scale
                if button == 'scrollup':
                    scale += self.SCROLL_FACTOR
                else:
                    if button == 'scrolldown':
                        scale -= self.SCROLL_FACTOR
                if scale < self.SCROLL_FACTOR:
                    scale = self.SCROLL_FACTOR
                scatter.scale = scale
                marker_scale = 1
                if scale > 1:
                    # adjust the scale only if we're zooming beyond 1x
                    marker_scale = ANALYSIS_MAP_ZOOM_SCALE / scale
                self.ids.track.marker_scale = marker_scale
            except:
                pass  # no scrollwheel support

    def select_map(self, latitude, longitude):
        """
        Find and display a nearby track by latitude / longitude
        The selection will favor a previously selected track in the nearby area
        :param latitude
        :type  latitude float
        :param longitude
        :type longitude float
        :returns the selected track, or None if there are no nearby tracks
        :type Track 
        """

        if not latitude or not longitude:
            return None

        point = GeoPoint.fromPoint(latitude, longitude)
        nearby_tracks = self.track_manager.find_nearby_tracks(point)

        saved_tracks = self.get_pref_track_selections()

        saved_nearby_tracks = [t for t in nearby_tracks if t.track_id in saved_tracks]

        # select the saved nearby track or just a nearby track
        track = next(iter(saved_nearby_tracks), None)
        track = next(iter(nearby_tracks), None) if track is None else track

        if self.track != track:
            # only update the trackmap if it's changing
            self._select_track(track)
        return track

    def remove_reference_mark(self, source):
        self.ids.track.remove_marker(source)

    def add_reference_mark(self, source, color):
        self.ids.track.add_marker(source, color)

    def update_reference_mark(self, source, point):
        self.ids.track.update_marker(str(source), point)

    def add_map_path(self, source_ref, path, color):
        source_key = str(source_ref)
        self.sources[source_key] = source_ref
        self.ids.track.add_path(source_key, path, color)
        if self.heatmap_channel:
            self.add_heat_values(self.heatmap_channel, source_ref)

        self._refresh_lap_legends()

    def remove_map_path(self, source_ref):
        source_key = str(source_ref)
        self.ids.track.remove_path(source_key)
        self.sources.pop(source_key, None)

        self._refresh_lap_legends()

    def _add_heat_value_results(self, channel, source_ref, query_data):
        """
        Callback for adding channel data from the heat values
        :param channel the channel fetched
        :type channel string
        :param source_ref the session / lap reference
        :type source_ref SourceRef
        :param query_data the data results
        :type query_data ChannelData
        """
        source_key = str(source_ref)
        values = query_data[channel].values
        channel_info = self.datastore.get_channel(channel)
        self.ids.track.set_heat_range(channel_info.min, channel_info.max)
        self.ids.track.add_heat_values(source_key, values)

    def add_heat_values(self, channel, source_ref):
        """
        Add heat values to the track map
        :param channel the channel for the selected heat values
        :type channel string
        :param source_ref the source session/lap reference
        :type source_ref SourceRef
        """
        def get_results(results):
            Clock.schedule_once(lambda dt: self._add_heat_value_results(channel, source_ref, results))
        self.datastore.get_channel_data(source_ref, [channel], get_results)

    def remove_heat_values(self, source_ref):
        """
        Remove the heat values for the specified source reference
        :param source_ref the session/lap reference
        :type source_ref SourceRef
        """
        source_key = str(source_ref)
        self.ids.track.remove_heat_values(source_key)

    def _refresh_lap_legends(self):
        """
        Wholesale refresh the list of lap legends
        """
        self.ids.legend_list.clear_widgets()

        height_pct = 0.4
        for source_ref in self.sources.itervalues():
            source_key = str(source_ref)
            # specify the heatmap color if multiple laps are selected, else use the default
            # multi-color heatmap for a single lap selection
            heatmap_channel = self.heatmap_channel
            source_key = str(source_ref)
            session_info = self.datastore.get_session_by_id(source_ref.session)
            if session_info is None:
                continue
            if heatmap_channel:
                channel_info = self.datastore.get_channel(heatmap_channel)
                if channel_info is None:
                    continue
                self.heatmap_channel_units = channel_info.units
                lap_legend = GradientLapLegend(session=session_info.name,
                                               lap=str(source_ref.lap),
                                               min_value=channel_info.min,
                                               max_value=channel_info.max,
                                               color=None,
                                               height_pct=height_pct
                                               )
            else:
                lap = self.datastore.get_cached_lap_info(source_ref)
                if lap is None:
                    continue
                path_color = self.ids.track.get_path(source_key).color
                lap_legend = LapLegend(color=path_color,
                                       session=session_info.name,
                                       lap=str(source_ref.lap),
                                       lap_time=format_laptime(lap.lap_time))
            self.ids.legend_list.add_widget(lap_legend)
            height_pct *= 0.6


class CustomizeParams(object):
    """
    A container class for holding multiple parameter for customization dialog
    """
    def __init__(self, settings, datastore, track_manager, **kwargs):
        self.settings = settings
        self.datastore = datastore
        self.track_manager = track_manager

class CustomizeValues(object):
    """
    A container class for holding customization values
    """
    def __init__(self, heatmap_channel, track_id, **kwargs):
        self.heatmap_channel = heatmap_channel
        self.track_id = track_id

class HeatmapButton(LabelIconButton):
    Builder.load_string('''
<HeatmapButton>:
    title: 'Heat Map'
    icon_size: self.height * .9
    title_font_size: self.height * 0.6
    icon: u'\uf06d'    
    ''')

class TrackmapButton(LabelIconButton):
    Builder.load_string('''
<TrackmapButton>:
    title: 'Track Map'
    icon_size: self.height * .9
    title_font_size: self.height * 0.6
    icon: u'\uf018'    
    ''')

class CustomizeHeatmapView(BaseOptionsScreen):
    """
    The customization view for customizing the heatmap options
    """
    Builder.load_string('''
<CustomizeHeatmapView>:
    BoxLayout:
        orientation: 'vertical'
        ChannelSelectView:
            id: heatmap_channel
            size_hint_y: 0.9
            on_channel_selected: root.channel_selected(*args)
    ''')

    def __init__(self, params, values, **kwargs):
        super(CustomizeHeatmapView, self).__init__(params, values, **kwargs)

    def on_enter(self):
        if self.initialized == False:
            channels = self._get_available_channel_names()
            self.ids.heatmap_channel.selected_channel = self.values.heatmap_channel
            self.ids.heatmap_channel.available_channels = channels

    def _get_available_channel_names(self):
        available_channels = self.params.datastore.channel_list
        return [str(c) for c in available_channels]

    def channel_selected(self, instance, value):
        modified = self.values.heatmap_channel != value
        self.values.heatmap_channel = value
        if modified:
            self.dispatch('on_screen_modified')

    def channel_cleared(self, *args):
        modified = self.values.heatmap_channel == None
        self.values.heatmap_channel = None
        if modified:
            self.dispatch('on_screen_modified')

class CustomizeTrackView(BaseOptionsScreen):
    """
    The customization view for selecting a track to display
    """
    Builder.load_string('''
<CustomizeTrackView>:
    BoxLayout:
        orientation: 'vertical'
        TracksBrowser:
            trackHeight: dp(200)
            multi_select: False
            id: track_browser
            size_hint_y: 0.90    
    ''')
    track_id = StringProperty(None, allownone=True)
    def __init__(self, params, values, **kwargs):
        super(CustomizeTrackView, self).__init__(params, values, **kwargs)
        self.ids.track_browser.set_trackmanager(self.params.track_manager)
        self.ids.track_browser.bind(on_track_selected=self.track_selected)
        self.ids.track_browser.init_view()

    def track_selected(self, instance, value):
        if type(value) is set:
            self.values.track_id = None if len(value) == 0 else next(iter(value))
        self.dispatch('on_screen_modified')
