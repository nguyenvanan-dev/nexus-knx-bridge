import { Lightbulb, Thermometer, Blinds, Wind } from 'lucide-react';

export const mockDevices = [
  {
    id: "device-1",
    name: "Living Room Main Light",
    type: "light",
    icon: Lightbulb,
    isOn: true,
    value: "75%",
    capabilities: ["on_off", "brightness"]
  },
  {
    id: "device-2",
    name: "AC Living Room",
    type: "ac",
    icon: Thermometer,
    isOn: true,
    value: "24°C",
    capabilities: ["on_off", "temperature", "mode"]
  },
  {
    id: "device-3",
    name: "Balcony Curtains",
    type: "curtain",
    icon: Blinds,
    isOn: false,
    value: "Closed",
    capabilities: ["open_close", "position"]
  },
  {
    id: "device-4",
    name: "Air Purifier",
    type: "appliance",
    icon: Wind,
    isOn: false,
    value: "Off",
    capabilities: ["on_off", "fan_speed"]
  }
];
