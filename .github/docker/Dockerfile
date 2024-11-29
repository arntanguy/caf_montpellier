# Point at any base image that you find suitable to extend.
FROM ubuntu:24.04 

# Install required tools that are useful for your project i.e. ninja-build
RUN apt update && apt install -y python3-bs4 python3-pip
RUN pip install --break-system-packages pip-system-certs rfeed ics pytz

ENTRYPOINT ["/bin/bash", "-c"]
