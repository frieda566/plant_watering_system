# Flower power - Our plant watering system

### Description 
This project combines an Arduino Uno with sensors and Python software to monitor plant health and automate watering. 
The system measures soil moisture, temperature, and humidity, stores the data, and compares it to optimal ranges for each plant. 
It can generate health reports and alert when conditions require attention, helping maintain healthy plants efficiently.

### File overview 
- arduinoIDE_code - contains the Arduino code uploaded to the Arduino Uno, handling sensor readings (moisture, temperature, humidity) and sending data to the Python application
- images - stores any images used in the Python GUI or documentation
- documentation - contains project-related ideas, development process, sources, possible further developments, ... 
- README.md - provides a general project overview, instructions and setup guidance for users
- LICENSE - 
- necessary_libraries???
- plant watering system.py - the main Python application; handles data collection, analysis, weekly health report generation, and GUI interactions
- plant_care_lexicon.csv - contains plant-specific information such as care tips or classifications used by the Python app
- plant_data.db - a SQLite database storing structured historical sensor data for plants
- plant_health_ranges.csv - reference table with optimal temperature, humidity, and optionally moisture ranges for each plant
- plant_history.json - stores the raw sensor readings over time, used for calculating weekly averages and generating health reports