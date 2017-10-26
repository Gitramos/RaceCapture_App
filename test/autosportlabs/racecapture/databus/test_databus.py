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

import unittest
from autosportlabs.racecapture.databus.databus import DataBus
from autosportlabs.racecapture.data.sampledata import Sample, ChannelMeta, SampleValue,\
	ChannelMetaCollection

class DataBusTest(unittest.TestCase):
	def test_update_value(self):
		dataBus = DataBus()

		sample = Sample()
		
		meta = ChannelMeta(name='RPM')
		sample.channel_metas = [meta]
		sample.samples = [SampleValue(1234, meta)]
		
		dataBus.update_samples(sample)
		dataBus.notify_listeners(None)
		
		value = dataBus.getData('RPM')
		self.assertEqual(value, 1234)

	listenerVal0 = None
	def test_listener(self):
		
		def listener(value):
			self.listenerVal0 = value

		sample = Sample()
		
		meta = ChannelMeta(name='RPM')
		sample.channel_metas = [meta]
		sample.samples = [SampleValue(1111, meta)]


		dataBus = DataBus()
		dataBus.addChannelListener('RPM', listener)
		dataBus.update_samples(sample)
		dataBus.notify_listeners(None)
		self.assertEqual(self.listenerVal0, 1111)
	
	listenerVal1 = None
	listenerVal2 = None
	def test_multiple_listeners(self):
		def listener1(value):
			self.listenerVal1 = value

		def listener2(value):
			self.listenerVal2 = value
			
		dataBus = DataBus()
		dataBus.addChannelListener('RPM', listener1)
		dataBus.addChannelListener('RPM', listener2)
		
		sample = Sample()
		meta = ChannelMeta(name='RPM')
		sample.channel_metas = [meta]
		sample.samples = [SampleValue(1111, meta)]
		
		dataBus.update_samples(sample)
		dataBus.notify_listeners(None)
		self.assertEqual(self.listenerVal1, 1111)
		self.assertEqual(self.listenerVal2, 1111)
		
	listenerVal3 = None
	listenerVal4 = None
	def test_mixed_listeners(self):
		def listener3(value):
			self.listenerVal3 = value

		def listener4(value):
			self.listenerVal4 = value
			
			
		sample = Sample()
		metaRpm = ChannelMeta(name='RPM')
		metaEngineTemp = ChannelMeta(name='EngineTemp')
		sample.channel_metas = [metaRpm, metaEngineTemp]
		sample.samples = [SampleValue(1111, metaRpm)]
			
		dataBus = DataBus()
		dataBus.addChannelListener('RPM', listener3)
		dataBus.addChannelListener('EngineTemp', listener4)
		dataBus.update_samples(sample)
		dataBus.notify_listeners(None)
		#ensure we don't set the wrong listener
		self.assertEqual(self.listenerVal3, 1111)
		self.assertEqual(self.listenerVal4, None)
		
		sample.samples = [SampleValue(1111, metaRpm), SampleValue(199, metaEngineTemp)]
		
		dataBus.update_samples(sample)
		dataBus.notify_listeners(None)
		#ensure we don't affect unrelated channels
		self.assertEqual(self.listenerVal3, 1111)
		self.assertEqual(self.listenerVal4, 199)
		
	def test_no_listener(self):

		sample = Sample()
		meta = ChannelMeta(name='EngineTemp')
		sample.channel_metas = [meta]
		sample.samples = [SampleValue(200, meta)]
		
		dataBus = DataBus()
		dataBus.update_samples(sample)
		dataBus.notify_listeners(None)
		#no listener for this channel, should not cause an error
	
	channelMeta = None
	def test_meta_listener(self):
		dataBus = DataBus()
		
		def metaListener(channel):
			self.channelMeta = channel

		metas = ChannelMetaCollection()
		metas.channel_metas = [ChannelMeta(name='RPM')]

		dataBus.addMetaListener(metaListener)
		dataBus.update_channel_meta(metas)
		dataBus.notify_listeners(None)
		self.assertEqual(self.channelMeta['RPM'], metas.channel_metas[0])
		
def main():
	unittest.main()

if __name__ == "__main__":
	main()
