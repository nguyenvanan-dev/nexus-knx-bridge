import re

with open("frontend/src/app/devices/page.js", "r") as f:
    code = f.read()

old_clone = """  const duplicateDevice = (key, dev) => {
    setWizardMode('add');
    setCurrentDevice({
      device_id: `${key}_copy`,
      type: dev.type || 'light',
      onoff_ga: dev.onoff_ga || '',
      status_ga: dev.status_ga || '',
      brightness_ga: dev.brightness_ga || '',
      brightness_status_ga: dev.brightness_status_ga || ''
    });
    setWizardStep(1);
    setGaWarnings([]);
    setShowWizard(true);
  };"""

new_clone = """  const duplicateDevice = (key, dev) => {
    setWizardMode('add');
    setCurrentDevice({
      device_id: `${key}_copy`,
      type: dev.type || 'light',
      onoff_ga: '',
      status_ga: '',
      brightness_ga: '',
      brightness_status_ga: ''
    });
    setWizardStep(1);
    setGaWarnings([]);
    setShowWizard(true);
  };"""

code = code.replace(old_clone, new_clone)

with open("frontend/src/app/devices/page.js", "w") as f:
    f.write(code)
