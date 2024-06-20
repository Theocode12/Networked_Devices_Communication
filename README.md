# Networked device Communication Application

## Overview
The networked devive communication application is designed to facilitate data collection from networked devices using both MQTT and HTTP protocols. This application manages the collection, storage, and transfer of data, ensuring efficient and reliable communication for solar power systems.

## Features
- **MQTT Communication**: Manages MQTT connections, subscribes to topics, and processes incoming messages.
- **HTTP Communication**: Periodically fetches data from specified IP addresses and stores it in a file-based database.
- **Data Storage**: Utilizes a file-based database for efficient data storage and retrieval.
- **Cloud Transfer**: Supports transferring data to a cloud service: Google Sheets.
- **Logging**: Logs every event that happen in the application
- **Configurable Settings**: Allows customization of various settings through environment variables.

## Configurable Settings

The application provides several configurable settings that can be set through environment variables. These settings allow you to customize the behavior of the application according to your needs.

### Mode of Operation

- **MODE**
  - Description: Sets the mode of operation for the application.
  - Values: `dev`, `inter-dev`, `prod`
  - Example: `MODE=dev`
  - Uses: `dev` is used when development is done outside the main system network and simulations are done using an abstract environment. `inter-dev` is used when development is within the main system network and but we do not want data to be stored in the main database. `prod` is used in production environments.

### MQTT Configuration

- **MQTT_TOPICS**
  - Description: Comma-separated list of MQTT topics to subscribe to.
  - Example: `MQTT_TOPICS=/dev/test/inverter1,/dev/test/inverter2,/dev/test/inverter3,test/topic`

- **MQTT_USERNAME**
  - Description: Username for MQTT broker authentication.
  - Example: `MQTT_USERNAME=raspberrypi`

- **MQTT_PASSWORD**
  - Description: Password for MQTT broker authentication.
  - Example: `MQTT_PASSWORD=raspberrypi`

**Note**: MQTT server must be available and configuration set to password authentication. [Mosquitto documnation](https://mosquitto.org/documentation/authentication-methods/) for more information.

### HTTP Communication Configuration

- **DEVICE_IPS**
  - Description: Comma-separated list of IP addresses of devices to collect data from. This devices data must be available on the `/status` path.
  - Example: `DEVICE_IPS=192.168.1.128,192.168.1.155,192.168.1.156`

- **HTTP_TOPIC**
  - Description: Topic used in production mode for database path creation.
  - Example: `HTTP_TOPIC=/inverter/all`

### Cloud Transfer Configuration

- **GOOGLE_HOST**
  - Description: Host for Google services.
  - Example: `GOOGLE_HOST=script.google.com`

- **GOOGLE_SHEET_ID**
  - Description: ID of the Google Sheet to which data will be transferred.
  - Example: `GOOGLE_SHEET_ID=AKfjsjskdikdkdlodfURbrZTxt0A4AyP7u28ejdie93jjdowav`

### Feature Managers Configuration

- **DT_INTERVAL_HR**
  - Description: Interval in hours between requests for data. Default is zero.
  -Example: `DT_INTERVAL_HR=0`
- **DT_INTERVAL_MIN**
  - Description: Interval in minutes between requests for data. Default is 15.
  - Example: `DT_INTERVAL_MIN=15`
- **DT_INTERVAL_SEC**
  -  Description: Interval in seconds between requests for data. Default is zero.
- **MQTT_ENABLED**
  - Description: Enables or disables MQTT communication.
  - Values: `true`, `false`
  - Example: `MQTT_ENABLED=false`

- **HTTP_ENABLED**
  - Description: Enables or disables HTTP communication.
  - Values: `true`, `false`
  - Example: `HTTP_ENABLED=true`

- **CLOUD_ENABLED**
  - Description: Enables or disables cloud data transfer.
  - Values: `true`, `false`
  - Example: `CLOUD_ENABLED=true`
## Requirements
- Python 3.x
- Virtual environment setup (recommended)
- MQTT Broker
- HTTP Server for data endpoints

## Installation
1. **Clone the repository**:
    ```bash
    git clone https://github.com/Theocode12/Solar_Station_Communication.git
    cd Solar_Station_Communication
    ```

2. **Set up the virtual environment**:
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3. **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables**:
    Create a `.env` file in the `config` directory if its is not availble and add the config parameter as decribed above.

## Usage
1. **Start the application**:
    ```bash
    python app.py
    ```

    The application will start the MQTT manager, connect to the broker, and begin processing messages. HTTP communication will also start, fetching data at specified intervals.

2. **Monitor logs**:
    Logs are stored in the `logs` directory, providing detailed information about the application's activities.

3. **Run as a service**:
    Create a systemd service to run the application in the background. This can be done by using runinning the init_app.sh script
	```bash
	chmod u+x init_app.sh
	./init_app.sh
	```
	It can also be done manually as shown below:

    ```bash
    sudo nano /etc/systemd/system/ssc.service
    ```

    The following is an example content of the `ssc.service` file:
    ```
    [Unit]
    Description=Solar Station Communication Script
    After=network.target

    [Service]
    ExecStart=/home/user/Solar_Station_Communication/.venv/bin/python /home/user/Solar_Station_Communication/app.py
    WorkingDirectory=/home/user/Solar_Station_Communication
    StandardOutput=inherit
    StandardError=inherit
    Restart=always
    User=user

    [Install]
    WantedBy=multi-user.target
    ```

    Press `ctrl+o` and `Enter` to write the contents to the file

	Enable and start the service:
    ```bash
    sudo systemctl enable ssc.service
    sudo systemctl start ssc.service
    ```
	Logs can be monitored by using the following command:
	```bash
	journalctl _SYSTEMD_UNIT=ssc.service
	```
4. **Graceful Shutdown**:
    The application handles termination signals to ensure a graceful shutdown. To stop the application, use `Ctrl+C` or `sudo systemctl stop ssc.service` if running as a service.

## Customization
- **Environment Variables**: Modify the `.env` file to customize the application's behavior, such as MQTT topics, HTTP endpoints, and cloud transfer settings.
- **Logger Configuration**: Adjust logging settings in the `ModelLogger` class to control log levels and output formats.

## Directory Structure
- `models/`: Contains the core logic for data management, communication protocols, and storage.
- `config/`: Configuration files and environment variables.
- `logs/`: Log files for monitoring application activity.
- `app.py`: Entry point for the application.
- `ssc.service`: Systemd service file for running the application as a background service.

## Contributing
1. **Fork the repository**.
2. **Create a new branch**:
    ```bash
    git checkout -b feature-branch
    ```
3. **Commit your changes**:
    ```bash
    git commit -m "Add new feature"
    ```
4. **Push to the branch**:
    ```bash
    git push origin feature-branch
    ```
5. **Create a pull request**.

## License
This project is licensed under the MIT License.


