"""
Arduino Thermocouple Communication Protocol
Implements PC-side communication for thermocouple data acquisition
"""

import serial
import serial.tools.list_ports
import time
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ThermocoupleConfig:
    """Configuration for a single thermocouple"""
    t_min: float
    t_max: float
    t_offset: float = 0.0


@dataclass
class ThermocoupleData:
    """Data from a single thermocouple reading"""
    time: int  # ms since PC_Start
    acq_time: int  # actual acquisition time (ms)
    cycle_time: int  # actual refresh time (ms)
    t_tc: List[Optional[float]]  # thermocouple temperatures (°C)
    v_tc: List[Optional[float]]  # thermocouple voltages (mV)
    v_total: List[Optional[float]]  # total voltages (mV)
    t_cj: List[float]  # cold junction temperatures (°C)
    v_cj: List[float]  # cold junction voltages (mV)


class ThermocoupleController:
    """Controller for Arduino thermocouple communication"""
    
    BAUD_RATE = 9600
    DEFAULT_REFRESH_TIME = 1000  # ms
    
    def __init__(self):
        self.port_com: Optional[serial.Serial] = None
        self.nb_tc: int = 0
        self.tc_configs: List[ThermocoupleConfig] = []
        self.time_start: float = 0
        
    def init(self, port_name: Optional[str] = None) -> bool:
        """
        Initialize connection to Arduino
        
        Args:
            port_name: Specific COM port to connect to (e.g., 'COM3', '/dev/ttyUSB0')
                      If None, will scan all available ports
        
        Returns:
            True if successful, False otherwise
        """
        # If specific port is provided, try only that port
        if port_name:
            return self._try_connect_port(port_name)
        
        # Otherwise, scan all available COM ports
        available_ports = serial.tools.list_ports.comports()
        
        for port in available_ports:
            if self._try_connect_port(port.device):
                return True
        
        print("ERROR: Arduino not found")
        return False
    
    def _try_connect_port(self, port_device: str) -> bool:
        """
        Try to connect to a specific port
        
        Args:
            port_device: Port device name (e.g., 'COM3', '/dev/ttyUSB0')
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Try to connect to the port
            ser = serial.Serial(port_device, self.BAUD_RATE, timeout=2)
            # time.sleep(2)  # Wait for Arduino to reset
            
            # Send PC_Init command
            ser.write(b"PC_Init\n")
            # time.sleep(0.5)
            
            # Read response
            if ser.in_waiting > 0:
                response = ser.readline().decode('utf-8').strip()
                
                # Check if response starts with "Thermocouple_"
                if response.startswith("Thermocouple_"):
                    self.port_com = ser
                    self._extract_init_data(response)
                    print(f"Connected to Arduino on {port_device}")
                    print(f"Number of thermocouples: {self.nb_tc}")
                    return True
            
            # Close if not the right device
            ser.close()
            
        except (serial.SerialException, Exception) as e:
            print(f"Error checking port {port_device}: {e}")
        
        return False
    
    def _extract_init_data(self, response: str):
        """Extract initialization data from PC_Init response"""
        # Format: "Thermocouple_nb_tc;tc1_t_min,tc1_t_max,tc1_t_offset;tc2_t_min,..."
        parts = response.split(';')
        
        # Extract number of thermocouples
        self.nb_tc = int(parts[0].split('_')[1])
        
        # Extract configuration for each thermocouple
        self.tc_configs = []
        for i in range(1, len(parts)):
            values = parts[i].split(',')
            if len(values) >= 2:
                t_min = float(values[0])
                t_max = float(values[1])
                t_offset = float(values[2]) if len(values) > 2 else 0.0
                self.tc_configs.append(ThermocoupleConfig(t_min, t_max, t_offset))
    
    def stop(self):
        """Stop data acquisition"""
        if self.port_com and self.port_com.is_open:
            self.port_com.write(b"PC_Stop\n")
            self.is_measuring = False
            print("Acquisition stopped")

    def make_command(self, refresh_time: Optional[int] = None,offsets: Optional[List[float]] = None) -> str:
        """Build command

        Args:
            refresh_time: Refresh time in ms (default: 1000)
            offsets: List of offset values for each thermocouple (°C)

        Returns:
            command: command to send to Arduino
        """
        # Build command
        command = "PC_Start"

        if refresh_time is not None or offsets is not None:
            if refresh_time is None:
                refresh_time = self.DEFAULT_REFRESH_TIME
            command += f";{refresh_time}"

            if offsets is not None:
                offsets_str = ','.join(str(offset) for offset in offsets)
                command += f";{offsets_str}"        
        return command
    
    def start(self, refresh_time: Optional[int] = None, 
              offsets: Optional[List[float]] = None) -> bool:
        """
        Start data acquisition
        
        Args:
            refresh_time: Refresh time in ms (default: 1000)
            offsets: List of offset values for each thermocouple (°C)
        
        Returns:
            True if started successfully
        """
        if not self.port_com or not self.port_com.is_open:
            print("ERROR: Not connected to Arduino")
            return False
        
        command = self.make_command(refresh_time, offsets)
        # Send command
        self.port_com.write(f"{command}\n".encode('utf-8'))
        self.time_start = time.time()
        self.is_measuring = True
        print(f"Acquisition started: {command}")
        return True
    
    def read_data(self) -> Optional[ThermocoupleData]:
        """
        Read one data packet from Arduino
        
        Returns:
            ThermocoupleData object or None if no data available
        """
        if not self.port_com or not self.port_com.is_open:
            return None
        
        if self.port_com.in_waiting > 0:
            response = self.port_com.readline().decode('utf-8').strip()
            return self._extract_data(response)
        
        return None
    
    def _extract_data(self, response: str) -> Optional[ThermocoupleData]:
        """Extract data from response string"""
        # Format: "time,acq_time,cycle_time;tc1_t_tc,tc2_t_tc,...;tc1_v_tc,...;tc1_v_total,...;tc1_t_cj,...;tc1_v_cj,..."
        
        if not response or response == "PC_Stop":
            return None
        
        try:
            parts = response.split(';')
            if len(parts) < 6:
                return None
            
            # Parse timing data
            timing = parts[0].split(',')
            time_ms = int(timing[0])
            acq_time = int(timing[1])
            cycle_time = int(timing[2])
            
            # Parse thermocouple data
            t_tc = self._parse_float_list(parts[1])
            v_tc = self._parse_float_list(parts[2])
            v_total = self._parse_float_list(parts[3])
            t_cj = self._parse_float_list(parts[4])
            v_cj = self._parse_float_list(parts[5])
            
            return ThermocoupleData(
                time=time_ms,
                acq_time=acq_time,
                cycle_time=cycle_time,
                t_tc=t_tc,
                v_tc=v_tc,
                v_total=v_total,
                t_cj=t_cj,
                v_cj=v_cj
            )
        except Exception as e:
            print(f"Error parsing data: {e}")
            return None
    
    def _parse_float_list(self, data_str: str) -> List[Optional[float]]:
        """Parse comma-separated float values, handling 'null' values"""
        values = []
        for value in data_str.split(','):
            value = value.strip()
            if value.lower() == 'null':
                values.append(None)
            else:
                try:
                    values.append(float(value))
                except ValueError:
                    values.append(None)
        return values
    
    def close(self):
        """Close serial connection"""
        if self.port_com and self.port_com.is_open:
            self.stop()
            self.port_com.close()
            print("Connection closed")


# Example usage
if __name__ == "__main__":
    # Initialize controller
    controller = ThermocoupleController()
    
    # Method 1: Auto-detect Arduino on any COM port
    if controller.init():
        pass
    
    # Method 2: Connect to specific COM port (faster if you know the port)
    # if controller.init(port_name='COM3'):  # Windows
    # if controller.init(port_name='/dev/ttyUSB0'):  # Linux
    # if controller.init(port_name='/dev/cu.usbserial-0001'):  # macOS
    
    if controller.port_com:
        # Display configuration
        print("\nThermocouple Configuration:")
        for i, config in enumerate(controller.tc_configs):
            print(f"TC{i+1}: min={config.t_min}°C, max={config.t_max}°C, offset={config.t_offset}°C")
        
        # Start acquisition
        # Example 1: Default settings
        # controller.start()
        
        # Example 2: Custom refresh time (500ms)
        # controller.start(refresh_time=500)
        
        # Example 3: Custom offsets
        # controller.start(offsets=[0.0, 20.0, 0.0, 0.0])
        
        # Example 4: Custom refresh time and offsets
        controller.start(refresh_time=500, offsets=[4.0, 4.0, 4.0, 4.0])
        
        try:
            # Read data for 10 seconds
            start_time = time.time()
            while time.time() - start_time < 10:
                data = controller.read_data()
                if data:
                    print(f"\nTime: {data.time}ms")
                    print(f"Acquisition time: {data.acq_time}ms, Cycle time: {data.cycle_time}ms")
                    for i in range(controller.nb_tc):
                        if i < len(data.t_tc):
                            temp = data.t_tc[i]
                            temp_str = f"{temp:.1f}°C" if temp is not None else "null"
                            print(f"TC{i+1}: {temp_str}")
                
                time.sleep(0.1)  # Small delay to avoid busy waiting
        
        except KeyboardInterrupt:
            print("\nStopped by user")
        
        finally:
            # Stop and close
            controller.close()
    else:
        print("Failed to initialize connection")