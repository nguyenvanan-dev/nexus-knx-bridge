import json
import traceback
import re
from datetime import datetime
from pathlib import Path
from core.proposal_schema import make_proposal_base

try:
    from xknxproject import XKNXProj
    has_xknx = True
except ImportError:
    has_xknx = False


class ETSParser:
    def __init__(self):
        pass

    def normalize_ga(self, ga):
        if not ga:
            return ""
        ga = str(ga).strip()
        parts = ga.split("/")
        if len(parts) == 3:
            try:
                return f"{int(parts[0])}/{int(parts[1])}/{int(parts[2])}"
            except ValueError:
                pass
        return ga

    def normalize_dpt(self, dpt):
        if not dpt:
            return ""
        dpt = str(dpt).strip()
        m = re.search(r"(\d+)[-.](\d+)", dpt)
        if m:
            return f"{m.group(1)}.{m.group(2).zfill(3)}"
        m2 = re.match(r"^(\d+)$", dpt)
        if m2:
            return f"{m2.group(1)}.001"
        return dpt

    def infer_room_from_name_path(self, name, path=""):
        combined = f"{name} {path}".lower()
        rooms = {
            "living_room": ["living", "khách", "pkhách", "salon", "lounge", "family room"],
            "bedroom": ["bedroom", "ngủ", "pngủ", "bed", "master", "kid"],
            "kitchen": ["kitchen", "bếp", "pbếp", "cook", "dining", "ăn", "păn"],
            "bathroom": ["bathroom", "tắm", "ptắm", "wc", "toilet", "restroom", "powder"],
            "corridor": ["corridor", "hall", "lobby", "hành lang", "hlang", "stairs", "cầu thang"],
            "balcony": ["balcony", "ban công", "logia", "terrace", "hiên"],
            "garden": ["garden", "sân", "yard", "ngoài", "outdoor", "garage", "kho"],
        }
        for room_key, keywords in rooms.items():
            if any(k in combined for k in keywords):
                return room_key.replace("_", " ").title()
        return "Common"

    def infer_device_type(self, dpts, name=""):
        dpts = [self.normalize_dpt(d) for d in dpts if d]
        name_lower = name.lower()

        if any(d.startswith("232.") for d in dpts) or any(k in name_lower for k in ["rgb", "rgbw", "color light", "màu"]):
            return "rgbw"

        if any(d.startswith("7.600") for d in dpts) or any(k in name_lower for k in ["color temp", "color_temp", "tunable", "kelvin", "nhiệt độ màu"]):
            return "color_light"

        if any(k in name_lower for k in ["sensor", "cảm biến", "motion", "presence", "lux", "temp sensor", "nhiệt độ"]):
            return "sensor"

        if any(d.startswith("9.") or d.startswith("20.") for d in dpts) or \
           any(k in name_lower for k in ["hvac", "thermostat", "điều hòa", "aircon"]) or \
           re.search(r"\b(ac|fcu|fan)\b", name_lower):
            return "hvac"

        if any(d.startswith("1.008") for d in dpts) or any(k in name_lower for k in ["blind", "shutter", "curtain", "rèm", "mành"]):
            if any(d.startswith("5.") for d in dpts) or "position" in name_lower:
                return "blind"
            return "curtain"

        if any(d.startswith("5.") for d in dpts) or any(k in name_lower for k in ["dimmer", "dimming", "tăng giảm"]):
            return "dimmer"

        if any(k in name_lower for k in ["switch", "button", "nút nhấn", "keypad"]):
            return "switch"

        if any(d.startswith("1.") for d in dpts) or any(k in name_lower for k in ["light", "lamp", "đèn"]):
            return "light"

        return "unknown"

    def build_capabilities(self, dev_type, gas):
        caps = {}

        def find_ga(dpt_prefix=None, name_kw=None, exclude_kw=None):
            for address in sorted(gas.keys()):
                info = gas[address]
                dpt = info.get("dpt", "")
                name = info.get("name", "").lower()
                obj_name = info.get("object_name", "").lower()
                if exclude_kw:
                    if any(k in name for k in exclude_kw) or any(k in obj_name for k in exclude_kw):
                        continue
                if dpt_prefix and dpt.startswith(dpt_prefix):
                    return address
                if name_kw:
                    if any(k in name for k in name_kw) or any(k in obj_name for k in name_kw):
                        return address
            return None

        if dev_type in ["light", "switch"]:
            onoff = find_ga(dpt_prefix="1.", exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="1.") or (list(gas.keys())[0] if gas else "")
            status = find_ga(name_kw=["status", "state", "feedback", "phản hồi"]) or onoff
            caps["onoff"] = {"write_ga": onoff, "status_ga": status, "dpt": "1.001"}

        elif dev_type == "dimmer":
            onoff = find_ga(dpt_prefix="1.", exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="1.") or (list(gas.keys())[0] if gas else "")
            status = find_ga(name_kw=["status", "state", "feedback", "phản hồi"]) or onoff
            caps["onoff"] = {"write_ga": onoff, "status_ga": status, "dpt": "1.001"}

            brightness = find_ga(dpt_prefix="5.", exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="5.")
            bright_status = find_ga(name_kw=["bright status", "bright feedback", "phần trăm phản hồi", "brightness status"]) or brightness
            if brightness:
                caps["brightness"] = {"write_ga": brightness, "status_ga": bright_status, "dpt": "5.001"}

        elif dev_type == "color_light":
            onoff = find_ga(dpt_prefix="1.", exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="1.") or (list(gas.keys())[0] if gas else "")
            status = find_ga(name_kw=["status", "state", "feedback", "phản hồi"]) or onoff
            caps["onoff"] = {"write_ga": onoff, "status_ga": status, "dpt": "1.001"}

            brightness = find_ga(dpt_prefix="5.", exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="5.")
            bright_status = find_ga(name_kw=["bright status", "brightness status"]) or brightness
            if brightness:
                caps["brightness"] = {"write_ga": brightness, "status_ga": bright_status, "dpt": "5.001"}

            color_temp = find_ga(dpt_prefix="7.600", exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="7.", exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="7.600") or find_ga(dpt_prefix="7.")
            ct_status = find_ga(name_kw=["color temp status", "color temperature status", "kelvin status"]) or color_temp
            if color_temp:
                caps["color_temperature"] = {
                    "write_ga": color_temp,
                    "status_ga": ct_status,
                    "dpt": "7.600",
                    "min": 2000,
                    "max": 6500
                }

        elif dev_type == "rgbw":
            onoff = find_ga(dpt_prefix="1.", exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="1.") or (list(gas.keys())[0] if gas else "")
            status = find_ga(name_kw=["status", "state", "feedback"]) or onoff
            caps["onoff"] = {"write_ga": onoff, "status_ga": status, "dpt": "1.001"}

            rgb = find_ga(dpt_prefix="232.", exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="232.")
            rgb_status = find_ga(name_kw=["rgb status", "color status", "màu status"]) or rgb
            if rgb:
                caps["rgb"] = {"write_ga": rgb, "status_ga": rgb_status, "dpt": "232.600"}

        elif dev_type in ["curtain", "blind"]:
            updown = find_ga(dpt_prefix="1.008", exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="1.", exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="1.008") or find_ga(dpt_prefix="1.") or (list(gas.keys())[0] if gas else "")
            stop = find_ga(dpt_prefix="1.017") or find_ga(name_kw=["stop", "dừng", "step"]) or updown
            caps["curtain"] = {"write_ga": updown, "stop_ga": stop, "dpt": "1.008"}

            position = find_ga(dpt_prefix="5.", exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="5.")
            pos_status = find_ga(name_kw=["position status", "pos status", "phần trăm phản hồi"]) or position
            if position:
                caps["position"] = {"write_ga": position, "status_ga": pos_status, "dpt": "5.001"}

        elif dev_type == "hvac":
            temp_status = find_ga(dpt_prefix="9.001") or find_ga(dpt_prefix="9.")
            if temp_status:
                caps["temperature"] = {"status_ga": temp_status, "dpt": "9.001"}

            setpoint = find_ga(name_kw=["setpoint", "đặt", "target"], exclude_kw=["status", "state", "feedback", "phản hồi"]) or find_ga(dpt_prefix="9.001") or find_ga(dpt_prefix="9.")
            setpoint_status = find_ga(name_kw=["setpoint status", "setpoint feedback"]) or setpoint
            if setpoint:
                caps["thermostat"] = {"write_ga": setpoint, "status_ga": setpoint_status, "dpt": "9.001"}

            mode = find_ga(dpt_prefix="20.102") or find_ga(dpt_prefix="20.")
            mode_status = find_ga(name_kw=["mode status", "chế độ status"]) or mode
            if mode:
                caps["mode"] = {"write_ga": mode, "status_ga": mode_status, "dpt": "20.102"}

        elif dev_type == "sensor":
            val_ga = find_ga(dpt_prefix="9.") or find_ga(dpt_prefix="14.") or find_ga(dpt_prefix="13.") or (list(gas.keys())[0] if gas else "")
            dpt = gas.get(val_ga, {}).get("dpt", "9.001") if val_ga else "9.001"
            caps["sensor"] = {"status_ga": val_ga, "dpt": dpt}

        return caps

    def build_legacy_fields(self, caps):
        legacy = {
            "onoff_ga": "",
            "status_ga": "",
            "brightness_ga": "",
            "brightness_status_ga": "",
            "color_ga": "",
            "color_status_ga": ""
        }
        if "onoff" in caps:
            legacy["onoff_ga"] = caps["onoff"].get("write_ga", "")
            legacy["status_ga"] = caps["onoff"].get("status_ga", "")
        if "brightness" in caps:
            legacy["brightness_ga"] = caps["brightness"].get("write_ga", "")
            legacy["brightness_status_ga"] = caps["brightness"].get("status_ga", "")
        if "rgb" in caps:
            legacy["color_ga"] = caps["rgb"].get("write_ga", "")
            legacy["color_status_ga"] = caps["rgb"].get("status_ga", "")
        elif "color_temperature" in caps:
            legacy["color_ga"] = caps["color_temperature"].get("write_ga", "")
            legacy["color_status_ga"] = caps["color_temperature"].get("status_ga", "")
        return legacy

    def parse_project(self, file_path, password=None):
        if not has_xknx:
            return {
                "status": "error",
                "message": "ETS Parse Error: xknxproject dependency is not installed."
            }

        try:
            proj = XKNXProj(file_path, password=password)
            project_data = proj.parse()

            ga_map = {}
            ga_list = project_data.get("group_addresses", {})

            if isinstance(ga_list, dict):
                for addr, ga_item in ga_list.items():
                    dpt_info = ga_item.get("dpt", {})
                    dpt_str = ""
                    if isinstance(dpt_info, dict):
                        main = dpt_info.get("main")
                        sub = dpt_info.get("sub")
                        if main is not None and sub is not None:
                            dpt_str = f"{main}.{str(sub).zfill(3)}"
                    else:
                        dpt_str = self.normalize_dpt(dpt_info)

                    ga_map[self.normalize_ga(addr)] = {
                        "dpt": dpt_str,
                        "name": ga_item.get("name", "")
                    }
            elif isinstance(ga_list, list):
                for ga_item in ga_list:
                    addr = ga_item.get("address", "")
                    dpt = ga_item.get("dpt", None)
                    name = ga_item.get("name", "")
                    if addr:
                        ga_map[self.normalize_ga(addr)] = {
                            "dpt": self.normalize_dpt(dpt),
                            "name": name
                        }

            devices_map = {}
            raw_devices = project_data.get("devices", {})
            if isinstance(raw_devices, dict):
                for addr, dev_dict in raw_devices.items():
                    if isinstance(dev_dict, dict):
                        devices_map[str(addr)] = dev_dict

            device_to_topology_path = {}
            topology = project_data.get("topology", {})

            if isinstance(topology, dict) and "areas" in topology and isinstance(topology["areas"], list):
                for area in topology["areas"]:
                    area_name = area.get("name") or "Area"
                    lines = area.get("lines", [])
                    for line in lines:
                        line_name = line.get("name") or "Line"
                        devices_list = line.get("devices", [])
                        for dev in devices_list:
                            if isinstance(dev, dict):
                                addr = dev.get("address") or dev.get("individual_address")
                                if addr:
                                    addr = str(addr)
                                    device_to_topology_path[addr] = (area_name, line_name)
                                    if addr not in devices_map:
                                        devices_map[addr] = dev
                            else:
                                addr = str(dev)
                                device_to_topology_path[addr] = (area_name, line_name)

            elif isinstance(topology, dict):
                for area_id, area_dict in topology.items():
                    if isinstance(area_dict, dict):
                        area_name = area_dict.get("name") or f"Area {area_id}"
                        lines = area_dict.get("lines", {})
                        if isinstance(lines, dict):
                            for line_id, line_dict in lines.items():
                                line_name = line_dict.get("name") or f"Line {line_id}"
                                devices_list = line_dict.get("devices", [])
                                for dev in devices_list:
                                    if isinstance(dev, dict):
                                        addr = dev.get("address") or dev.get("individual_address")
                                        if addr:
                                            addr = str(addr)
                                            device_to_topology_path[addr] = (area_name, line_name)
                                            if addr not in devices_map:
                                                devices_map[addr] = dev
                                    else:
                                        addr = str(dev)
                                        device_to_topology_path[addr] = (area_name, line_name)
                        elif isinstance(lines, list):
                            for line in lines:
                                line_name = line.get("name", "")
                                devices_list = line.get("devices", [])
                                for dev in devices_list:
                                    if isinstance(dev, dict):
                                        addr = dev.get("address") or dev.get("individual_address")
                                        if addr:
                                            addr = str(addr)
                                            device_to_topology_path[addr] = (area_name, line_name)
                                            if addr not in devices_map:
                                                devices_map[addr] = dev
                                    else:
                                        addr = str(dev)
                                        device_to_topology_path[addr] = (area_name, line_name)

            proposed_devices = []
            unmapped_ga_set = set(ga_map.keys())

            com_objs = project_data.get("communication_objects", {})

            for phys_address, device in devices_map.items():
                dev_name = device.get("name", "Unknown Device")
                manufacturer = device.get("manufacturer_name", "")
                product = device.get("hardware_name", "")

                area_name, line_name = device_to_topology_path.get(phys_address, ("Common", "Common"))

                channels = device.get("channels", {})
                if not channels and "com_objects" in device:
                    channels = {
                        "MAIN": {
                            "name": "Main Channel",
                            "com_objects": device.get("com_objects", [])
                        }
                    }
                elif not channels and device.get("communication_object_ids"):
                    channels = {
                        "MAIN": {
                            "name": "Main Channel",
                            "communication_object_ids": device.get("communication_object_ids", [])
                        }
                    }

                for chan_id, chan_dict in channels.items():
                    chan_name = chan_dict.get("name") or chan_id
                    com_obj_ids = chan_dict.get("communication_object_ids", [])
                    inline_com_objects = chan_dict.get("com_objects", [])

                    device_gas = {}
                    all_dpts = []
                    objects_list = []

                    for oid in com_obj_ids:
                        obj = com_objs.get(oid)
                        if obj:
                            com_name = obj.get("name") or obj.get("function_text") or "Object"
                            gas = obj.get("group_address_links", [])
                            objects_list.append({
                                "name": com_name,
                                "gas": gas
                            })
                            for ga in gas:
                                norm = self.normalize_ga(ga)
                                info = dict(ga_map.get(norm, {"dpt": "", "name": ""}))
                                if com_name:
                                    info["object_name"] = com_name
                                    if not info.get("name"):
                                        info["name"] = com_name
                                    else:
                                        info["name"] = f"{info['name']} {com_name}"
                                device_gas[norm] = info
                                if info["dpt"]:
                                    all_dpts.append(info["dpt"])
                                unmapped_ga_set.discard(norm)

                    for obj in inline_com_objects:
                        com_name = obj.get("name") or "Object"
                        gas = obj.get("group_addresses", [])
                        objects_list.append({
                            "name": com_name,
                            "gas": gas
                        })
                        for ga in gas:
                            norm = self.normalize_ga(ga)
                            info = dict(ga_map.get(norm, {"dpt": "", "name": ""}))
                            if com_name:
                                info["object_name"] = com_name
                                if not info.get("name"):
                                    info["name"] = com_name
                                else:
                                    info["name"] = f"{info['name']} {com_name}"
                            device_gas[norm] = info
                            if info["dpt"]:
                                all_dpts.append(info["dpt"])
                            unmapped_ga_set.discard(norm)

                    if not device_gas:
                        continue

                    if chan_name.lower() in dev_name.lower():
                        logical_name = dev_name
                    else:
                        logical_name = f"{dev_name} {chan_name}"

                    inferred_type = self.infer_device_type(all_dpts, logical_name)
                    inferred_room = self.infer_room_from_name_path(logical_name, f"{area_name} {line_name}")

                    caps = self.build_capabilities(inferred_type, device_gas)
                    legacy = self.build_legacy_fields(caps)

                    status = "ready"
                    reasons = []
                    confidence = 1.0

                    if inferred_type == "unknown":
                        status = "needs_review"
                        confidence = 0.5
                        reasons.append("Unknown device type could not be inferred from DPTs.")

                    if not any(legacy.values()):
                        status = "missing_info"
                        confidence = 0.3
                        reasons.append("No common Group Addresses could be mapped to legacy control fields.")

                    clean_name = re.sub(r"[^a-z0-9]+", "_", logical_name.lower().strip())
                    device_id = f"knx_{clean_name}_{phys_address.replace('.', '_')}"

                    proposed_devices.append({
                        "device_id": device_id,
                        "name": logical_name,
                        "room": inferred_room,
                        "type": inferred_type,
                        "status": status,
                        "confidence": confidence,
                        "reasons": reasons,
                        "source": {
                            "physical_address": phys_address,
                            "manufacturer": manufacturer,
                            "product": product,
                            "channel": chan_id,
                            "ets_device_name": dev_name
                        },
                        "legacy_fields": legacy,
                        "knx_config_payload": {
                            "capabilities": caps,
                            "raw": {
                                "group_addresses": list(device_gas.keys()),
                                "communication_objects": objects_list
                            }
                        },
                        "warnings": []
                    })

            ga_seen = {}
            duplicates = []
            for dev in proposed_devices:
                for ga in dev["knx_config_payload"]["raw"]["group_addresses"]:
                    if ga in ga_seen:
                        duplicates.append({
                            "group_address": ga,
                            "devices": [ga_seen[ga], dev["device_id"]]
                        })
                    ga_seen[ga] = dev["device_id"]

            proposal = make_proposal_base(
                file_name=Path(file_path).name,
                project_name=project_data.get("name", "KNX Project"),
                parser_version="3.9.0"
            )

            ready_count = sum(1 for d in proposed_devices if d["status"] == "ready")
            review_count = sum(1 for d in proposed_devices if d["status"] == "needs_review")
            missing_count = sum(1 for d in proposed_devices if d["status"] == "missing_info")

            by_type = {}
            for d in proposed_devices:
                t = d["type"]
                by_type[t] = by_type.get(t, 0) + 1

            proposal["summary"] = {
                "total_devices": len(proposed_devices),
                "ready": ready_count,
                "needs_review": review_count,
                "missing_info": missing_count,
                "by_type": by_type,
                "total_group_addresses": len(ga_map)
            }
            proposal["proposed_devices"] = proposed_devices
            proposal["duplicates"] = duplicates
            proposal["unmapped_group_addresses"] = list(unmapped_ga_set)

            return proposal

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
