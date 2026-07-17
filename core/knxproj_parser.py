import json
import traceback
from xknxproject import XKNXProj

class ETSParser:
    def __init__(self):
        pass

    def parse_project(self, file_path, password=None):
        try:
            # Step 1: Parse the KNX project file
            proj = XKNXProj(file_path, password=password)
            project_data = proj.parse()
            
            # Extract basic group address metadata (GA -> DPT map)
            ga_dpt_map = {}
            if "group_addresses" in project_data:
                # Based on xknxproject spec, group_addresses is a list of dictionaries or object containing address and dpt
                # We normalize it into a fast lookup map: { "1/1/1": "1.001", ... }
                # Handle varying structures just in case
                ga_list = project_data.get("group_addresses", [])
                
                # Check if group_addresses is structured hierarchically (main -> middle -> sub) or flattened
                if isinstance(ga_list, list):
                    for ga_item in ga_list:
                        # Extract string GA
                        ga_address = ga_item.get("address", "")
                        dpt = ga_item.get("dpt", None)
                        if ga_address and dpt:
                            ga_dpt_map[ga_address] = str(dpt)
                elif isinstance(ga_list, dict):
                    # Sometimes grouped by main/middle
                    def extract_flattened_gas(data_node):
                        if isinstance(data_node, dict):
                            addr = data_node.get("address")
                            dpt = data_node.get("dpt")
                            if addr and dpt:
                                ga_dpt_map[addr] = str(dpt)
                            for val in data_node.values():
                                extract_flattened_gas(val)
                        elif isinstance(data_node, list):
                            for item in data_node:
                                extract_flattened_gas(item)
                    extract_flattened_gas(ga_list)
                    
            devices_result = []

            # Step 2: Traverse Topology to find Physical Devices
            topology = project_data.get("topology", {})
            areas = topology.get("areas", [])
            for area in areas:
                lines = area.get("lines", [])
                for line in lines:
                    devices = line.get("devices", [])
                    for device in devices:
                        # Extract basic info
                        phys_address = device.get("address", "")
                        name = device.get("name", "Unknown Device")
                        manufacturer = device.get("manufacturer_name", "")
                        
                        device_id = f"knx_{phys_address.replace('.', '_')}"
                        
                        # Step 3: Extract communication objects and associated GAs
                        com_objects = device.get("com_objects", [])
                        
                        # We will gather all GAs associated with this device to determine its profile and config
                        device_gas = []
                        for com in com_objects:
                            gas = com.get("group_addresses", [])
                            # Handle both list of strings or list of objects
                            for ga in gas:
                                if isinstance(ga, str):
                                    device_gas.append(ga)
                                elif isinstance(ga, dict) and "address" in ga:
                                    device_gas.append(ga["address"])
                        
                        # Deduplicate GAs
                        device_gas = list(set(device_gas))
                        
                        if not device_gas:
                            continue # Skip devices with no group addresses assigned
                            
                        # Step 4: Map to our standardized DB Schema
                        # We use simple heuristics to map basic GA to legacy fields (onoff_ga, status_ga) 
                        # and package EVERYTHING else into knx_config_payload with its DPT
                        
                        knx_config_payload = {}
                        onoff_ga = ""
                        status_ga = ""
                        brightness_ga = ""
                        brightness_status_ga = ""
                        
                        # Simple Inference Engine for DPT Mapping
                        for ga in device_gas:
                            dpt = ga_dpt_map.get(ga, "")
                            
                            # Build the dynamic payload
                            payload_key = f"ga_{ga.replace('/', '_')}"
                            knx_config_payload[payload_key] = {
                                "ga": ga,
                                "dpt": dpt
                            }
                            
                            # Heuristic mapping for Legacy compatibility
                            if dpt.startswith("1."):
                                if "status" in name.lower() or "state" in name.lower() or not onoff_ga:
                                    if not onoff_ga:
                                        onoff_ga = ga
                                    else:
                                        status_ga = ga
                            elif dpt.startswith("5."):
                                if not brightness_ga:
                                    brightness_ga = ga
                                else:
                                    brightness_status_ga = ga
                                    
                        # Determine rough device type based on DPTs present
                        dev_type = "light"
                        dpt_list = [v["dpt"] for v in knx_config_payload.values()]
                        if any(d.startswith("9.") or d.startswith("20.") for d in dpt_list):
                            dev_type = "hvac"
                        elif any(d.startswith("1.008") for d in dpt_list):
                            dev_type = "blind"
                        elif any(d.startswith("232.") for d in dpt_list):
                            dev_type = "rgbw"
                        elif brightness_ga:
                            dev_type = "dimmer"

                        devices_result.append({
                            "device_id": device_id,
                            "name": f"{name} ({phys_address})",
                            "type": dev_type,
                            "onoff_ga": onoff_ga,
                            "status_ga": status_ga,
                            "brightness_ga": brightness_ga,
                            "brightness_status_ga": brightness_status_ga,
                            "knx_config_payload": json.dumps({
                                "manufacturer": manufacturer,
                                "physical_address": phys_address,
                                "profile": dev_type,
                                "config": knx_config_payload
                            })
                        })
            
            return {
                "status": "success",
                "total_devices": len(devices_result),
                "devices": devices_result
            }
            
        except Exception as e:
            error_msg = str(e)
            if "BadZipFile" in str(type(e)):
                error_msg = "Invalid ETS project file format (Not a ZIP file)."
            elif "password" in str(e).lower() or "decrypt" in str(e).lower():
                error_msg = "Failed to decrypt ETS project. Incorrect password."
            return {
                "status": "error",
                "message": f"ETS Parse Error: {error_msg}",
                "trace": traceback.format_exc()
            }
