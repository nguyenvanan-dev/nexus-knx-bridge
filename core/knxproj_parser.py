import json
import traceback
import re
from datetime import datetime
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

        if any(d.startswith("9.") or d.startswith("20.") for d in dpts) or any(k in name_lower for k in ["hvac", "thermostat", "điều hòa", "ac", "aircon", "fcu", "fan"]):
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

        def find_ga(dpt_prefix=None, name_kw=None):
            for address, info in gas.items():
                dpt = info.get("dpt", "")
                name = info.get("name", "").lower()
                if dpt_prefix and dpt.startswith(dpt_prefix):
                    return address
                if name_kw and any(k in name for k in name_kw):
                    return address
            return None

        if dev_type in ["light", "switch"]:
            onoff = find_ga("1.") or (list(gas.keys())[0] if gas else "")
            status = find_ga(name_kw=["status", "state", "feedback", "phản hồi"]) or onoff
            caps["onoff"] = {"write_ga": onoff, "status_ga": status, "dpt": "1.001"}

        elif dev_type == "dimmer":
            onoff = find_ga("1.") or (list(gas.keys())[0] if gas else "")
            status = find_ga(name_kw=["status", "state", "feedback", "phản hồi"]) or onoff
            caps["onoff"] = {"write_ga": onoff, "status_ga": status, "dpt": "1.001"}

            brightness = find_ga("5.")
            bright_status = find_ga(name_kw=["bright status", "bright feedback", "phần trăm phản hồi", "brightness status"]) or brightness
            if brightness:
                caps["brightness"] = {"write_ga": brightness, "status_ga": bright_status, "dpt": "5.001"}

        elif dev_type == "color_light":
            onoff = find_ga("1.") or (list(gas.keys())[0] if gas else "")
            status = find_ga(name_kw=["status", "state", "feedback", "phản hồi"]) or onoff
            caps["onoff"] = {"write_ga": onoff, "status_ga": status, "dpt": "1.001"}

            brightness = find_ga("5.")
            bright_status = find_ga(name_kw=["bright status", "brightness status"]) or brightness
            if brightness:
                caps["brightness"] = {"write_ga": brightness, "status_ga": bright_status, "dpt": "5.001"}

            color_temp = find_ga("7.600") or find_ga("7.")
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
            onoff = find_ga("1.") or (list(gas.keys())[0] if gas else "")
            status = find_ga(name_kw=["status", "state", "feedback"]) or onoff
            caps["onoff"] = {"write_ga": onoff, "status_ga": status, "dpt": "1.001"}

            rgb = find_ga("232.")
            rgb_status = find_ga(name_kw=["rgb status", "color status", "màu status"]) or rgb
            if rgb:
                caps["rgb"] = {"write_ga": rgb, "status_ga": rgb_status, "dpt": "232.600"}

        elif dev_type in ["curtain", "blind"]:
            updown = find_ga("1.008") or find_ga("1.") or (list(gas.keys())[0] if gas else "")
            stop = find_ga("1.017") or find_ga(name_kw=["stop", "dừng", "step"]) or updown
            caps["curtain"] = {"write_ga": updown, "stop_ga": stop, "dpt": "1.008"}

            position = find_ga("5.")
            pos_status = find_ga(name_kw=["position status", "pos status", "phần trăm phản hồi"]) or position
            if position:
                caps["position"] = {"write_ga": position, "status_ga": pos_status, "dpt": "5.001"}

        elif dev_type == "hvac":
            temp_status = find_ga("9.001") or find_ga("9.")
            if temp_status:
                caps["temperature"] = {"status_ga": temp_status, "dpt": "9.001"}

            setpoint = find_ga(name_kw=["setpoint", "đặt", "target"]) or find_ga("9.001") or find_ga("9.")
            setpoint_status = find_ga(name_kw=["setpoint status", "setpoint feedback"]) or setpoint
            if setpoint:
                caps["thermostat"] = {"write_ga": setpoint, "status_ga": setpoint_status, "dpt": "9.001"}

            mode = find_ga("20.102") or find_ga("20.")
            mode_status = find_ga(name_kw=["mode status", "chế độ status"]) or mode
            if mode:
                caps["mode"] = {"write_ga": mode, "status_ga": mode_status, "dpt": "20.102"}

        elif dev_type == "sensor":
            val_ga = find_ga("9.") or find_ga("14.") or find_ga("13.") or (list(gas.keys())[0] if gas else "")
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
            ga_list = project_data.get("group_addresses", [])

            if isinstance(ga_list, list):
                for ga_item in ga_list:
                    addr = ga_item.get("address", "")
                    dpt = ga_item.get("dpt", None)
                    name = ga_item.get("name", "")
                    if addr:
                        norm_addr = self.normalize_ga(addr)
                        ga_map[norm_addr] = {
                            "dpt": self.normalize_dpt(dpt),
                            "name": name
                        }
            elif isinstance(ga_list, dict):
                def extract_flat(node):
                    if isinstance(node, dict):
                        addr = node.get("address")
                        dpt = node.get("dpt")
                        name = node.get("name", "")
                        if addr:
                            norm_addr = self.normalize_ga(addr)
                            ga_map[norm_addr] = {
                                "dpt": self.normalize_dpt(dpt),
                                "name": name
                            }
                        for v in node.values():
                            extract_flat(v)
                    elif isinstance(node, list):
                        for item in node:
                            extract_flat(item)
                extract_flat(ga_list)

            proposed_devices = []
            unmapped_ga_set = set(ga_map.keys())

            topology = project_data.get("topology", {})
            areas = topology.get("areas", [])
            for area in areas:
                area_name = area.get("name", "")
                lines = area.get("lines", [])
                for line in lines:
                    line_name = line.get("name", "")
                    devices = line.get("devices", [])
                    for device in devices:
                        phys_address = device.get("address", "")
                        dev_name = device.get("name", "Unknown Device")
                        manufacturer = device.get("manufacturer_name", "")
                        product = device.get("product_name", "")

                        com_objects = device.get("com_objects", [])

                        channel_groups = {}
                        for com in com_objects:
                            com_name = com.get("name", "")
                            gas = com.get("group_addresses", [])

                            chan_match = re.search(r"\b(ch(?:annel)?|output|in|out|ch\.)\s*([a-h0-9]+)\b", com_name, re.IGNORECASE)
                            chan_key = chan_match.group(0).upper() if chan_match else "MAIN"

                            if chan_key not in channel_groups:
                                channel_groups[chan_key] = []
                            channel_groups[chan_key].append((com_name, gas))

                        for chan, objects in channel_groups.items():
                            device_gas = {}
                            all_dpts = []
                            for com_name, gas in objects:
                                for ga in gas:
                                    ga_addr = ga if isinstance(ga, str) else ga.get("address", "")
                                    if ga_addr:
                                        norm = self.normalize_ga(ga_addr)
                                        info = ga_map.get(norm, {"dpt": "", "name": com_name})
                                        device_gas[norm] = info
                                        if info["dpt"]:
                                            all_dpts.append(info["dpt"])
                                        unmapped_ga_set.discard(norm)

                            if not device_gas:
                                continue

                            chan_suffix = f" {chan}" if chan != "MAIN" else ""
                            logical_name = f"{dev_name}{chan_suffix}"
                            inferred_type = self.infer_device_type(all_dpts, logical_name)
                            inferred_room = self.infer_room_from_name_path(logical_name, f"{area_name} {line_name}")

                            caps = self.build_capabilities(inferred_type, device_gas)
                            legacy = self.build_legacy_fields(caps)

                            status = "ready"
                            reasons = []
                            warnings = []
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
                                    "channel": chan,
                                    "ets_device_name": dev_name
                                },
                                "legacy_fields": legacy,
                                "knx_config_payload": {
                                    "capabilities": caps,
                                    "raw": {
                                        "group_addresses": list(device_gas.keys()),
                                        "communication_objects": [{"name": o[0], "gas": o[1]} for o in objects]
                                    }
                                },
                                "warnings": warnings
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
