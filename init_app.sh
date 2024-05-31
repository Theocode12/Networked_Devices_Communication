#!/bin/bash
sudo cp ./ssc.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable ssc.service
sudo systemctl start ssc.service
