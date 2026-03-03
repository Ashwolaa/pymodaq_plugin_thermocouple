from pathlib import Path
from .utils import Config
from pymodaq_utils.utils import get_version, PackageNotFoundError
from pymodaq_utils.logger import set_logger, get_module_name

config = Config()
try:
    __version__ = get_version(__package__)
except PackageNotFoundError:
    __version__ = '0.0.0dev'


from serial.tools.list_ports import comports
COM_ports = [comport.name for comport in comports()]
ind = COM_ports.index('COM7')  # Ensure COM5 is in the list of available ports
COM_ports.insert(0, COM_ports.pop(ind))  # Move COM7 to the front of the list
config["com_ports"] = COM_ports

config.save()