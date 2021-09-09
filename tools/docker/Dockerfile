# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

ARG ENV="cpu"
ARG HOME="/root"

FROM ubuntu:18.04 AS base

LABEL maintainer="Microsoft Recommender Project <RecoDevTeam@service.microsoft.com>"

ARG HOME
ARG VIRTUAL_ENV
ENV HOME="${HOME}"
WORKDIR ${HOME}

# Exit if VIRTUAL_ENV is not specified correctly
RUN if [ "${VIRTUAL_ENV}" != "conda" ] && [ "${VIRTUAL_ENV}" != "venv" ] && [ "${VIRTUAL_ENV}" != "virtualenv" ]; then \
    echo 'VIRTUAL_ENV argument should be either "conda", "venv" or "virtualenv"'; exit 1; fi

# Install base dependencies, cmake (for xlearn) and libpython (for cornac)
RUN apt-get update && \
    apt-get install -y curl build-essential cmake
RUN if [ "${VIRTUAL_ENV}" = "conda" ] ; then apt-get install -y libpython3.7; fi
RUN if [ "${VIRTUAL_ENV}" = "venv" ] || [ "${VIRTUAL_ENV}" = "virtualenv" ]; then apt-get install -y libpython3.6; fi

# Install Anaconda
ARG ANACONDA="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
RUN if [ "${VIRTUAL_ENV}" = "conda" ] ; then curl ${ANACONDA} -o anaconda.sh && \
    /bin/bash anaconda.sh -b -p conda && \
    rm anaconda.sh && \
    echo ". ${HOME}/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc ; fi

ENV PATH="${HOME}/${VIRTUAL_ENV}/bin:${PATH}"

# --login option used to source bashrc (thus activating conda env) at every RUN statement
SHELL ["/bin/bash", "--login", "-c"]

# Python version supported by recommenders
RUN if [ "${VIRTUAL_ENV}" = "conda" ] ; then conda install python=3.7; fi
RUN if [ "${VIRTUAL_ENV}" = "venv" ] ; then apt-get -y install python3.6; \
    apt-get -y install python3-pip; \
    apt-get -y install python3.6-venv; fi
RUN if [ "${VIRTUAL_ENV}" = "virtualenv" ] ; then apt-get -y install python3.6; \
    apt-get -y install python3-pip; \
    python3.6 -m pip install --user virtualenv; fi

# Activate the virtual environment
RUN if [ "${VIRTUAL_ENV}" = "venv" ] ; then python3.6 -m venv --system-site-packages $HOME/${VIRTUAL_ENV}; \
    source $HOME/${VIRTUAL_ENV}/bin/activate; \
    pip install --upgrade pip; \
    pip install --upgrade setuptools; fi
RUN if [ "${VIRTUAL_ENV}" = "virtualenv" ] ; then python3.6 -m virtualenv $HOME/${VIRTUAL_ENV}; \
    source $HOME/${VIRTUAL_ENV}/bin/activate; \
    pip install --upgrade pip; \
    pip install --upgrade setuptools; fi

###########
# CPU Stage
###########
FROM base AS cpu

RUN if [ "${VIRTUAL_ENV}" = "venv" ] || [ "${VIRTUAL_ENV}" = "virtualenv" ]; then source $HOME/${VIRTUAL_ENV}/bin/activate; \
    pip install recommenders[xlearn,examples]; fi
# Note that "conda install numpy-base" needs to be called after the pip installation
# so that numpy works smoothly with other dependencies in python 3.7
RUN if [ "${VIRTUAL_ENV}" = "conda" ] ; then pip install recommenders[xlearn,examples]; \
    conda install -n base numpy-base; fi


###############
# PySpark Stage
###############
FROM base AS pyspark

# Install Java version 8
RUN apt-get update && \
    apt-get install -y libgomp1 openjdk-8-jre

ENV JAVA_HOME="/usr/lib/jvm/java-8-openjdk-amd64" \
    PYSPARK_PYTHON="${HOME}/${VIRTUAL_ENV}/bin/python" \
    PYSPARK_DRIVER_PYTHON="${HOME}/${VIRTUAL_ENV}/bin/python"

# Install dependencies in virtual environment
RUN if [ "${VIRTUAL_ENV}" = "venv" ] || [ "${VIRTUAL_ENV}" = "virtualenv" ]; then source $HOME/${VIRTUAL_ENV}/bin/activate; \
    pip install recommenders[spark,xlearn,examples]; fi
RUN if [ "${VIRTUAL_ENV}" = "conda" ] ; then pip install recommenders[spark,xlearn,examples]; \
    conda install -n base numpy-base; fi


###########
# GPU Stage
###########
FROM nvidia/cuda:10.0-cudnn7-runtime-ubuntu18.04 AS gpu

ARG HOME
ARG VIRTUAL_ENV
ENV HOME="${HOME}"
WORKDIR ${HOME}

# Exit if VIRTUAL_ENV is not specified correctly
RUN if [ "${VIRTUAL_ENV}" != "conda" ] && [ "${VIRTUAL_ENV}" != "venv" ] && [ "${VIRTUAL_ENV}" != "virtualenv" ]; then \
    echo 'VIRTUAL_ENV argument should be either "conda", "venv" or "virtualenv"'; exit 1; fi

RUN apt-get update && \
    apt-get install -y curl build-essential cmake
RUN if [ "${VIRTUAL_ENV}" = "conda" ] ; then apt-get install -y libpython3.7; fi
RUN if [ "${VIRTUAL_ENV}" = "venv" ] || [ "${VIRTUAL_ENV}" = "virtualenv" ]; then apt-get install -y libpython3.6; fi

# Install Anaconda
ARG ANACONDA="https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh"
RUN if [ "${VIRTUAL_ENV}" = "conda" ] ; then curl ${ANACONDA} -o anaconda.sh && \
    /bin/bash anaconda.sh -b -p conda && \
    rm anaconda.sh && \
    echo ". ${HOME}/conda/etc/profile.d/conda.sh" >> ~/.bashrc && \
    echo "conda activate base" >> ~/.bashrc; fi

ENV PATH="${HOME}/${VIRTUAL_ENV}/bin:${PATH}"

SHELL ["/bin/bash", "--login", "-c"]

# Python version supported by recommenders
RUN if [ "${VIRTUAL_ENV}" = "conda" ] ; then conda install python=3.7; fi
RUN if [ "${VIRTUAL_ENV}" = "venv" ] ; then apt-get -y install python3.6; \
    apt-get -y install python3-pip; \
    apt-get -y install python3.6-venv; fi
RUN if [ "${VIRTUAL_ENV}" = "virtualenv" ] ; then apt-get -y install python3.6; \
    apt-get -y install python3-pip; \
    python3.6 -m pip install --user virtualenv; fi

# Activate the virtual environment
RUN if [ "${VIRTUAL_ENV}" = "venv" ] ; then python3.6 -m venv --system-site-packages $HOME/${VIRTUAL_ENV}; \
    source $HOME/${VIRTUAL_ENV}/bin/activate; \
    pip install --upgrade pip; \
    pip install --upgrade setuptools; \
    pip install recommenders[gpu,xlearn,examples]; fi
RUN if [ "${VIRTUAL_ENV}" = "virtualenv" ] ; then python3.6 -m virtualenv $HOME/${VIRTUAL_ENV}; \
    source $HOME/${VIRTUAL_ENV}/bin/activate; \
    pip install --upgrade pip; \
    pip install --upgrade setuptools; \
    pip install recommenders[gpu,xlearn,examples]; fi

RUN if [ "${VIRTUAL_ENV}" = "conda" ] ; then \
    pip install recommenders[gpu,xlearn,examples] -f https://download.pytorch.org/whl/cu100/torch_stable.html && \
    conda install -n base numpy-base; fi


############
# Full Stage
############
FROM gpu AS full

ARG HOME
WORKDIR ${HOME}

SHELL ["/bin/bash", "--login", "-c"]

# Install Java version 8
RUN apt-get update && \
    apt-get install -y libgomp1 openjdk-8-jre

ENV JAVA_HOME="/usr/lib/jvm/java-8-openjdk-amd64" \
    PYSPARK_PYTHON="${HOME}/${VIRTUAL_ENV}/bin/python" \
    PYSPARK_DRIVER_PYTHON="${HOME}/${VIRTUAL_ENV}/bin/python"

# Install dependencies in virtual environment
RUN if [ "${VIRTUAL_ENV}" = "venv" ] || [ "${VIRTUAL_ENV}" = "virtualenv" ]; then source $HOME/${VIRTUAL_ENV}/bin/activate; \
    pip install recommenders[all]; fi
RUN if [ "${VIRTUAL_ENV}" = "conda" ] ; then pip install recommenders[all]; fi

# It is not clear why but force-reinstall is needed at this place, 
# otherwise numpy-base does not appear in conda list  
RUN if [ "${VIRTUAL_ENV}" = "conda" ] ; then conda update --force-reinstall -y -n base numpy-base; fi


#############
# Final Stage
#############
FROM $ENV AS final

# Setup Jupyter notebook configuration
ENV NOTEBOOK_CONFIG="${HOME}/.jupyter/jupyter_notebook_config.py"
RUN mkdir ${HOME}/.jupyter && \
    echo "c.NotebookApp.token = ''" >> ${NOTEBOOK_CONFIG} && \
    echo "c.NotebookApp.ip = '0.0.0.0'" >> ${NOTEBOOK_CONFIG} && \
    echo "c.NotebookApp.allow_root = True" >> ${NOTEBOOK_CONFIG} && \
    echo "c.NotebookApp.open_browser = False" >> ${NOTEBOOK_CONFIG} && \
    echo "c.MultiKernelManager.default_kernel_name = 'python3'" >> ${NOTEBOOK_CONFIG}

# Register the environment with Jupyter
RUN if [ "${VIRTUAL_ENV}" = "conda" ]; then python -m ipykernel install --user --name base --display-name "Python (base)"; fi
RUN if [ "${VIRTUAL_ENV}" = "venv" ] || [ "${VIRTUAL_ENV}" = "virtualenv" ]; then source $HOME/${VIRTUAL_ENV}/bin/activate; \
    python -m ipykernel install --user --name venv --display-name "Python (venv)"; fi

ARG HOME
WORKDIR ${HOME}

EXPOSE 8888
CMD ["jupyter", "notebook"]
