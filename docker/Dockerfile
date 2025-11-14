FROM registry.access.redhat.com/ubi9/python-39

RUN yum -y install gcc make patchelf &&     python3 -m pip install --upgrade pip setuptools wheel

# Copy tool and install
WORKDIR /opt/s390x-auto-path
COPY . /opt/s390x-auto-path
RUN pip install -e .
