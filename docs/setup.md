### Prequiestes & Requirements

- Raspberry Pi 4 or 5
- Wired USB Webcam

It is assumed that you have already imaged your SD card, with Debian Trixie Distro and know the basics of CLIs (Command Line Interface) & Debian commands.

The following Raspberry PI specs were used:

- Model: Raspberry Pi 5
- RAM: 16 GB
- SD Card Storage: 256 GB
- CPU: 4 Core Processor
- ARM64 Architecture

### Setup Instructions

- (if you haven't already) Follow the docker installation steps: [Docker Documentation](https://docs.docker.com/engine/install/raspberry-pi-os/) & test that you can run containers by running the command: `sudo docker run hello-world`
- Start the docker engine by executing the following command: `sudo sysctl start docker `
- Pull the latest image of my repo to your PI using the following command: `sudo docker pull johneley/johns-private-repo:latest` and wait for it to install
- Connect your webcam to the USB port on your Raspberry PI and verify that the webcam is powered on and if applicable make sure that the privacy shutter is retracted
- Start the container by running the following command:  `sudo docker run -p 5000:5000 johneley/johns-private-repo:latest`