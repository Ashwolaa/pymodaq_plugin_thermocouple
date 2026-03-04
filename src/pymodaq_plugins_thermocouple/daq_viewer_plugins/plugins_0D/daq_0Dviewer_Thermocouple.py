import numpy as np

from pymodaq_utils.utils import ThreadCommand
from pymodaq_data.data import DataToExport
from pymodaq_gui.parameter import Parameter

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins
from pymodaq_plugins_lakeshore.utils import Config
from serial.tools.list_ports import comports

config = Config()
com_ports = [port.device for port in comports()]
from pymodaq_plugins_thermocouple.hardware.thermocouple import ThermocoupleController, ThermocoupleData



class DAQ_0DViewer_Thermocouple(DAQ_Viewer_base):
    """ Instrument plugin class for a OD viewer.
    
    This object inherits all functionalities to communicate with PyMoDAQ’s DAQ_Viewer module through inheritance via
    DAQ_Viewer_base. It makes a bridge between the DAQ_Viewer module and the Python wrapper of a particular instrument.

    TODO Complete the docstring of your plugin with:
        * The set of instruments that should be compatible with this instrument plugin.
        * With which instrument it has actually been tested.
        * The version of PyMoDAQ during the test.
        * The version of the operating system.
        * Installation instructions: what manufacturer’s drivers should be installed to make it run?

    Attributes:
    -----------
    controller: object
        The particular object that allow the communication with the hardware, in general a python wrapper around the
         hardware library.
         
    # TODO add your particular attributes here if any

    """
    params = comon_parameters+[
        {'title': 'COM', 'name':  'com_port', 'type': 'list', 'limits': com_ports},
        {'title': 'Refresh time', 'name':  'refresh_time', 'type': 'int', 'value':1000,'suffix':'ms'},
        {'title': 'Thermocouples', 'name':  'channels', 'type': 'group', 'children':[]},
        ## TODO for your custom plugin: elements to be added here as dicts in order to control your custom stage
        ]

    def ini_attributes(self):
        #  TODO declare the type of the wrapper (and assign it to self.controller) you're going to use for easy
        #  autocompletion
        self.controller: ThermocoupleController = None

        #TODO declare here attributes you want/need to init with a default value
        pass

    
    def commit_settings(self, param: Parameter):
        """Apply the consequences of a change of value in the detector settings

        Parameters
        ----------
        param: Parameter
            A given parameter (within detector_settings) whose value has been changed by the user
        """
        ## TODO for your custom plugin
        if param.name() == "refresh_time":
           self.apply_settings(*self.build_settings())
        elif param.name().startswith('tc'):
            self.apply_settings(*self.build_settings())
        elif "channel" in param.name():
            self.active_channels = self.get_active_channels()
        

#        elif ...
    def get_active_channels(self) -> list:
        """Return the channel list for channels whose checkbox is currently enabled.

        Returns
        -------
        list of dict
            Subset of `self.channels` where the corresponding settings bool is True.
            Each dict contains at least 'name' and 'enabled', plus any extra keys
            defined in `channels` (address, unit, …).
        """
        return [f'channel_{index}' for index in range(self.controller.nb_tc) if self.settings.child('channels',f'channel_{index}').value()]

    
    def build_settings(self):
        """Build the settings tree"""
        refresh_time = self.settings.child('refresh_time').value()
        offsets = [self.settings.child('channels',f'channel_{i}', f'tc{i}_offset').value() for i in range(self.controller.nb_tc)]
        return refresh_time, offsets
    
    def apply_settings(self, refresh_time, offsets):
        """Apply the settings"""
        # if self.controller.is_measuring:
        #     self.controller.stop()
        self.controller.start(refresh_time, offsets)

    def ini_detector(self, controller=None):
        """Detector communication initialization

        Parameters
        ----------
        controller: (object)
            custom object of a PyMoDAQ plugin (Slave case). None if only one actuator/detector by controller
            (Master case)

        Returns
        -------
        info: str
        initialized: bool
            False if initialization failed otherwise True
        """

        # raise NotImplementedError  # TODO when writing your own plugin remove this line and modify the one below
        if self.is_master:
            self.controller = ThermocoupleController()  #instantiate you driver with whatever arguments are needed
            initialized = self.controller._try_connect_port(self.settings.child('com_port').value())
        else:
            self.controller = controller
            initialized = True

        thermo_couple_channels = self.make_thermocouple_channels()
        # print(thermo_couple_channels)
        # TODO for your custom plugin (optional) initialize viewers panel with the future type of data
        
        self.active_channels = self.get_active_channels()
        dte = self._build_dte(
            data=[np.array([0.0]) for _ in self.active_channels],
            active_channels = self.active_channels
        )
        self.dte_signal_temp.emit(dte)
             
        info = "Whatever info you want to log"
        return info, initialized
    
    def make_thermocouple_channels(self):
        thermo_couple_channels = []
        for index, tc_config in enumerate(self.controller.tc_configs):
            param = Parameter(title =f'Channel {index}', name=f'channel_{index}', value=True, type='bool', children=[
                {'title': 'Min', 'name':  f'tc{index}_min', 'type': 'float', 'value':tc_config.t_min, 'suffix':'°C'},
                {'title': 'Max', 'name':  f'tc{index}_max', 'type': 'float', 'value':tc_config.t_max, 'suffix':'°C'},
                {'title': 'Offset', 'name':  f'tc{index}_offset', 'type': 'float', 'value':tc_config.t_offset, 'suffix':'°C'},
            ])
            thermo_couple_channels.append(param)
        self.settings.child('channels').addChildren(thermo_couple_channels)
        return thermo_couple_channels

    def close(self):
        """Terminate the communication protocol"""
        ## TODO for your custom plugin
        self.controller.close()


    def _build_dte(self, data: list, active_channels: list) -> DataToExport:
        """Assemble a DataToExport from a list of scalar arrays and active channel dicts.

        Parameters
        ----------
        data: list of np.ndarray
            One 1-element array per active channel, in the same order.
        active_channels: list
            The channel list returned by get_active_channels().
        """
        return DataToExport(
            name='Themocouple',
            data=[DataFromPlugins(
                name='Channels',
                data=data,
                dim='Data0D',
                labels=active_channels,
            )]
        )
    
    def data_to_channel_dict(self, data: ThermocoupleData) -> dict:
        """Convert a ThermocoupleData object to a dict with channel names as keys"""
        return {
            f'channel_{i}': data.t_tc[i] for i in range(self.controller.nb_tc) 
        }
    def grab_data(self, Naverage=1, **kwargs):
        """Start a grab from the detector

        Parameters
        ----------
        Naverage: int
            Number of hardware averaging (if hardware averaging is possible, self.hardware_averaging should be set to
            True in class preamble and you should code this implementation)
        kwargs: dict
            others optionals arguments
        """
        ## TODO for your custom plugin: you should choose EITHER the synchrone or the asynchrone version following
        active_channels = self.get_active_channels()
        data_channels = []

        data = self.controller.read_data()        
        if data:        
            data_dict = self.data_to_channel_dict(data)
            for ch in self.active_channels:
                data_channels.append(np.array([data_dict[ch]]))
            self.dte_signal.emit(self._build_dte(data=data_channels, active_channels=self.active_channels))

    def callback(self):
        """optional asynchrone method called when the detector has finished its acquisition of data"""
        data_tot = self.controller.your_method_to_get_data_from_buffer()
        self.dte_signal.emit(DataToExport(name='myplugin',
                                          data=[DataFromPlugins(name='Mock1', data=data_tot,
                                                                dim='Data0D', labels=['dat0', 'data1'])]))

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        self.controller.stop() 
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))
        ##############################
        return ''


if __name__ == '__main__':
    main(__file__)
