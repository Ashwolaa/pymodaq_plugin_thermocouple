import numpy as np

from pymodaq_utils.utils import ThreadCommand
from pymodaq_data.data import DataToExport
from pymodaq_gui.parameter import Parameter

from pymodaq.control_modules.viewer_utility_classes import DAQ_Viewer_base, comon_parameters, main
from pymodaq.utils.data import DataFromPlugins
from pymodaq_plugins_lakeshore.utils import Config
config = Config()

from pymodaq_plugins_thermocouple.hardware.thermocouple import ThermocoupleController

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
        {'title': 'COM', 'name':  'com_port', 'type': 'list', 'limits': config['com_ports'], 'value':config['com_ports'][0]},
        {'title': 'Refresh time', 'name':  'refresh_time', 'type': 'int', 'value':1000,'suffix':'ms'},
        {'title': 'Thermocouples', 'name':  'thermocouple', 'type': 'group', 'children':[]},
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
        

#        elif ...
    def get_active_input_channels(self):
        """Return the list of input channels whose checkbox is enabled."""
        return [ch for ch in self.input_channels
                if self.settings.child('thermocouple').child(ch).value()]
    
    def build_settings(self):
        """Build the settings tree"""
        refresh_time = self.settings.child('refresh_time').value()
        offsets = [self.settings.child(f'tc{i}_offset').value() for i in range(self.controller.nb_tc)]
        return refresh_time, offsets
    
    def apply_settings(self, refresh_time, offsets):
        """Apply the settings"""
        if self.controller.is_measuring:
            self.controller.stop()
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
            self.controller._try_connect_port(self.settings.child('com_port').value())
            self.controller.init(port_name=self.settings.child('com_port').value()) # call eventual methods
            initialized = True
        else:
            self.controller = controller
            initialized = True

        self.make_thermocouple_channels()
        # TODO for your custom plugin (optional) initialize viewers panel with the future type of data
        self.dte_signal_temp.emit(DataToExport(name='myplugin',
                                               data=[DataFromPlugins(name='Mock1',
                                                                    data=[np.array([0]), np.array([0])],
                                                                    dim='Data0D',
                                                                    labels=['Mock1', 'label2'])]))

        info = "Whatever info you want to log"
        return info, initialized
    def make_thermocouple_channels(self):
        thermo_couple_channels = []
        for index, tc_config in enumerate(self.controller.tc_configs):
            param = Parameter(name=f'tc{index}', value=True, type='bool', children=[
                {'title': 'Min', 'name':  f'tc{index}_min', 'type': 'float', 'value':tc_config.t_min, 'suffix':'°C'},
                {'title': 'Max', 'name':  f'tc{index}_max', 'type': 'float', 'value':tc_config.t_max, 'suffix':'°C'},
                {'title': 'Offset', 'name':  f'tc{index}_offset', 'type': 'float', 'value':tc_config.t_offset, 'suffix':'°C'},
            ])
            thermo_couple_channels.append(param)
        self.settings.child('thermocouple').addChildren(thermo_couple_channels)
        

    def close(self):
        """Terminate the communication protocol"""
        ## TODO for your custom plugin
        self.controller.close()


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

        # synchrone version (blocking function)
        if not self.controller.is_measuring:
            self.controller.start()


        data = self.controller.read_data()

        raise NotImplementedError  # when writing your own plugin remove this line
        data_tot = self.controller.your_method_to_start_a_grab_snap()
        self.dte_signal.emit(DataToExport(name='myplugin',
                                          data=[DataFromPlugins(name='Mock1', data=data_tot,
                                                                dim='Data0D', labels=['dat0', 'data1'])]))
        #########################################################

        # asynchrone version (non-blocking function with callback)
        raise NotImplementedError  # when writing your own plugin remove this line
        self.controller.your_method_to_start_a_grab_snap(self.callback)  # when writing your own plugin replace this line
        #########################################################


    def callback(self):
        """optional asynchrone method called when the detector has finished its acquisition of data"""
        data_tot = self.controller.your_method_to_get_data_from_buffer()
        self.dte_signal.emit(DataToExport(name='myplugin',
                                          data=[DataFromPlugins(name='Mock1', data=data_tot,
                                                                dim='Data0D', labels=['dat0', 'data1'])]))

    def stop(self):
        """Stop the current grab hardware wise if necessary"""
        self.controller.stop() 
        self.is_started = False
        self.emit_status(ThreadCommand('Update_Status', ['Some info you want to log']))
        ##############################
        return ''


if __name__ == '__main__':
    main(__file__)
