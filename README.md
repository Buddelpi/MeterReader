# MeterReader

MeterReader is a small toolset to read mechanical meter digits from a camera, provide a GUI to configure digit masks and a headless reader that publishes readings via MQTT. It uses a small TFLite digit classifier and OpenCV for image capture and manipulation.

## Quick links
- Main reader: [`MeterReader.MeterReader`](MeterReader.py) — [MeterReader.py](MeterReader.py)  
- Configuration GUI: [`MeterConfigurator.MeterConfGUI`](MeterConfigurator.py) — [MeterConfigurator.py](MeterConfigurator.py)  
- Canvas widget used to draw/select masks: [`ImageManLabel.ImageManLabel`](ImageManLabel.py) — [ImageManLabel.py](ImageManLabel.py)  
- Mask item widget: [`ImageMaskPicker.MaskDigitItem`](ImageMaskPicker.py) — [ImageMaskPicker.py](ImageMaskPicker.py)  
- MQTT helper: [`MqttHandler.MqttHandler`](MqttHandler.py) — [MqttHandler.py](MqttHandler.py)  
- Trained digit model: [DigitNumberModel.tflite](DigitNumberModel.tflite)  
- Configuration template: [MeterToolConf.json](MeterToolConf.json)  
- Dockerfile: [Dockerfile](Dockerfile)  
- Python dependencies: [requirements.txt](requirements.txt)  
- GUI stylesheet: [style.css](style.css)

## Features
- Interactive Qt-based mask configurator to select each digit area on an image and save masks. See the GUI at [`MeterConfigurator.MeterConfGUI`](MeterConfigurator.py).
- Headless reader that:
  - Controls a flashlight via MQTT topics defined in the config,
  - Captures images, crops configured digit regions, runs a TFLite model to classify digits,
  - Publishes meter values via MQTT. See [`MeterReader.MeterReader`](MeterReader.py) and [`MqttHandler.MqttHandler`](MqttHandler.py).
- Small TFLite model for 0–9 digit inference: [DigitNumberModel.tflite](DigitNumberModel.tflite).

## Prerequisites
- Python 3.11+
- System packages required for OpenCV (Dockerfile demonstrates an example)
- Install Python deps:
```sh
# Install dependencies
pip install -r requirements.txt
```

## Configuration
- Copy and edit [MeterToolConf.json](MeterToolConf.json) to set:
  - MQTT broker details and topics,
  - Camera URL,
  - Digit layout and saved masks,
  - Inference thresholds and timing.

The configurator GUI (`MeterConfigurator`) helps create masks visually and stores them in `MeterToolConf.json`.

## Usage

1. Configure masks (GUI)
```sh
python MeterConfigurator.py
```
Use the UI to capture an image, click "Change" on a digit item to select its region (uses [`ImageManLabel.ImageManLabel`](ImageManLabel.py) for selection) and save the config.

2. Run the reader
```sh
python MeterReader.py
```
This starts the loop that captures images, runs inference with [DigitNumberModel.tflite](DigitNumberModel.tflite), and publishes results via MQTT using [`MqttHandler.MqttHandler`](MqttHandler.py).

## Docker (example)
The included [Dockerfile](Dockerfile) shows a simple image build that installs system libs and runs the reader. Adjust as needed for your runtime environment.

## File overview
- [MeterReader.py](MeterReader.py) — main reader loop and health/error handling (`MeterReader.MeterReader`)  
- [MeterConfigurator.py](MeterConfigurator.py) — configuration GUI (`MeterConfigurator.MeterConfGUI`)  
- [ImageManLabel.py](ImageManLabel.py) — interactive QLabel used to draw and crop regions (`ImageManLabel.ImageManLabel`)  
- [ImageMaskPicker.py](ImageMaskPicker.py) — widget for per-digit mask items (`ImageMaskPicker.MaskDigitItem`)  
- [MqttHandler.py](MqttHandler.py) — reconnecting MQTT client helper (`MqttHandler.MqttHandler`)  
- [DigitNumberModel.tflite](DigitNumberModel.tflite) — TFLite digit classifier  
- [MeterToolConf.json](MeterToolConf.json) — persistent config for masks, MQTT and camera  
- [requirements.txt](requirements.txt) — Python dependencies  
- [style.css](style.css) — GUI styling

## Notes & tips
- The TFLite model expects digit crops resized to 20×32. The GUI and reader perform that resize automatically.
- MQTT topics are specified in [MeterToolConf.json](MeterToolConf.json). The GUI can publish flashlight control topics for camera illumination.
- Logs are written to `meter_reader_log.log` by the reader.

## Contributing
Bug reports, improvements and PRs welcome.

## License
See